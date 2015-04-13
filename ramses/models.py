import logging

from nefertari import engine as eng

from .utils import generate_model_name, find_dynamic_resource
from .generators import setup_data_model


log = logging.getLogger(__name__)

"""
Map of RAML types names to nefertari.engine fields.

"""
type_fields = {
    'string':           eng.StringField,
    'float':            eng.FloatField,
    'integer':          eng.IntegerField,
    'boolean':          eng.BooleanField,
    'datetime':         eng.DateTimeField,
    'file':             eng.BinaryField,
    'relationship':     eng.Relationship,
    'dict':             eng.DictField,
    'foreign_key':      eng.ForeignKeyField,
    'big_integer':      eng.BigIntegerField,
    'date':             eng.DateField,
    'choice':           eng.ChoiceField,
    'interval':         eng.IntervalField,
    'decimal':          eng.DecimalField,
    'pickle':           eng.PickleField,
    'small_integer':    eng.SmallIntegerField,
    'text':             eng.TextField,
    'time':             eng.TimeField,
    'unicode':          eng.UnicodeField,
    'unicode_text':     eng.UnicodeTextField,
    'id_field':         eng.IdField,
    'list':             eng.ListField,
}


def get_existing_model(model_name):
    """ Try to find existing model class named `model_name`.

    Arguments:
        :model_name: String name of the model class.
    """
    try:
        model_cls = eng.get_document_cls(model_name)
        log.debug('Model `{}` already exists. Using existing one'.format(
            model_name))
        return model_cls
    except ValueError:
        log.debug('Model `{}` does not exist'.format(model_name))


def prepare_relationship(field_name, model_name, raml_resource):
    """ Create referenced model if not exists.

    When preparing relationship, we check to see if model that will be
    referenced already exists. If not, it is created so it would be possible
    to use it in relationship. Thus first usage of this model in RAML file
    must provide its schema in one of http methods that are assumed to contain
    full body schema.

    Arguments:
        :field_name: Name of the field that should become a `Relationship`.
        :model_name: Name of the model at which :field_name: will be defined.
        :raml_resource: Instance of pyraml.entities.RamlResource. Resource
            for which :model_name: will is being defined.
    """
    rel_model_name = generate_model_name(field_name)
    if get_existing_model(rel_model_name) is None:
        dynamic_res = find_dynamic_resource(raml_resource)
        subresources = getattr(dynamic_res, 'resources', {}) or {}
        subresources = {k.strip('/'): v for k, v in subresources.items()}
        if field_name not in subresources:
            raise ValueError('Model `{}` used in relationship `{}` is not '
                             'defined'.format(rel_model_name, field_name))
        setup_data_model(subresources[field_name], rel_model_name)


def generate_model_cls(properties, model_name, raml_resource, es_based=True):
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
    base_cls = eng.ESBaseDocument if es_based else eng.BaseDocument
    metaclass = type(base_cls)
    bases = (base_cls,)
    attrs = {
        '__tablename__': model_name.lower(),
    }

    # Generate fields from properties
    for field_name, props in properties.items():
        if field_name in attrs:
            continue

        field_kwargs = {
            'required': bool(props.get('required'))
        }
        field_kwargs.update(props.get('args', {}) or {})

        raml_type = (props.get('type', 'string') or 'string').lower()
        if raml_type not in type_fields:
            raise ValueError('Unknown type: {}'.format(raml_type))

        field_cls = type_fields[raml_type]

        if field_cls is eng.Relationship:
            prepare_relationship(field_name, model_name, raml_resource)
        if field_cls is eng.ForeignKeyField:
            key = 'ref_column_type'
            field_kwargs[key] = type_fields[field_kwargs[key]]
        if field_cls is eng.ListField:
            key = 'item_type'
            field_kwargs[key] = type_fields[field_kwargs[key]]

        attrs[field_name] = field_cls(**field_kwargs)

    # Generate new model class
    return metaclass(str(model_name), bases, attrs)
