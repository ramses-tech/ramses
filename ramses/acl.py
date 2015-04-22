import logging

from pyramid.security import (
    Allow, Deny,
    Everyone, Authenticated,
    ALL_PERMISSIONS, DENY_ALL)

from .views import collection_methods, item_methods
from . import registry


log = logging.getLogger(__name__)


actions = {
    'allow': Allow,
    'deny': Deny,
}
special_principals = {
    'everyone': Everyone,
    'authenticated': Authenticated,
}


def methods_to_perms(perms, methods_map):
    """ Convert permissions (perms) which are either HTTP methods or
    keyword 'all' to a set of valid Pyramid permissions.

    Arguments:
        :perms: List or comma-separated string of HTTP methods, or 'all'
        :methods_map: Map of HTTP methods to permission names (nefertari view
            methods)
    """
    if isinstance(perms, basestring):
        perms = perms.split(',')
    perms = [perm.strip().lower() for perm in perms]
    if 'all' in perms:
        return ALL_PERMISSIONS
    else:
        try:
            return [methods_map[p] for p in perms]
        except KeyError:
            raise ValueError(
                'Unknown method name in permissions: {}. Valid methods: '
                '{}'.format(perms, methods_map.keys()))


def parse_acl(acl_string, methods_map):
    """ Parse raw string :acl_string: of RAML-defined ACLs.

    If :acl_string: is blank or None, DENY_ALL is returned.
    Values of ACL action and principal are parsed using `actions` and
    `special_principals` maps and are looked up after `strip()` and `lower()`.

    ACEs in :acl_string: may be separated by newline or semicolon.
    Action, principal and permission list must be separated with space.
    Permissions must be separated with comma.
    E.g. 'allow everyone get,post,patch' and 'deny authenticated delete'

    Arguments:
        :acl_string: Raw RAML string containing defined ACEs.
        :methods_map: Map of HTTP methods to nefertari method handlers' names.
    """
    if not acl_string:
        return [DENY_ALL]

    aces_list = acl_string.replace('\n', ';').split(';')
    aces_list = [ace.strip().split(' ', 2) for ace in aces_list if ace]
    aces_list = [(a, b, c.split(',')) for a, b, c in aces_list]
    result_acl = []

    for action_str, princ_str, perms in aces_list:
        # Process action
        action_str = action_str.strip().lower()
        action = actions.get(action_str)
        if action is None:
            raise ValueError('Unknown ACL action: {}. Valid actions: {}'.format(
                action_str, actions.keys()))

        # Process principal
        princ_str = princ_str.strip().lower()
        if princ_str in special_principals:
            principal = special_principals[princ_str]
        elif princ_str.startswith('{{'):
            princ_str = princ_str.strip('{{').strip('}}').strip()
            principal = registry.get(princ_str)
        else:
            principal = 'g:' + princ_str

        # Process permissions
        permissions = methods_to_perms(perms, methods_map)

        result_acl.append((action, principal, permissions))

    return result_acl


def generate_acl(context_cls, raml_resource, parsed_raml):
    """ Generate an ACL.

    Generated ACL class has `__context_class__` attribute set to :context_cls:.

    ACLs used for collection and item access control are generated from a
    security scheme which has a name of :raml_resource.securedBy[0]:.
    If :raml_resource.securedBy[0]: is None, everyone gets ALL_PERMISSIONS.
    If :raml_resource: has no `securedBy` schemes defined DENY_ALL ACL is used.
    If `collection` or `item` setting is empty, it is assigned DENY_ALL ACL.

    Arguments:
        :context_cls: Generated model class
        :raml_resource: Instance of pyraml.entities.RamlResource for which
            ACL is being generated
        :parsed_raml: Whole parsed RAML object
    """
    security_schemes = parsed_raml.securitySchemes or {}
    secured_by = raml_resource.securedBy or []

    if not secured_by:
        log.debug('No ACL scheme applied. Denying all permissions')
        collection_acl = item_acl = [DENY_ALL]
    elif secured_by[0] is None:
        log.debug('null ACL scheme applied. Allowing all permissions')
        collection_acl = item_acl = [(Allow, Everyone, ALL_PERMISSIONS)]
    else:
        log.debug('{} ACL scheme applied'.format(secured_by[0]))
        sec_scheme = security_schemes.get(secured_by[0])
        if sec_scheme is None:
            raise ValueError('Undefined ACL security scheme: {}'.format(
                secured_by[0]))
        settings = sec_scheme.settings or {}
        collection_acl = parse_acl(
            acl_string=settings.get('collection'),
            methods_map=collection_methods)
        item_acl = parse_acl(
            acl_string=settings.get('item'),
            methods_map=item_methods)

    class GeneratedACL(object):
        __context_class__ = context_cls

        def __init__(self, request):
            super(GeneratedACL, self).__init__()
            self.request = request
            self.collection_acl = collection_acl
            self.item_acl = item_acl

        def _apply_callables(self, acl, methods_map, obj=None):
            new_acl = []
            for i, ace in enumerate(acl):
                principal = ace[1]
                if callable(principal):
                    ace = principal(ace=ace, request=self.request, obj=obj)
                    ace = [(a, b, methods_to_perms(c)) for a, b, c in ace]
                if ace and any(ace):
                    new_acl += ace
            return new_acl

        def __acl__(self):
            return self._apply_callables(
                acl=self.collection_acl,
                methods_map=collection_methods)

        def context_acl(self, obj):
            return self._apply_callables(
                acl=self.item_acl,
                methods_map=item_methods,
                obj=obj)

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
