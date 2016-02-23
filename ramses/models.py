import logging

from nefertari import engine
from inflection import pluralize

from .utils import (
    resolve_to_callable, is_callable_tag,
    resource_schema, generate_model_name,
    get_events_map)
from . import registry


log = logging.getLogger(__name__)

"""
Map of RAML types names to nefertari.engine fields.

"""
type_fields = {
    'string':           engine.StringField,
    'float':            engine.FloatField,
    'integer':          engine.IntegerField,
    'boolean':          engine.BooleanField,
    'datetime':         engine.DateTimeField,
    'file':             engine.BinaryField,
    'relationship':     engine.Relationship,
    'dict':             engine.DictField,
    'foreign_key':      engine.ForeignKeyField,
    'big_integer':      engine.BigIntegerField,
    'date':             engine.DateField,
    'choice':           engine.ChoiceField,
    'interval':         engine.IntervalField,
    'decimal':          engine.DecimalField,
    'pickle':           engine.PickleField,
    'small_integer':    engine.SmallIntegerField,
    'text':             engine.TextField,
    'time':             engine.TimeField,
    'unicode':          engine.UnicodeField,
    'unicode_text':     engine.UnicodeTextField,
    'id_field':         engine.IdField,
    'list':             engine.ListField,
}


def get_existing_model(model_name):
    """ Try to find existing model class named `model_name`.

    :param model_name: String name of the model class.
    """
    try:
        model_cls = engine.get_document_cls(model_name)
        log.debug('Model `{}` already exists. Using existing one'.format(
            model_name))
        return model_cls
    except ValueError:
        log.debug('Model `{}` does not exist'.format(model_name))


def prepare_relationship(config, model_name, raml_resource):
    """ Create referenced model if it doesn't exist.

    When preparing a relationship, we check to see if the model that will be
    referenced already exists. If not, it is created so that it will be possible
    to use it in a relationship. Thus the first usage of this model in RAML file
    must provide its schema in POST method resource body schema.

    :param model_name: Name of model which should be generated.
    :param raml_resource: Instance of ramlfications.raml.ResourceNode for
        which :model_name: will be defined.
    """
    if get_existing_model(model_name) is None:
        plural_route = '/' + pluralize(model_name.lower())
        route = '/' + model_name.lower()
        for res in raml_resource.root.resources:
            if res.method.upper() != 'POST':
                continue
            if res.path.endswith(plural_route) or res.path.endswith(route):
                break
        else:
            raise ValueError('Model `{}` used in relationship is not '
                             'defined'.format(model_name))
        setup_data_model(config, res, model_name)


def generate_model_cls(config, schema, model_name, raml_resource,
                       es_based=True):
    """ Generate model class.

    Engine DB field types are determined using `type_fields` and only those
    types may be used.

    :param schema: Model schema dict parsed from RAML.
    :param model_name: String that is used as new model's name.
    :param raml_resource: Instance of ramlfications.raml.ResourceNode.
    :param es_based: Boolean indicating if generated model should be a
        subclass of Elasticsearch-based document class or not.
        It True, ESBaseDocument is used; BaseDocument is used otherwise.
        Defaults to True.
    """
    from nefertari.authentication.models import AuthModelMethodsMixin
    base_cls = engine.ESBaseDocument if es_based else engine.BaseDocument
    model_name = str(model_name)
    metaclass = type(base_cls)
    auth_model = schema.get('_auth_model', False)

    bases = []
    if config.registry.database_acls:
        from nefertari_guards import engine as guards_engine
        bases.append(guards_engine.DocumentACLMixin)
    if auth_model:
        bases.append(AuthModelMethodsMixin)
    bases.append(base_cls)

    attrs = {
        '__tablename__': model_name.lower(),
        '_public_fields': schema.get('_public_fields') or [],
        '_auth_fields': schema.get('_auth_fields') or [],
        '_hidden_fields': schema.get('_hidden_fields') or [],
        '_nested_relationships': schema.get('_nested_relationships') or [],
    }
    if '_nesting_depth' in schema:
        attrs['_nesting_depth'] = schema.get('_nesting_depth')

    # Generate fields from properties
    properties = schema.get('properties', {})
    for field_name, props in properties.items():
        if field_name in attrs:
            continue

        db_settings = props.get('_db_settings')
        if db_settings is None:
            continue

        field_kwargs = db_settings.copy()
        field_kwargs['required'] = bool(field_kwargs.get('required'))

        for default_attr_key in ('default', 'onupdate'):
            value = field_kwargs.get(default_attr_key)
            if is_callable_tag(value):
                field_kwargs[default_attr_key] = resolve_to_callable(value)

        type_name = (
            field_kwargs.pop('type', 'string') or 'string').lower()
        if type_name not in type_fields:
            raise ValueError('Unknown type: {}'.format(type_name))

        field_cls = type_fields[type_name]

        if field_cls is engine.Relationship:
            prepare_relationship(
                config, field_kwargs['document'],
                raml_resource)
        if field_cls is engine.ForeignKeyField:
            key = 'ref_column_type'
            field_kwargs[key] = type_fields[field_kwargs[key]]
        if field_cls is engine.ListField:
            key = 'item_type'
            field_kwargs[key] = type_fields[field_kwargs[key]]

        attrs[field_name] = field_cls(**field_kwargs)

    # Update model definition with methods and variables defined in registry
    attrs.update(registry.mget(model_name))

    # Generate new model class
    model_cls = metaclass(model_name, tuple(bases), attrs)
    setup_model_event_subscribers(config, model_cls, schema)
    setup_fields_processors(config, model_cls, schema)
    return model_cls, auth_model


def setup_data_model(config, raml_resource, model_name):
    """ Setup storage/data model and return generated model class.

    Process follows these steps:
      * Resource schema is found and restructured by `resource_schema`.
      * Model class is generated from properties dict using util function
        `generate_model_cls`.

    :param raml_resource: Instance of ramlfications.raml.ResourceNode.
    :param model_name: String representing model name.
    """
    model_cls = get_existing_model(model_name)
    schema = resource_schema(raml_resource)

    if not schema:
        raise Exception('Missing schema for model `{}`'.format(model_name))

    if model_cls is not None:
        return model_cls, schema.get('_auth_model', False)

    log.info('Generating model class `{}`'.format(model_name))
    return generate_model_cls(
        config,
        schema=schema,
        model_name=model_name,
        raml_resource=raml_resource,
    )


def handle_model_generation(config, raml_resource):
    """ Generates model name and runs `setup_data_model` to get
    or generate actual model class.

    :param raml_resource: Instance of ramlfications.raml.ResourceNode.
    """
    model_name = generate_model_name(raml_resource)
    try:
        return setup_data_model(config, raml_resource, model_name)
    except ValueError as ex:
        raise ValueError('{}: {}'.format(model_name, str(ex)))


def setup_model_event_subscribers(config, model_cls, schema):
    """ Set up model event subscribers.

    :param config: Pyramid Configurator instance.
    :param model_cls: Model class for which handlers should be connected.
    :param schema: Dict of model JSON schema.
    """
    events_map = get_events_map()
    model_events = schema.get('_event_handlers', {})
    event_kwargs = {'model': model_cls}

    for event_tag, subscribers in model_events.items():
        type_, action = event_tag.split('_')
        event_objects = events_map[type_][action]

        if not isinstance(event_objects, list):
            event_objects = [event_objects]

        for sub_name in subscribers:
            sub_func = resolve_to_callable(sub_name)
            config.subscribe_to_events(
                sub_func, event_objects, **event_kwargs)


def setup_fields_processors(config, model_cls, schema):
    """ Set up model fields' processors.

    :param config: Pyramid Configurator instance.
    :param model_cls: Model class for field of which processors should be
        set up.
    :param schema: Dict of model JSON schema.
    """
    properties = schema.get('properties', {})
    for field_name, props in properties.items():
        if not props:
            continue

        processors = props.get('_processors')
        backref_processors = props.get('_backref_processors')

        if processors:
            processors = [resolve_to_callable(val) for val in processors]
            setup_kwargs = {'model': model_cls, 'field': field_name}
            config.add_field_processors(processors, **setup_kwargs)

        if backref_processors:
            db_settings = props.get('_db_settings', {})
            is_relationship = db_settings.get('type') == 'relationship'
            document = db_settings.get('document')
            backref_name = db_settings.get('backref_name')
            if not (is_relationship and document and backref_name):
                continue

            backref_processors = [
                resolve_to_callable(val) for val in backref_processors]
            setup_kwargs = {
                'model': engine.get_document_cls(document),
                'field': backref_name
            }
            config.add_field_processors(
                backref_processors, **setup_kwargs)
