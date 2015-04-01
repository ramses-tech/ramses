from nefertari import engine


"""
Map of RAML types names to nefertari.engine fields.

"""
type_fields = {
    'string':   engine.StringField,
    'number':   engine.FloatField,
    'integer':  engine.IntegerField,
    'boolean':  engine.BooleanField,
    'date':     engine.DateTimeField,
    'file':     engine.BinaryField,
}


def generate_model_cls(properties, model_name):
    """ Generate model class.

    Engine DB field types are determined using `type_fields` and only those
    types may be used.
    Assumes field is a Primary Key, if its name is 'id'.

    Arguments:
        :properties: Dictionary of DB schema fields which looks like
            {field_name: {required: boolean, type: type_name}, ...}
        :model_name: String that is used as new model's name.
    """
    metaclass = type(engine.BaseDocument)
    bases = (engine.BaseDocument,)
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
            field_cls = engine.PrimaryKeyField
        else:
            field_cls = type_fields[raml_type]

        attrs[field_name] = field_cls(**field_kwargs)

    # Generate new model class
    return metaclass(model_name, bases, attrs)
