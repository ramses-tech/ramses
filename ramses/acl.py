import logging

from nefertari.acl import GuestACL, AuthenticatedReadACL

from .utils import closest_secured_by


log = logging.getLogger(__name__)


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

        def __getitem__(self, key):
            """ Hack to use current nefertari ACLs usage logic but don't get
            an object from database here.

            We define a fake class that represents a resource and on which ACL
            values are set. Thus defined resource class allows us to have
            benefits of ACL and does not query the database.
            """
            class MockResource(object):
                pass

            obj = MockResource()
            obj.__acl__ = self.context_acl(obj)
            obj.__parent__ = self
            obj.__name__ = key
            return obj

    return GeneratedACL
