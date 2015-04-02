from nefertari import engine as eng


"""
Map of RAML types names to nefertari.engine fields.

"""
type_fields = {
    'string':   eng.StringField,
    'number':   eng.FloatField,
    'integer':  eng.IntegerField,
    'boolean':  eng.BooleanField,
    'date':     eng.DateTimeField,
    'file':     eng.BinaryField,
    'object':   eng.Relationship,
    # 'array':    eng.ListField,  # Not implemented in sqla yet
}


def get_existing_model(model_name):
    """ Try to find existing model class named `model_name`.

    Arguments:
        :model_name: String name of the model class.
    """
    try:
        model_cls = eng.get_document_cls(model_name)
        print('Model `{}` already exists. Using existing one')
        return model_cls
    except ValueError:
        print('Model `{}` does not exist'.format(model_name))


def generate_model_cls(properties, model_name, es_based=True):
    """ Generate model class.

    Engine DB field types are determined using `type_fields` and only those
    types may be used.
    Assumes field is a Primary Key, if its name is 'id'.

    Arguments:
        :properties: Dictionary of DB schema fields which looks like
            {field_name: {required: boolean, type: type_name}, ...}
        :model_name: String that is used as new model's name.
        :es_based: Boolean indicating if generated model should be a
            subclass of Elasticsearch-based document class or not.
            It True, ESBaseDocument is used; BaseDocument is used otherwise.
            Defaults to True.
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
        field_kwargs = {
            'required': props.get('required', False) or False
        }
        raml_type = (props.get('type', 'string') or 'string').lower()
        if raml_type not in type_fields:
            raise ValueError('Unknown type: {}'.format(raml_type))

        # Assume field is a Primary Key, if its name is 'id'
        if field_name.lower() == 'id':
            field_cls = eng.PrimaryKeyField
        else:
            field_cls = type_fields[raml_type]

        attrs[field_name] = field_cls(**field_kwargs)

    # Generate new model class
    return metaclass(model_name, bases, attrs)
