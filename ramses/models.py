import logging

from nefertari import engine
from nefertari.authentication.models import AuthModelDefaultMixin
from .utils import find_dynamic_resource
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
    must provide its schema in one of http methods that are assumed to contain
    a full body schema.

    Arguments:
        :field_name: Name of the field that should become a `Relationship`.
        :raml_resource: Instance of pyraml.entities.RamlResource. Resource
            for which :model_name: will is being defined.
    """
    from .generators import setup_data_model
    if get_existing_model(model_name) is None:
        dynamic_res = find_dynamic_resource(raml_resource)
        subresources = getattr(dynamic_res, 'resources', {}) or {}
        subresources = {k.strip('/'): v for k, v in subresources.items()}
        if field_name not in subresources:
            raise ValueError('Model `{}` used in relationship `{}` is not '
                             'defined'.format(model_name, field_name))
        setup_data_model(subresources[field_name], model_name)


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
    base_cls = engine.ESBaseDocument if es_based else engine.BaseDocument
    model_name = str(model_name)
    metaclass = type(base_cls)
    auth_model = schema.get('auth_model', False)
    if auth_model:
        bases = (AuthModelDefaultMixin, base_cls)
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

        for proc_key in ('before_validation', 'after_validation'):
            processors = field_kwargs.get(proc_key, [])
            field_kwargs[proc_key] = [
                registry.get(name) for name in processors]

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
