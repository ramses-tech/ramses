import pytest
from mock import Mock, patch, call

from nefertari.utils import dictset

from .fixtures import engine_mock


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
            secure='true',
            include_ip='true',
            http_only='false',
            wild_domain='true',
            debug='true',
            parent_domain='true',
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
        auth._setup_ticket_policy(
            config=config, params={'secret': 'my_secret'})
        config.add_route.assert_has_calls([
            call('login', '/auth/login'),
            call('logout', '/auth/logout'),
            call('register', '/auth/register'),
        ])
        login, logout, register = config.add_view.call_args_list
        login_kwargs = login[1]
        assert sorted(login_kwargs.keys()) == sorted([
            'request_method', 'view', 'route_name', 'attr'])
        assert login_kwargs['route_name'] == 'login'
        assert login_kwargs['attr'] == 'login'
        assert login_kwargs['request_method'] == 'POST'

        logout_kwargs = logout[1]
        assert sorted(logout_kwargs.keys()) == sorted([
            'view', 'route_name', 'attr'])
        assert logout_kwargs['route_name'] == 'logout'
        assert logout_kwargs['attr'] == 'logout'

        register_kwargs = register[1]
        assert sorted(register_kwargs.keys()) == sorted([
            'request_method', 'view', 'route_name', 'attr'])
        assert register_kwargs['route_name'] == 'register'
        assert register_kwargs['attr'] == 'register'
        assert register_kwargs['request_method'] == 'POST'


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
        auth._setup_apikey_policy(config, {})
        config.add_route.assert_has_calls([
            call('token', '/auth/token'),
            call('reset_token', '/auth/reset_token'),
            call('register', '/auth/register'),
        ])

        token, reset_token, register = config.add_view.call_args_list
        token_kwargs = token[1]
        assert sorted(token_kwargs.keys()) == sorted([
            'request_method', 'view', 'route_name', 'attr'])
        assert token_kwargs['route_name'] == 'token'
        assert token_kwargs['attr'] == 'claim_token'
        assert token_kwargs['request_method'] == 'POST'

        reset_token_kwargs = reset_token[1]
        assert sorted(reset_token_kwargs.keys()) == sorted([
            'request_method', 'view', 'route_name', 'attr'])
        assert reset_token_kwargs['route_name'] == 'reset_token'
        assert reset_token_kwargs['attr'] == 'reset_token'
        assert reset_token_kwargs['request_method'] == 'POST'

        register_kwargs = register[1]
        assert sorted(register_kwargs.keys()) == sorted([
            'request_method', 'view', 'route_name', 'attr'])
        assert register_kwargs['route_name'] == 'register'
        assert register_kwargs['attr'] == 'register'
        assert register_kwargs['request_method'] == 'POST'


@pytest.mark.usefixtures('engine_mock')
class TestSetupAuthPolicies(object):

    def test_not_secured(self):
        from ramses import auth
        raml_data = Mock(securedBy=[None])
        config = Mock()
        auth.setup_auth_policies(config, raml_data)
        assert not config.set_authentication_policy.called
        assert not config.set_authorization_policy.called

    def test_not_defined_security_scheme(self):
        from ramses import auth
        raml_data = Mock(securedBy=['zoo'], securitySchemes={'foo': 'bar'})
        with pytest.raises(ValueError) as ex:
            auth.setup_auth_policies('asd', raml_data)
        expected = 'Not defined security scheme used in `securedBy`: zoo'
        assert expected == str(ex.value)

    def test_not_supported_scheme_type(self):
        from ramses import auth
        raml_data = Mock(
            securedBy=['foo'],
            securitySchemes={'foo': Mock(type='asd123')}
        )
        with pytest.raises(ValueError) as ex:
            auth.setup_auth_policies(None, raml_data)
        expected = 'Not supported security scheme type: asd123'
        assert expected == str(ex.value)

    @patch('ramses.auth.ACLAuthorizationPolicy')
    def test_policies_calls(self, mock_acl):
        from ramses import auth
        scheme = Mock(type='mytype', settings={'name': 'user1'})
        raml_data = Mock(
            securedBy=['foo'],
            securitySchemes={'foo': scheme}
        )
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

    def test_create_admin_user_key_error(self):
        from ramses import auth
        config = Mock()
        config.registry.settings = {}
        auth.create_admin_user(config)
        assert not config.registry.auth_model.get_or_create.called

    @patch('ramses.auth.transaction')
    def test_create_admin_user_exists(self, mock_trans):
        from ramses import auth
        config = Mock()
        config.registry.settings = {
            'system.user': 'user12',
            'system.password': '123456',
            'system.email': 'user12@example.com',
        }
        config.registry.auth_model.get_or_create.return_value = (1, False)
        auth.create_admin_user(config)
        assert not mock_trans.commit.called
        config.registry.auth_model.get_or_create.assert_called_once_with(
            username='user12',
            defaults={
                'password': '123456',
                'email': 'user12@example.com',
                'groups': ['admin']
            }
        )

    @patch('ramses.auth.transaction')
    def test_create_admin_user_created(self, mock_trans):
        from ramses import auth
        config = Mock()
        config.registry.settings = {
            'system.user': 'user12',
            'system.password': '123456',
            'system.email': 'user12@example.com',
        }
        config.registry.auth_model.get_or_create.return_value = (
            Mock(), True)
        auth.create_admin_user(config)
        mock_trans.commit.assert_called_once_with()
        config.registry.auth_model.get_or_create.assert_called_once_with(
            username='user12',
            defaults={
                'password': '123456',
                'email': 'user12@example.com',
                'groups': ['admin']
            }
        )

    @patch('ramses.auth.create_admin_user')
    def test_includeme(self, mock_create):
        from ramses import auth
        auth.includeme(config=1)
        mock_create.assert_called_once_with(1)
