from nefertari import engine

from .utils import resource_model_name


type_fields = {
    'string':   engine.StringField,
    'number':   engine.FloatField,
    'integer':  engine.IntegerField,
    'boolean':  engine.BooleanField,
    'date':     engine.DateTimeField,
    'file':     engine.BinaryField,
}


def generate_model_cls(properties, resource):
    metaclass = type(engine.BaseDocument)
    cls_name = resource_model_name(resource)
    bases = (engine.BaseDocument,)
    attrs = {
        '__tablename__': cls_name.lower(),
    }

    # Generate fields from properties
    for field_name, props in properties:
        required = props.get('required', False) or False
        raml_type = (props.get('type', 'string') or 'string').lower()
        if raml_type not in type_fields:
            raise ValueError('Unknown type: {}'.format(raml_type))
        field_cls = type_fields[raml_type]
        attrs[field_name] = field_cls(
            required=required,
        )

    # Generate new model class
    return metaclass(cls_name, bases, attrs)
