
def generate_acl(context_cls, base_cls):
    """ Generate an ACL.

    Generated ACL is a subclass of `base_cls` and has `__context_class__`
    attribute set to `context_cls`.

    Arguments:
        :context_cls: Generated model class.
        :base_cls: ACL class to be inherited. E.g. nefertari.acl.GuestACL.
    """
    class GeneratedACL(base_cls):
        __context_class__ = context_cls
    return GeneratedACL
