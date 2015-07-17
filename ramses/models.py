import logging

from nefertari import engine

from .utils import (
    resolve_to_callable, is_callable_tag,
    resource_schema, generate_model_name)
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

    Arguments:
        :model_name: String name of the model class.
    """
    try:
        model_cls = engine.get_document_cls(model_name)
        log.debug('Model `{}` already exists. Using existing one'.format(
            model_name))
        return model_cls
    except ValueError:
        log.debug('Model `{}` does not exist'.format(model_name))


def prepare_relationship(field_name, model_name, raml_resource):
    """ Create referenced model if it doesn't exist.

    When preparing a relationship, we check to see if the model that will be
    referenced already exists. If not, it is created so that it will be possible
    to use it in a relationship. Thus the first usage of this model in RAML file
    must provide its schema in POST method resource body schema.

    Arguments:
        :field_name: Name of the field that should become a `Relationship`.
        :raml_resource: Instance of pyraml.entities.RamlResource. Resource
            for which :model_name: will be defined.
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
        setup_data_model(res, model_name)


def generate_model_cls(schema, model_name, raml_resource, es_based=True):
    """ Generate model class.

    Engine DB field types are determined using `type_fields` and only those
    types may be used.

    Arguments:
        :properties: Dictionary of DB schema fields which looks like
            {field_name: {required: boolean, type: type_name}, ...}
        :model_name: String that is used as new model's name.
        :raml_resource: Instance of pyraml.entities.RamlResource.
        :es_based: Boolean indicating if generated model should be a
            subclass of Elasticsearch-based document class or not.
            It True, ESBaseDocument is used; BaseDocument is used otherwise.
            Defaults to True.
        :predefined_fields: Dictionary of {field_name: field_obj} of fields
            that are already instantiated.
    """
    from nefertari.authentication.models import AuthModelMethodsMixin
    base_cls = engine.ESBaseDocument if es_based else engine.BaseDocument
    model_name = str(model_name)
    metaclass = type(base_cls)
    auth_model = schema.get('auth_model', False)
    if auth_model:
        bases = (AuthModelMethodsMixin, base_cls)
    else:
        bases = (base_cls,)
    attrs = {
        '__tablename__': model_name.lower(),
        '_public_fields': schema.get('public_fields') or [],
        '_auth_fields': schema.get('auth_fields') or [],
        '_nested_relationships': schema.get('nested_relationships') or [],
    }
    # Generate fields from properties
    properties = schema.get('properties', {})
    for field_name, props in properties.items():
        if field_name in attrs:
            continue

        field_kwargs = {
            'required': bool(props.get('required'))
        }
        field_kwargs.update(props.get('args', {}) or {})

        for default_attr_key in ('default', 'onupdate'):
            value = field_kwargs.get(default_attr_key)
            if is_callable_tag(value):
                field_kwargs[default_attr_key] = resolve_to_callable(value)

        for processor_key in ('before_validation', 'after_validation'):
            processors = field_kwargs.get(processor_key, [])
            field_kwargs[processor_key] = [
                resolve_to_callable(name) for name in processors]

        raml_type = (props.get('type', 'string') or 'string').lower()
        if raml_type not in type_fields:
            raise ValueError('Unknown type: {}'.format(raml_type))

        field_cls = type_fields[raml_type]

        if field_cls is engine.Relationship:
            prepare_relationship(
                field_name, field_kwargs['document'], raml_resource)
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
    return metaclass(model_name, bases, attrs), auth_model


def setup_data_model(raml_resource, model_name):
    """ Setup storage/data model and return generated model class.

    Process follows these steps:
      * Resource schema is found and restructured by `resource_schema`.
      * Model class is generated from properties dict using util function
        `generate_model_cls`.

    Arguments:
        :raml_resource: Instance of pyraml.entities.RamlResource.
        :model_name: String representing model name.
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
        schema=schema,
        model_name=model_name,
        raml_resource=raml_resource,
    )


def handle_model_generation(raml_resource, route_name):
    """ Generates model name and runs `setup_data_model` to get
    or generate actual model class.

    Arguments:
        :raml_resource: Instance of pyraml.entities.RamlResource.
        :route_name: String name of the resource.
    """
    model_name = generate_model_name(route_name)
    try:
        return setup_data_model(raml_resource, model_name)
    except ValueError as ex:
        raise ValueError('{}: {}'.format(model_name, str(ex)))
