import logging

import six
from pyramid.security import (
    Allow, Deny,
    Everyone, Authenticated,
    ALL_PERMISSIONS)
from nefertari.acl import CollectionACL
from nefertari.resource import PERMISSIONS
from nefertari.elasticsearch import ES

from .utils import resolve_to_callable, is_callable_tag


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


def validate_permissions(perms):
    """ Validate :perms: contains valid permissions.

    :param perms: List of permission names or ALL_PERMISSIONS.
    """
    if not isinstance(perms, (list, tuple)):
        perms = [perms]
    valid_perms = set(PERMISSIONS.values())
    if ALL_PERMISSIONS in perms:
        return perms
    if set(perms) - valid_perms:
        raise ValueError(
            'Invalid ACL permission names. Valid permissions '
            'are: {}'.format(', '.join(valid_perms)))
    return perms


def parse_permissions(perms):
    """ Parse permissions ("perms") which are either exact permission
    names or the keyword 'all'.

    :param perms: List or comma-separated string of nefertari permission
        names, or 'all'
    """
    if isinstance(perms, six.string_types):
        perms = perms.split(',')
    perms = [perm.strip().lower() for perm in perms]
    if 'all' in perms:
        return ALL_PERMISSIONS
    return validate_permissions(perms)


def parse_acl(acl_string):
    """ Parse raw string :acl_string: of RAML-defined ACLs.

    If :acl_string: is blank or None, all permissions are given.
    Values of ACL action and principal are parsed using `actions` and
    `special_principals` maps and are looked up after `strip()` and
    `lower()`.

    ACEs in :acl_string: may be separated by newlines or semicolons.
    Action, principal and permission lists must be separated by spaces.
    Permissions must be comma-separated.
    E.g. 'allow everyone view,create,update' and 'deny authenticated delete'

    :param acl_string: Raw RAML string containing defined ACEs.
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
            raise ValueError(
                'Unknown ACL action: {}. Valid actions: {}'.format(
                    action_str, list(actions.keys())))

        # Process principal
        princ_str = princ_str.strip().lower()
        if princ_str in special_principals:
            principal = special_principals[princ_str]
        elif is_callable_tag(princ_str):
            principal = resolve_to_callable(princ_str)
        else:
            principal = princ_str

        # Process permissions
        permissions = parse_permissions(perms)

        result_acl.append((action, principal, permissions))

    return result_acl


class BaseACL(CollectionACL):
    """ ACL Base class. """

    es_based = False
    _collection_acl = (ALLOW_ALL, )
    _item_acl = (ALLOW_ALL, )

    def _apply_callables(self, acl, obj=None):
        """ Iterate over ACEs from :acl: and apply callable principals
        if any.

        Principals are passed 3 arguments on call:
            :ace: Single ACE object that looks like (action, callable,
                permission or [permission])
            :request: Current request object
            :obj: Object instance to be accessed via the ACL
        Principals must return a single ACE or a list of ACEs.

        :param acl: Sequence of valid Pyramid ACEs which will be processed
        :param obj: Object to be accessed via the ACL
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
                ace = [(a, b, validate_permissions(c)) for a, b, c in ace]
            else:
                ace = [ace]
            new_acl += ace
        return tuple(new_acl)

    def __acl__(self):
        """ Apply callables to `self._collection_acl` and return result. """
        return self._apply_callables(acl=self._collection_acl)

    def generate_item_acl(self, item):
        acl = self._apply_callables(
            acl=self._item_acl,
            obj=item)
        if acl is None:
            acl = self.__acl__()
        return acl

    def item_acl(self, item):
        """ Apply callables to `self._item_acl` and return result. """
        return self.generate_item_acl(item)

    def item_db_id(self, key):
        # ``self`` can be used for current authenticated user key
        if key != 'self':
            return key
        user = getattr(self.request, 'user', None)
        if user is None or not isinstance(user, self.item_model):
            return key
        return getattr(user, user.pk_field())

    def __getitem__(self, key):
        """ Get item using method depending on value of `self.es_based` """
        if not self.es_based:
            return super(BaseACL, self).__getitem__(key)
        return self.getitem_es(self.item_db_id(key))

    def getitem_es(self, key):
        es = ES(self.item_model.__name__)
        obj = es.get_item(id=key)
        obj.__acl__ = self.item_acl(obj)
        obj.__parent__ = self
        obj.__name__ = key
        return obj


class DatabaseACLMixin(object):
    """ Mixin to be used when ACLs are stored in database. """

    def item_acl(self, item):
        """ Objectify ACL if ES is used or call item.get_acl() if
        db is used.
        """
        if self.es_based:
            from nefertari_guards.elasticsearch import get_es_item_acl
            return get_es_item_acl(item)
        return super(DatabaseACLMixin, self).item_acl(item)

    def getitem_es(self, key):
        """ Override to support ACL filtering.

        To do so: passes `self.request` to `get_item` and uses
        `ACLFilterES`.
        """
        from nefertari_guards.elasticsearch import ACLFilterES
        es = ACLFilterES(self.item_model.__name__)
        params = {
            'id': key,
            'request': self.request,
        }
        obj = es.get_item(**params)
        obj.__acl__ = self.item_acl(obj)
        obj.__parent__ = self
        obj.__name__ = key
        return obj


def generate_acl(config, model_cls, raml_resource, es_based=True):
    """ Generate an ACL.

    Generated ACL class has a `item_model` attribute set to
    :model_cls:.

    ACLs used for collection and item access control are generated from a
    first security scheme with type `x-ACL`.
    If :raml_resource: has no x-ACL security schemes defined then ALLOW_ALL
    ACL is used.
    If the `collection` or `item` settings are empty, then ALLOW_ALL ACL
    is used.

    :param model_cls: Generated model class
    :param raml_resource: Instance of ramlfications.raml.ResourceNode
        for which ACL is being generated
    :param es_based: Boolean inidicating whether ACL should query ES or
        not when getting an object
    """
    schemes = raml_resource.security_schemes or []
    schemes = [sch for sch in schemes if sch.type == 'x-ACL']

    if not schemes:
        collection_acl = item_acl = []
        log.debug('No ACL scheme applied. Using ACL: {}'.format(item_acl))
    else:
        sec_scheme = schemes[0]
        log.debug('{} ACL scheme applied'.format(sec_scheme.name))
        settings = sec_scheme.settings or {}
        collection_acl = parse_acl(acl_string=settings.get('collection'))
        item_acl = parse_acl(acl_string=settings.get('item'))

    class GeneratedACLBase(object):
        item_model = model_cls

        def __init__(self, request, es_based=es_based):
            super(GeneratedACLBase, self).__init__(request=request)
            self.es_based = es_based
            self._collection_acl = collection_acl
            self._item_acl = item_acl

    bases = [GeneratedACLBase]
    if config.registry.database_acls:
        from nefertari_guards.acl import DatabaseACLMixin as GuardsMixin
        bases += [DatabaseACLMixin, GuardsMixin]
    bases.append(BaseACL)

    return type('GeneratedACL', tuple(bases), {})
