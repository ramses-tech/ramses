import inflection


def generate_model_cls(properties, resource):
    from nefertari import engine
    metaclass = type(engine.BaseDocument)
    cls_name = inflection.camelize(resource.uid.replace(':', '_'))
    bases = (engine.BaseDocument,)
    attrs = {
        '__metaclass__': metaclass,
        '__tablename__': cls_name.lower(),
    }
