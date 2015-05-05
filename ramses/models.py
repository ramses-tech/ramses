import logging

from nefertari import engine as eng
from nefertari.authentication.models import AuthModelDefaultMixin
from .utils import generate_model_name, find_dynamic_resource
from . import registry


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


auth_methods = set([
    'is_admin',
    'verify_password',
    'token_credentials',
    'groups_by_token',
    'authenticate_by_password',
    'groups_by_userid',
    'create_account',
    'authuser_by_userid',
    'authuser_by_name',
])


class RamsesAuthModelDefaultMixin(AuthModelDefaultMixin):

    def __getattribute__(self, name):
        super_get = super(RamsesAuthModelDefaultMixin, self).__getattribute__
        if name in auth_methods:
            try:
                key = '{}.{}'.format(self.__class__.__name__, name)
                return registry.get(key)
            except KeyError:
                return super_get(name)
        return super_get(name)


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
    from .generators import setup_data_model
    rel_model_name = generate_model_name(field_name)
    if get_existing_model(rel_model_name) is None:
        dynamic_res = find_dynamic_resource(raml_resource)
        subresources = getattr(dynamic_res, 'resources', {}) or {}
        subresources = {k.strip('/'): v for k, v in subresources.items()}
        if field_name not in subresources:
            raise ValueError('Model `{}` used in relationship `{}` is not '
                             'defined'.format(rel_model_name, field_name))
        setup_data_model(subresources[field_name], rel_model_name)


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
    base_cls = eng.ESBaseDocument if es_based else eng.BaseDocument
    metaclass = type(base_cls)
    auth_model = schema.get('auth_model', False)
    if auth_model:
        bases = (RamsesAuthModelDefaultMixin, base_cls)
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

        processors = field_kwargs.get('processors', [])
        field_kwargs['processors'] = [registry.get(name) for name in processors]

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
    return metaclass(str(model_name), bases, attrs), auth_model
