import logging

from nefertari import engine

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


def prepare_relationship(config, field_name, model_name, raml_resource):
    """ Create referenced model if it doesn't exist.

    When preparing a relationship, we check to see if the model that will be
    referenced already exists. If not, it is created so that it will be possible
    to use it in a relationship. Thus the first usage of this model in RAML file
    must provide its schema in POST method resource body schema.

    :param field_name: Name of the field that should become a `Relationship`.
    :param model_name: Name of model which should be generated.
    :param raml_resource: Instance of ramlfications.raml.ResourceNode for
        which :model_name: will be defined.
    """
    if get_existing_model(model_name) is None:
        for res in raml_resource.root.resources:
            if res.method.upper() != 'POST':
                continue
            if res.path.endswith('/' + field_name):
                break
        else:
            raise ValueError('Model `{}` used in relationship `{}` is not '
                             'defined'.format(model_name, field_name))
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
    if auth_model:
        bases = (AuthModelMethodsMixin, base_cls)
    else:
        bases = (base_cls,)
    attrs = {
        '__tablename__': model_name.lower(),
        '_public_fields': schema.get('_public_fields') or [],
        '_auth_fields': schema.get('_auth_fields') or [],
        '_nested_relationships': schema.get('_nested_relationships') or [],
    }
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
                config, field_name, field_kwargs['document'],
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
    model_cls = metaclass(model_name, bases, attrs)
    setup_event_subscribers(config, model_cls, schema)
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
    from .models import generate_model_cls, get_existing_model
    model_cls = get_existing_model(model_name)
    if model_cls is not None:
        return model_cls, False

    schema = resource_schema(raml_resource)
    if not schema:
        raise Exception('Missing schema for model `{}`'.format(model_name))

    log.info('Generating model class `{}`'.format(model_name))
    return generate_model_cls(
        config,
        schema=schema,
        model_name=model_name,
        raml_resource=raml_resource,
    )


def handle_model_generation(config, raml_resource, route_name):
    """ Generates model name and runs `setup_data_model` to get
    or generate actual model class.

    :param raml_resource: Instance of ramlfications.raml.ResourceNode.
    :param route_name: String name of the resource.
    """
    model_name = generate_model_name(route_name)
    try:
        return setup_data_model(config, raml_resource, model_name)
    except ValueError as ex:
        raise ValueError('{}: {}'.format(model_name, str(ex)))


def _connect_subscribers(config, events_map, events_schema, event_kwargs):
    """ Performs the actual subscribers set up.

    :param config: Pyramid Configurator instance.
    :param events_map: Dict returned by `get_events_map`.
    :param events_schema: Dict of {event_tag: [handler1, ...]}
    :param event_kwargs: Dict of kwargs to be used when subscribing
        to event.
    """
    for event_tag, subscribers in events_schema.items():
        type_, action = event_tag.split('_')
        event_objects = events_map[type_][action]

        if not isinstance(event_objects, list):
            event_objects = [event_objects]

        for sub_name in subscribers:
            sub_func = resolve_to_callable(sub_name)
            config.subscribe_to_events(
                sub_func, event_objects, **event_kwargs)


def setup_event_subscribers(config, model_cls, schema):
    """ High level function to set up event subscribers.

    :param config: Pyramid Configurator instance.
    :param model_cls: Model class for which handlers should be connected.
    :param schema: Dict of model JSON schema.
    """
    events_map = get_events_map()

    # Model events
    model_events = schema.get('_event_handlers', {})
    event_kwargs = {'model': model_cls}
    _connect_subscribers(config, events_map, model_events, event_kwargs)

    # Field events
    properties = schema.get('properties', {})
    for field_name, props in properties.items():

        if not props or '_event_handlers' not in props:
            continue

        field_events = props.get('_event_handlers', {})
        event_kwargs = {'model': model_cls, 'field': field_name}
        _connect_subscribers(config, events_map, field_events, event_kwargs)
