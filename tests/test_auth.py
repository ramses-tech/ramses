import pytest
from mock import Mock, patch

from nefertari.utils import dictset
from pyramid.security import Allow, ALL_PERMISSIONS

from .fixtures import engine_mock, guards_engine_mock


@pytest.mark.usefixtures('engine_mock')
class TestACLAssignRegisterMixin(object):
    def _dummy_view(self):
        from ramses import auth

        class DummyBase(object):
            def register(self, *args, **kwargs):
                return 1

        class DummyView(auth.ACLAssignRegisterMixin, DummyBase):
            def __init__(self, *args, **kwargs):
                super(DummyView, self).__init__(*args, **kwargs)
                self.Model = Mock()
                self.request = Mock(_user=Mock())
                self.request.registry._model_collections = {}
        return DummyView

    def test_register_acl_present(self):
        DummyView = self._dummy_view()
        view = DummyView()
        view.request._user._acl = ['a']
        assert view.register() == 1
        assert view.request._user._acl == ['a']

    def test_register_no_model_collection(self):
        DummyView = self._dummy_view()
        view = DummyView()
        view.Model.__name__ = 'Foo'
        view.request._user._acl = []
        assert view.register() == 1
        assert view.request._user._acl == []

    def test_register_acl_set(self, guards_engine_mock):
        DummyView = self._dummy_view()
        view = DummyView()
        view.Model.__name__ = 'Foo'
        resource = Mock()
        view.request.registry._model_collections['Foo'] = resource
        view.request._user._acl = []
        assert view.register() == 1
        factory = resource.view._factory
        factory.assert_called_once_with(view.request)
        factory().generate_item_acl.assert_called_once_with(
            view.request._user)
        guards_engine_mock.ACLField.stringify_acl.assert_called_once_with(
            factory().generate_item_acl())
        view.request._user.update.assert_called_once_with(
            {'_acl': guards_engine_mock.ACLField.stringify_acl()})


@pytest.mark.usefixtures('engine_mock')
class TestSetupTicketPolicy(object):

    def test_no_secret(self):
        from ramses import auth
        with pytest.raises(ValueError) as ex:
            auth._setup_ticket_policy(config='', params={})
        expected = 'Missing required security scheme settings: secret'
        assert expected == str(ex.value)

    @patch('ramses.auth.AuthTktAuthenticationPolicy')
    def test_params_converted(self, mock_policy):
        from ramses import auth
        params = dictset(
            secure=True,
            include_ip=True,
            http_only=False,
            wild_domain=True,
            debug=True,
            parent_domain=True,
            secret='my_secret_setting'
        )
        auth_model = Mock()
        config = Mock()
        config.registry.settings = {'my_secret_setting': 12345}
        config.registry.auth_model = auth_model
        auth._setup_ticket_policy(config=config, params=params)
        mock_policy.assert_called_once_with(
            include_ip=True, secure=True, parent_domain=True,
            callback=auth_model.get_groups_by_userid, secret=12345,
            wild_domain=True, debug=True, http_only=False
        )

    @patch('ramses.auth.AuthTktAuthenticationPolicy')
    def test_request_method_added(self, mock_policy):
        from ramses import auth
        config = Mock()
        config.registry.settings = {'my_secret': 12345}
        config.registry.auth_model = Mock()
        policy = auth._setup_ticket_policy(
            config=config, params={'secret': 'my_secret'})
        config.add_request_method.assert_called_once_with(
            config.registry.auth_model.get_authuser_by_userid,
            'user', reify=True)
        assert policy == mock_policy()

    @patch('ramses.auth.AuthTktAuthenticationPolicy')
    def test_routes_views_added(self, mock_policy):
        from ramses import auth
        config = Mock()
        config.registry.settings = {'my_secret': 12345}
        config.registry.auth_model = Mock()
        root = Mock()
        config.get_root_resource.return_value = root
        auth._setup_ticket_policy(
            config=config, params={'secret': 'my_secret'})
        assert root.add.call_count == 3
        login, logout, register = root.add.call_args_list
        login_kwargs = login[1]
        assert sorted(login_kwargs.keys()) == sorted([
            'view', 'prefix', 'factory'])
        assert login_kwargs['prefix'] == 'auth'
        assert login_kwargs['factory'] == 'nefertari.acl.AuthenticationACL'

        logout_kwargs = logout[1]
        assert sorted(logout_kwargs.keys()) == sorted([
            'view', 'prefix', 'factory'])
        assert logout_kwargs['prefix'] == 'auth'
        assert logout_kwargs['factory'] == 'nefertari.acl.AuthenticationACL'

        register_kwargs = register[1]
        assert sorted(register_kwargs.keys()) == sorted([
            'view', 'prefix', 'factory'])
        assert register_kwargs['prefix'] == 'auth'
        assert register_kwargs['factory'] == 'nefertari.acl.AuthenticationACL'


@pytest.mark.usefixtures('engine_mock')
class TestSetupApiKeyPolicy(object):

    @patch('ramses.auth.ApiKeyAuthenticationPolicy')
    def test_policy_params(self, mock_policy):
        from ramses import auth
        auth_model = Mock()
        config = Mock()
        config.registry.auth_model = auth_model
        policy = auth._setup_apikey_policy(config, {'foo': 'bar'})
        mock_policy.assert_called_once_with(
            foo='bar', check=auth_model.get_groups_by_token,
            credentials_callback=auth_model.get_token_credentials,
            user_model=auth_model,
        )
        assert policy == mock_policy()

    @patch('ramses.auth.ApiKeyAuthenticationPolicy')
    def test_routes_views_added(self, mock_policy):
        from ramses import auth
        auth_model = Mock()
        config = Mock()
        config.registry.auth_model = auth_model
        root = Mock()
        config.get_root_resource.return_value = root
        auth._setup_apikey_policy(config, {})
        assert root.add.call_count == 3
        token, reset_token, register = root.add.call_args_list
        token_kwargs = token[1]
        assert sorted(token_kwargs.keys()) == sorted([
            'view', 'prefix', 'factory'])
        assert token_kwargs['prefix'] == 'auth'
        assert token_kwargs['factory'] == 'nefertari.acl.AuthenticationACL'

        reset_token_kwargs = reset_token[1]
        assert sorted(reset_token_kwargs.keys()) == sorted([
            'view', 'prefix', 'factory'])
        assert reset_token_kwargs['prefix'] == 'auth'
        assert reset_token_kwargs['factory'] == 'nefertari.acl.AuthenticationACL'

        register_kwargs = register[1]
        assert sorted(register_kwargs.keys()) == sorted([
            'view', 'prefix', 'factory'])
        assert register_kwargs['prefix'] == 'auth'
        assert register_kwargs['factory'] == 'nefertari.acl.AuthenticationACL'


@pytest.mark.usefixtures('engine_mock')
class TestSetupAuthPolicies(object):

    def test_not_secured(self):
        from ramses import auth
        raml_data = Mock(secured_by=[None])
        config = Mock()
        auth.setup_auth_policies(config, raml_data)
        assert not config.set_authentication_policy.called
        assert not config.set_authorization_policy.called

    def test_not_defined_security_scheme(self):
        from ramses import auth
        scheme = Mock()
        scheme.name = 'foo'
        raml_data = Mock(secured_by=['zoo'], security_schemes=[scheme])
        with pytest.raises(ValueError) as ex:
            auth.setup_auth_policies('asd', raml_data)
        expected = 'Undefined security scheme used in `secured_by`: zoo'
        assert expected == str(ex.value)

    def test_not_supported_scheme_type(self):
        from ramses import auth
        scheme = Mock(type='asd123')
        scheme.name = 'foo'
        raml_data = Mock(secured_by=['foo'], security_schemes=[scheme])
        with pytest.raises(ValueError) as ex:
            auth.setup_auth_policies(None, raml_data)
        expected = 'Unsupported security scheme type: asd123'
        assert expected == str(ex.value)

    @patch('ramses.auth.ACLAuthorizationPolicy')
    def test_policies_calls(self, mock_acl):
        from ramses import auth
        scheme = Mock(type='mytype', settings={'name': 'user1'})
        scheme.name = 'foo'
        raml_data = Mock(secured_by=['foo'], security_schemes=[scheme])
        config = Mock()
        mock_setup = Mock()
        with patch.dict(auth.AUTHENTICATION_POLICIES, {'mytype': mock_setup}):
            auth.setup_auth_policies(config, raml_data)
        mock_setup.assert_called_once_with(config, {'name': 'user1'})
        config.set_authentication_policy.assert_called_once_with(
            mock_setup())
        mock_acl.assert_called_once_with()
        config.set_authorization_policy.assert_called_once_with(
            mock_acl())


@pytest.mark.usefixtures('engine_mock')
class TestHelperFunctions(object):

    def test_create_system_user_key_error(self):
        from ramses import auth
        config = Mock()
        config.registry.settings = {}
        auth.create_system_user(config)
        assert not config.registry.auth_model.get_or_create.called

    @patch('ramses.auth.transaction')
    @patch('ramses.auth.cryptacular')
    def test_create_system_user_exists(self, mock_crypt, mock_trans):
        from ramses import auth
        encoder = mock_crypt.bcrypt.BCRYPTPasswordManager()
        encoder.encode.return_value = '654321'
        config = Mock()
        config.registry.settings = {
            'system.user': 'user12',
            'system.password': '123456',
            'system.email': 'user12@example.com',
        }
        config.registry.auth_model.get_or_create.return_value = (1, False)
        auth.create_system_user(config)
        assert not mock_trans.commit.called
        encoder.encode.assert_called_once_with('123456')
        config.registry.auth_model.get_or_create.assert_called_once_with(
            username='user12',
            defaults={
                'password': '654321',
                'email': 'user12@example.com',
                'groups': ['admin'],
                '_acl': [(Allow, 'g:admin', ALL_PERMISSIONS)],
            }
        )

    @patch('ramses.auth.transaction')
    @patch('ramses.auth.cryptacular')
    def test_create_system_user_created(self, mock_crypt, mock_trans):
        from ramses import auth
        encoder = mock_crypt.bcrypt.BCRYPTPasswordManager()
        encoder.encode.return_value = '654321'
        config = Mock()
        config.registry.settings = {
            'system.user': 'user12',
            'system.password': '123456',
            'system.email': 'user12@example.com',
        }
        config.registry.auth_model.get_or_create.return_value = (
            Mock(), True)
        auth.create_system_user(config)
        mock_trans.commit.assert_called_once_with()
        encoder.encode.assert_called_once_with('123456')
        config.registry.auth_model.get_or_create.assert_called_once_with(
            username='user12',
            defaults={
                'password': '654321',
                'email': 'user12@example.com',
                'groups': ['admin'],
                '_acl': [(Allow, 'g:admin', ALL_PERMISSIONS)],
            }
        )

    @patch('ramses.auth.create_system_user')
    def test_includeme(self, mock_create):
        from ramses import auth
        auth.includeme(config=1)
        mock_create.assert_called_once_with(1)
