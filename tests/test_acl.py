import pytest
from mock import Mock, patch, call
from pyramid.security import (
    Allow, Deny,
    Everyone, Authenticated,
    ALL_PERMISSIONS)

from ramses import acl

from .fixtures import config_mock


class TestACLHelpers(object):
    def test_validate_permissions_all_perms(self):
        perms = ALL_PERMISSIONS
        assert acl.validate_permissions(perms) == [perms]
        assert acl.validate_permissions([perms]) == [perms]

    def test_validate_permissions_valid(self):
        perms = ['update', 'delete']
        assert acl.validate_permissions(perms) == perms

    def test_validate_permissions_invalid(self):
        with pytest.raises(ValueError) as ex:
            acl.validate_permissions(['foobar'])
        assert 'Invalid ACL permission names' in str(ex.value)

    def test_parse_permissions_all_permissions(self):
        perms = acl.parse_permissions('all,view,create')
        assert perms is ALL_PERMISSIONS

    def test_parse_permissions_invalid_perm_name(self):
        with pytest.raises(ValueError) as ex:
            acl.parse_permissions('foo,create')
        expected = ('Invalid ACL permission names. Valid '
                    'permissions are: ')
        assert expected in str(ex.value)

    def test_parse_permissions(self):
        perms = acl.parse_permissions('view')
        assert perms == ['view']
        perms = acl.parse_permissions('view,create')
        assert sorted(perms) == ['create', 'view']

    def test_parse_acl_no_string(self):
        perms = acl.parse_acl('')
        assert perms == [acl.ALLOW_ALL]

    def test_parse_acl_unknown_action(self):
        with pytest.raises(ValueError) as ex:
            acl.parse_acl('foobar admin all')
        assert 'Unknown ACL action: foobar' in str(ex.value)

    @patch.object(acl, 'parse_permissions')
    def test_parse_acl_multiple_values(self, mock_perms):
        mock_perms.return_value = 'Foo'
        perms = acl.parse_acl(
            'allow everyone read,write;allow authenticated all')
        mock_perms.assert_has_calls([
            call(['read', 'write']),
            call(['all']),
        ])
        assert sorted(perms) == sorted([
            (Allow, Everyone, 'Foo'),
            (Allow, Authenticated, 'Foo'),
        ])

    @patch.object(acl, 'parse_permissions')
    def test_parse_acl_special_principal(self, mock_perms):
        mock_perms.return_value = 'Foo'
        perms = acl.parse_acl('allow everyone all')
        mock_perms.assert_called_once_with(['all'])
        assert perms == [(Allow, Everyone, 'Foo')]

    @patch.object(acl, 'parse_permissions')
    def test_parse_acl_group_principal(self, mock_perms):
        mock_perms.return_value = 'Foo'
        perms = acl.parse_acl('allow g:admin all')
        mock_perms.assert_called_once_with(['all'])
        assert perms == [(Allow, 'g:admin', 'Foo')]

    @patch.object(acl, 'resolve_to_callable')
    @patch.object(acl, 'parse_permissions')
    def test_parse_acl_callable_principal(self, mock_perms, mock_res):
        mock_perms.return_value = 'Foo'
        mock_res.return_value = 'registry callable'
        perms = acl.parse_acl('allow {{my_user}} all')
        mock_perms.assert_called_once_with(['all'])
        mock_res.assert_called_once_with('{{my_user}}')
        assert perms == [(Allow, 'registry callable', 'Foo')]


@patch.object(acl, 'parse_acl')
class TestGenerateACL(object):

    def test_no_security(self, mock_parse):
        config = config_mock()
        acl_cls = acl.generate_acl(
            config, model_cls='Foo',
            raml_resource=Mock(security_schemes=[]),
            es_based=True)
        assert acl_cls.item_model == 'Foo'
        assert issubclass(acl_cls, acl.BaseACL)
        instance = acl_cls(request=None)
        assert instance.es_based
        assert instance._collection_acl == []
        assert instance._item_acl == []
        assert not mock_parse.called

    def test_wrong_security_scheme_type(self, mock_parse):
        raml_resource = Mock(security_schemes=[
            Mock(type='x-Foo', settings={'collection': 4, 'item': 7})
        ])
        config = config_mock()
        acl_cls = acl.generate_acl(
            config, model_cls='Foo',
            raml_resource=raml_resource,
            es_based=False)
        assert not mock_parse.called
        assert acl_cls.item_model == 'Foo'
        assert issubclass(acl_cls, acl.BaseACL)
        instance = acl_cls(request=None)
        assert not instance.es_based
        assert instance._collection_acl == []
        assert instance._item_acl == []

    def test_correct_security_scheme(self, mock_parse):
        raml_resource = Mock(security_schemes=[
            Mock(type='x-ACL', settings={'collection': 4, 'item': 7})
        ])
        config = config_mock()
        acl_cls = acl.generate_acl(
            config, model_cls='Foo',
            raml_resource=raml_resource,
            es_based=False)
        mock_parse.assert_has_calls([
            call(acl_string=4),
            call(acl_string=7),
        ])
        instance = acl_cls(request=None)
        assert instance._collection_acl == mock_parse()
        assert instance._item_acl == mock_parse()
        assert not instance.es_based

    def test_database_acls_option(self, mock_parse):
        raml_resource = Mock(security_schemes=[
            Mock(type='x-ACL', settings={'collection': 4, 'item': 7})
        ])
        kwargs = dict(
            model_cls='Foo',
            raml_resource=raml_resource,
            es_based=False,
        )
        config = config_mock()
        config.registry.database_acls = False
        acl_cls = acl.generate_acl(config, **kwargs)
        assert not issubclass(acl_cls, acl.DatabaseACLMixin)
        config.registry.database_acls = True
        acl_cls = acl.generate_acl(config, **kwargs)
        assert issubclass(acl_cls, acl.DatabaseACLMixin)


class TestBaseACL(object):

    def test_init(self):
        obj = acl.BaseACL(request='Foo')
        assert obj.item_model is None
        assert obj._collection_acl == (acl.ALLOW_ALL,)
        assert obj._item_acl == (acl.ALLOW_ALL,)
        assert obj.request == 'Foo'

    def test_apply_callables_no_callables(self):
        obj = acl.BaseACL('req')
        new_acl = obj._apply_callables(
            acl=[('foo', 'bar', 'baz')],
            obj='obj')
        assert new_acl == (('foo', 'bar', 'baz'),)

    @patch.object(acl, 'validate_permissions')
    def test_apply_callables(self, mock_meth):
        mock_meth.return_value = '123'
        principal = Mock(return_value=(7, 8, 9))
        obj = acl.BaseACL('req')
        new_acl = obj._apply_callables(
            acl=[('foo', principal, 'bar')],
            obj='obj')
        assert new_acl == ((7, 8, '123'),)
        principal.assert_called_once_with(
            ace=('foo', principal, 'bar'),
            request='req',
            obj='obj')
        mock_meth.assert_called_once_with(9)

    @patch.object(acl, 'parse_permissions')
    def test_apply_callables_principal_returns_none(self, mock_meth):
        mock_meth.return_value = '123'
        principal = Mock(return_value=None)
        obj = acl.BaseACL('req')
        new_acl = obj._apply_callables(
            acl=[('foo', principal, 'bar')],
            obj='obj')
        assert new_acl == ()
        principal.assert_called_once_with(
            ace=('foo', principal, 'bar'),
            request='req',
            obj='obj')
        assert not mock_meth.called

    @patch.object(acl, 'validate_permissions')
    def test_apply_callables_principal_returns_list(self, mock_meth):
        mock_meth.return_value = '123'
        principal = Mock(return_value=[(7, 8, 9)])
        obj = acl.BaseACL('req')
        new_acl = obj._apply_callables(
            acl=[('foo', principal, 'bar')],
            obj='obj')
        assert new_acl == ((7, 8, '123'),)
        principal.assert_called_once_with(
            ace=('foo', principal, 'bar'),
            request='req',
            obj='obj')
        mock_meth.assert_called_once_with(9)

    def test_apply_callables_functional(self):
        obj = acl.BaseACL('req')
        principal = lambda ace, request, obj: [(Allow, Everyone, 'view')]
        new_acl = obj._apply_callables(
            acl=[(Deny, principal, ALL_PERMISSIONS)],
        )
        assert new_acl == ((Allow, Everyone, ['view']),)

    def test_magic_acl(self):
        obj = acl.BaseACL('req')
        obj._collection_acl = [(1, 2, 3)]
        obj._apply_callables = Mock()
        result = obj.__acl__()
        obj._apply_callables.assert_called_once_with(
            acl=[(1, 2, 3)],
        )
        assert result == obj._apply_callables()

    def test_item_acl(self):
        obj = acl.BaseACL('req')
        obj._item_acl = [(1, 2, 3)]
        obj._apply_callables = Mock()
        result = obj.item_acl('foobar')
        obj._apply_callables.assert_called_once_with(
            acl=[(1, 2, 3)],
            obj='foobar'
        )
        assert result == obj._apply_callables()

    def test_magic_getitem_es_based(self):
        obj = acl.BaseACL('req')
        obj.item_db_id = Mock(return_value=42)
        obj.getitem_es = Mock()
        obj.es_based = True
        obj.__getitem__(1)
        obj.item_db_id.assert_called_once_with(1)
        obj.getitem_es.assert_called_once_with(42)

    def test_magic_getitem_db_based(self):
        obj = acl.BaseACL('req')
        obj.item_db_id = Mock(return_value=42)
        obj.item_model = Mock()
        obj.item_model.pk_field.return_value = 'id'
        obj.es_based = False
        obj.__getitem__(1)
        obj.item_db_id.assert_called_once_with(1)

    @patch('ramses.acl.ES')
    def test_getitem_es(self, mock_es):
        found_obj = Mock()
        es_obj = Mock()
        es_obj.get_item.return_value = found_obj
        mock_es.return_value = es_obj
        obj = acl.BaseACL('req')
        obj.item_model = Mock(__name__='Foo')
        obj.item_model.pk_field.return_value = 'myname'
        obj.item_acl = Mock()
        value = obj.getitem_es(key='varvar')
        mock_es.assert_called_with('Foo')
        es_obj.get_item.assert_called_once_with(id='varvar')
        obj.item_acl.assert_called_once_with(found_obj)
        assert value.__acl__ == obj.item_acl()
        assert value.__parent__ is obj
        assert value.__name__ == 'varvar'
