
def generate_acl(context_cls, base_cls):
    class GeneratedACL(base_cls):
        __context_class__ = context_cls
    return GeneratedACL
