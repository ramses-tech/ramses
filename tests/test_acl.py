import pytest
from mock import Mock, patch, call
from pyramid.security import (
    Allow, Deny,
    Everyone, Authenticated,
    ALL_PERMISSIONS)

from ramses import acl


class TestACLHelpers(object):
    methods_map = {'get': 'index', 'post': 'create'}

    def test_methods_to_perms_all_permissions(self):
        perms = acl.methods_to_perms('all,get,post', self.methods_map)
        assert perms is ALL_PERMISSIONS

    def test_methods_to_perms_invalid_perm_name(self):
        with pytest.raises(ValueError) as ex:
            acl.methods_to_perms('foo,post', self.methods_map)
        expected = ("Unknown method name in permissions: "
                    "['foo', 'post']")
        assert expected in str(ex.value)

    def test_methods_to_perms(self):
        perms = acl.methods_to_perms('get', self.methods_map)
        assert perms == ['index']
        perms = acl.methods_to_perms('get,post', self.methods_map)
        assert perms == ['index', 'create']

    def test_parse_acl_no_string(self):
        perms = acl.parse_acl('', self.methods_map)
        assert perms == [(Allow, Everyone, ALL_PERMISSIONS)]

    def test_parse_acl_unknown_action(self):
        with pytest.raises(ValueError) as ex:
            acl.parse_acl('foobar admin all', self.methods_map)
        assert 'Unknown ACL action: foobar' in str(ex.value)

    @patch.object(acl, 'methods_to_perms')
    def test_parse_acl_multiple_values(self, mock_perms):
        mock_perms.return_value = 'Foo'
        perms = acl.parse_acl(
            'allow everyone read,write;allow authenticated all',
            self.methods_map)
        mock_perms.assert_has_calls([
            call(['read', 'write'], self.methods_map),
            call(['all'], self.methods_map),
        ])
        assert perms == [
            (Allow, Everyone, 'Foo'),
            (Allow, Authenticated, 'Foo'),
        ]

    @patch.object(acl, 'methods_to_perms')
    def test_parse_acl_special_principal(self, mock_perms):
        mock_perms.return_value = 'Foo'
        perms = acl.parse_acl('allow everyone all', self.methods_map)
        mock_perms.assert_called_once_with(['all'], self.methods_map)
        assert perms == [(Allow, Everyone, 'Foo')]

    @patch.object(acl, 'methods_to_perms')
    def test_parse_acl_group_principal(self, mock_perms):
        mock_perms.return_value = 'Foo'
        perms = acl.parse_acl('allow admin all', self.methods_map)
        mock_perms.assert_called_once_with(['all'], self.methods_map)
        assert perms == [(Allow, 'g:admin', 'Foo')]

    @patch.object(acl, 'registry')
    @patch.object(acl, 'methods_to_perms')
    def test_parse_acl_callable_principal(self, mock_perms, mock_registry):
        mock_perms.return_value = 'Foo'
        mock_registry.get.return_value = 'registry callable'
        perms = acl.parse_acl('allow {{my_user}} all', self.methods_map)
        mock_perms.assert_called_once_with(['all'], self.methods_map)
        mock_registry.get.assert_called_once_with('my_user')
        assert perms == [(Allow, 'registry callable', 'Foo')]
