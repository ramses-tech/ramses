import logging

import six
from pyramid.security import (
    Allow, Deny,
    Everyone, Authenticated,
    ALL_PERMISSIONS)
from nefertari.acl import SelfParamMixin

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
ALLOW_ALL = (Allow, Everyone, ALL_PERMISSIONS)


def methods_to_perms(perms, methods_map):
    """ Convert permissions ("perms") which are either HTTP methods or
    the keyword 'all' into a set of valid Pyramid permissions.

    Arguments:
        :perms: List or comma-separated string of HTTP methods, or 'all'
        :methods_map: Map of HTTP methods to permission names (nefertari view
            methods)
    """
    if isinstance(perms, six.string_types):
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
                '{}'.format(perms, list(methods_map.keys())))


def parse_acl(acl_string, methods_map):
    """ Parse raw string :acl_string: of RAML-defined ACLs.

    If :acl_string: is blank or None, all permissions are given.
    Values of ACL action and principal are parsed using `actions` and
    `special_principals` maps and are looked up after `strip()` and `lower()`.

    ACEs in :acl_string: may be separated by newlines or semicolons.
    Action, principal and permission lists must be separated by spaces.
    Permissions must be comma-separated.
    E.g. 'allow everyone get,post,patch' and 'deny authenticated delete'

    Arguments:
        :acl_string: Raw RAML string containing defined ACEs.
        :methods_map: Map of HTTP methods to nefertari method handler names.
    """
    if not acl_string:
        return [ALLOW_ALL]

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
                action_str, list(actions.keys())))

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


class BaseACL(SelfParamMixin):
    """ ACL Base class. """
    __context_class__ = None
    collection_acl = None
    item_acl = None

    def __init__(self, request):
        super(BaseACL, self).__init__()
        self.request = request

    def _apply_callables(self, acl, methods_map, obj=None):
        """ Iterate over ACEs from :acl: and apply callable principals if any.

        Principals are passed 3 arguments on call:
            :ace: Single ACE object that looks like (action, callable,
                permission or [permission])
            :request: Current request object
            :obj: Object instance to be accessed via the ACL
        Principals must return a single ACE or a list of ACEs.

        Arguments:
            :acl: Sequence of valid Pyramid ACEs which will be processed
            :methods_map: Map of HTTP methods to nefertari view method names
                (permissions)
            :obj: Object to be accessed via the ACL
        """
        new_acl = []
        for i, ace in enumerate(acl):
            principal = ace[1]
            if six.callable(principal):
                ace = principal(ace=ace, request=self.request, obj=obj)
                if not ace:
                    continue
                if not isinstance(ace[0], (list, tuple)):
                    ace = [ace]
                ace = [(a, b, methods_to_perms(c, methods_map))
                       for a, b, c in ace]
            else:
                ace = [ace]
            new_acl += ace
        return new_acl

    def __acl__(self):
        """ Apply callables to `self.collection_acl` and return result. """
        return self._apply_callables(
            acl=self.collection_acl,
            methods_map=collection_methods)

    def context_acl(self, obj):
        """ Apply callables to `self.item_acl` and return result. """
        return self._apply_callables(
            acl=self.item_acl,
            methods_map=item_methods,
            obj=obj)

    def __getitem__(self, key):
        """ Get item using method depending on value of `self.es_based` """
        key = self.resolve_self_key(key)
        if self.es_based:
            return self.getitem_es(key=key)
        else:
            return self.getitem_db(key=key)

    def getitem_db(self, key):
        """ Get item with ID of :key: from database """
        pk_field = self.__context_class__.pk_field()
        obj = self.__context_class__.get_resource(
            **{pk_field: key})
        obj.__acl__ = self.context_acl(obj)
        obj.__parent__ = self
        obj.__name__ = key
        return obj

    def getitem_es(self, key):
        """ Get item with ID of :key: from elasticsearch """
        from nefertari.elasticsearch import ES
        es = ES(self.__context_class__.__name__)
        pk_field = self.__context_class__.pk_field()
        kwargs = {
            pk_field: key,
            '_limit': 1,
            '__raise_on_empty': True,
        }
        obj = es.get_collection(**kwargs)[0]
        obj.__acl__ = self.context_acl(obj)
        obj.__parent__ = self
        obj.__name__ = key
        return obj


def generate_acl(context_cls, raml_resource, parsed_raml, es_based=True):
    """ Generate an ACL.

    Generated ACL class has a `__context_class__` attribute set to :context_cls:.

    ACLs used for collection and item access control are generated from a
    security scheme which has a name of :raml_resource.securedBy[0]:.
    If :raml_resource: has no `securedBy` schemes defined then ALLOW_ALL ACL is
    used.
    If the `collection` or `item` settings are empty, then ALLOW_ALL ACL is used.

    Arguments:
        :context_cls: Generated model class
        :raml_resource: Instance of pyraml.entities.RamlResource for which
            ACL is being generated
        :parsed_raml: Whole parsed RAML object
        :es_based: Boolean inidicating whether ACL should query ES or not
            when getting an object
    """
    secured_by = raml_resource.securedBy or []

    if not secured_by:
        log.debug('No ACL scheme applied. Giving all permissions')
        collection_acl = item_acl = [ALLOW_ALL]
    else:
        log.debug('{} ACL scheme applied'.format(secured_by[0]))
        security_schemes = parsed_raml.securitySchemes or {}
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

    class GeneratedACL(BaseACL):
        __context_class__ = context_cls

        def __init__(self, request, es_based=es_based):
            super(GeneratedACL, self).__init__(request=request)
            self.es_based = es_based
            self.collection_acl = collection_acl
            self.item_acl = item_acl

    return GeneratedACL
