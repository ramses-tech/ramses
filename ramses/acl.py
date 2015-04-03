from nefertari.acl import GuestACL, AuthenticatedReadACL

from .utils import closest_secured_by


def generate_acl(context_cls, raml_resource):
    """ Generate an ACL.

    Generated ACL is a subclass of `base_cls` and has `__context_class__`
    attribute set to `context_cls`.

    Arguments:
        :context_cls: Generated model class.
        :raml_resource: Instance of pyraml.entities.RamlResource for which
            ACL is being generated.
    """
    secured_by = closest_secured_by(raml_resource)

    if secured_by and 'auth_read' in secured_by:
        base_cls = AuthenticatedReadACL
    else:
        base_cls = GuestACL

    class GeneratedACL(base_cls):
        __context_class__ = context_cls

    return GeneratedACL
