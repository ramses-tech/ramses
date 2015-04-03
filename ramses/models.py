from nefertari import engine as eng

from .utils import generate_model_name, find_dymanic_resource
from .generators import setup_data_model


"""
Map of RAML types names to nefertari.engine fields.

"""
type_fields = {
    'string':       eng.StringField,
    'number':       eng.FloatField,
    'integer':      eng.IntegerField,
    'boolean':      eng.BooleanField,
    'date':         eng.DateTimeField,
    'file':         eng.BinaryField,
    'object':       eng.Relationship,
    'nested':       eng.DictField,
    'foreign_key':  eng.ForeignKeyField,
    # 'array':    eng.ListField,  # Not implemented in sqla yet
}


def get_existing_model(model_name):
    """ Try to find existing model class named `model_name`.

    Arguments:
        :model_name: String name of the model class.
    """
    try:
        model_cls = eng.get_document_cls(model_name)
        print('Model `{}` already exists. Using existing one'.format(
            model_name))
        return model_cls
    except ValueError:
        print('Model `{}` does not exist'.format(model_name))


def prepare_relationship(field_name, model_name, raml_resource):
    """ Prepare `Relationship` kwargs and create referenced model if not exists.

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
    field_kwargs = dict(
        document=rel_model_name,
        backref_name=model_name.lower(),
    )
    if get_existing_model(rel_model_name) is None:
        dynamic_res = find_dymanic_resource(raml_resource)
        subresources = getattr(dynamic_res, 'resources', {}) or {}
        subresources = {k.strip('/'): v for k, v in subresources.items()}
        if field_name not in subresources:
            raise ValueError('Model `{}` used in relationship `{}` is not '
                             'defined'.format(rel_model_name, field_name))
        setup_data_model(subresources[field_name], rel_model_name)
    return field_kwargs


def generate_model_cls(properties, model_name, raml_resource, es_based=True):
    """ Generate model class.

    Engine DB field types are determined using `type_fields` and only those
    types may be used.
    Assumes field is a Primary Key, if its name is 'id'.

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
    model_cls = get_existing_model(model_name)
    if model_cls is not None:
        return model_cls

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
            'required': props.get('required', False) or False
        }

        if 'title' in props:
            raml_type = 'nested'
        else:
            raml_type = (props.get('type', 'string') or 'string').lower()

        if raml_type not in type_fields:
            raise ValueError('Unknown type: {}'.format(raml_type))

        # Assume field is a Primary Key, if its name is 'id'
        if field_name.lower() == 'id':
            field_cls = eng.PrimaryKeyField
        else:
            field_cls = type_fields[raml_type]

        if field_cls is eng.Relationship:
            rel_kwargs = prepare_relationship(
                field_name, model_name, raml_resource)
            field_kwargs.update(rel_kwargs)
        elif field_cls is eng.ForeignKeyField:
            model, field = field_name.split('_')
            field_kwargs.update(
                ref_document=model.title(),
                ref_column='.'.join([model, field]),
            )

        attrs[field_name] = field_cls(**field_kwargs)

    # Generate new model class
    return metaclass(str(model_name), bases, attrs)
