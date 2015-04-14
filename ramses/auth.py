"""
Auth module that contains all code needed for authentication/authorization
systems to run.

In particular:
    :AuthUser: Class that is meant to be User class in Auth system.
    :AuthorizationView: View for basic auth operations: login, logout, register.
        Is registered with '/auth' prefix and makes available routes:
        '/auth/login', '/auth/logout', '/auth/register'.
    :includeme: Function that actually creates routes listed above and
        connects view to them.
    :create_admin_user: Function that creates system/admin user.

"""
import logging

import cryptacular.bcrypt
from pyramid.security import authenticated_userid, remember, forget
from pyramid.authentication import (
    AuthTktAuthenticationPolicy, BasicAuthAuthenticationPolicy)
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.httpexceptions import HTTPUnauthorized
from pyramid.view import forbidden_view_config

from nefertari import engine as eng
from nefertari.utils import dictset
from nefertari.json_httpexceptions import *
from nefertari.view import BaseView

log = logging.getLogger(__name__)
crypt = cryptacular.bcrypt.BCRYPTPasswordManager()


def lower_strip(value):
    return (value or '').lower().strip()


def crypt_password(password):
    if password:
        password = unicode(crypt.encode(password))
    return password


class AuthUser(eng.BaseDocument):
    __tablename__ = 'authuser'

    id = eng.IdField(primary_key=True)
    username = eng.StringField(
        min_length=1, max_length=50, unique=True,
        required=True, processors=[lower_strip])
    email = eng.StringField(
        unique=True, required=True, processors=[lower_strip])
    password = eng.StringField(
        min_length=3, required=True, processors=[crypt_password])
    group = eng.ChoiceField(
        choices=['admin', 'user'], default='user',
        types_name='auth_user_group_types')

    uid = property(lambda self: str(self.id))

    def verify_password(self, password):
        return crypt.check(self.password, password)

    @classmethod
    def authenticate(cls, params):
        login = params['login'].lower().strip()
        key = 'email' if '@' in login else 'username'

        try:
            user = cls.get_resource(**{key: login})
        except JHTTPNotFound:
            success = False
            user = None

        if user:
            password = params.get('password', None)
            success = (password and user.verify_password(password))
        return success, user

    @classmethod
    def auth_groupfinder(cls, username, password, request):
        """ Authenticate user with :username: and :password: and return
        user's groups if passed credentials are valid.

        In case username/password are not valid, Pyramid `forget` is
        performed.
        """
        success, user = cls.authenticate(params={
            'login': username,
            'password': password,
        })
        if success:
            return ['g:%s' % user.group]
        else:
            forget(request)

    @classmethod
    def groupfinder(cls, userid, request):
        try:
            user = cls.get_resource(id=userid)
        except JHTTPNotFound:
            forget(request)
        else:
            if user:
                return ['g:%s' % user.group]

    @classmethod
    def create_account(cls, params):
        user_params = dictset(params).subset(
            ['username', 'email', 'password'])
        try:
            return cls.get_or_create(
                email=user_params['email'],
                defaults=user_params)
        except JHTTPBadRequest:
            raise JHTTPBadRequest('Failed to create account.')

    @classmethod
    def get_auth_user(cls, request):
        _id = authenticated_userid(request)
        if _id:
            return cls.get_resource(id=_id)


class AuthorizationView(BaseView):
    _model_class = AuthUser

    def create(self):
        user, created = self._model_class.create_account(self._params)

        if not created:
            raise JHTTPConflict('Looks like you already have an account.')

        return JHTTPOk('Registered')

    def login(self, **params):
        self._params.update(params)
        next = self._params.get('next', '')
        login_url = self.request.route_url('login')
        if next.startswith(login_url):
            next = ''  # never use the login form itself as next

        unauthorized_url = self._params.get('unauthorized', None)
        success, user = self._model_class.authenticate(self._params)

        if success:
            headers = remember(self.request, user.uid)
            if next:
                return JHTTPOk('Logged in', headers=headers)
            else:
                return JHTTPOk('Logged in', headers=headers)
        if user:
            if unauthorized_url:
                return JHTTPUnauthorized(location=unauthorized_url+'?error=1')

            raise JHTTPUnauthorized('Failed to Login.')
        else:
            raise JHTTPNotFound('User not found')

    def logout(self):
        headers = forget(self.request)
        return JHTTPOk('Logged out', headers=headers)


def includeme(config):
    log.info('Connecting auth routes and views')
    config.add_request_method(AuthUser.get_auth_user, 'user', reify=True)
    config.add_route('login', '/login')
    config.add_view(
        view=AuthorizationView,
        route_name='login', attr='login', request_method='POST')

    config.add_route('logout', '/logout')
    config.add_view(
        view=AuthorizationView,
        route_name='logout', attr='logout')

    config.add_route('register', '/register')
    config.add_view(
        view=AuthorizationView,
        route_name='register', attr='create', request_method='POST')

    create_admin_user(config)


def create_admin_user(config):
    log.info('Creating system user')
    settings = config.registry.settings
    try:
        s_user = settings['system.user']
        s_pass = settings['system.password']
        s_email = settings['system.email']
        user, created = AuthUser.get_or_create(
            username=s_user,
            defaults=dict(
                password=s_pass,
                email=s_email,
                group='admin'
            ))
        if created:
            import transaction
            transaction.commit()
    except KeyError as e:
        log.error('Failed to create system user. Missing config: %s' % e)


def _setup_ticket_policy(config, params):
    """ Setup Pyramid AuthTktAuthenticationPolicy.

    Notes:
      * Initial `secret` params value is considered to be a name of config
        param that represents a cookie name.
      * `AuthUser.groupfinder` is used as a `callback`.
      * Special processing is applied to boolean params to convert string
        values like 'True', 'true' to booleans. This is done because pyraml
        parser currently does not support setting value being a boolean.

    Arguments:
        :config: Pyramid Configurator instance.
        :params: Nefertari dictset which contains security scheme `settings`.
    """
    if 'secret' not in params:
        raise ValueError(
            'Missing required security scheme settings: secret')
    bool_keys = ('secure', 'include_ip', 'http_only', 'wild_domain', 'debug',
                 'parent_domain')
    for key in bool_keys:
        params[key] = params.asbool(key)

    params['secret'] = config.registry.settings[params['secret']]
    params['callback'] = AuthUser.groupfinder
    return AuthTktAuthenticationPolicy(**params)


def _setup_basic_policy(config, params):
    """ Setup BasicAuthAuthenticationPolicy.

    Also registers "Forbidden" view. From Pyramid docs:
      Regular browsers will not send username/password credentials unless
      they first receive a challenge from the server. The following recipe
      will register a view that will send a Basic Auth challenge to the user
      whenever there is an attempt to call a view which results in a Forbidden
      response.

    Notes:
      * AuthUser.auth_groupfinder is used as `check` param value.
      * Special processing is applied to boolean params to convert string
        values like 'True', 'true' to booleans. This is done because pyraml
        parser currently does not support setting value being a boolean.

    Arguments:
        :config: Pyramid Configurator instance.
        :params: Nefertari dictset which contains security scheme `settings`.
    """
    bool_keys = ('debug',)
    for key in bool_keys:
        params[key] = params.asbool(key)
    params['check'] = AuthUser.auth_groupfinder
    policy = BasicAuthAuthenticationPolicy(**params)

    @forbidden_view_config()
    def basic_challenge(request):
        response = HTTPUnauthorized()
        response.headers.update(forget(request))
        return response

    return policy


""" Map of `security_scheme_type`: `generator_function`, where:

  * `security_scheme_type`: String that represents RAML security scheme type
    name that should be used to apply a particular authentication system.
  * `generator_function`: Function that receives instance of Pyramid
    Configurator instance and dictset of security scheme settings and returns
    generated Pyramid authentication policy instance.

"""
AUTHENTICATION_POLICIES = {
    'Basic':    _setup_basic_policy,
    'x-Ticket': _setup_ticket_policy,
}


def setup_auth_policies(config, raml_data):
    """ Setup authentication, authorization policies.

    Performs basic validation to check all the required values are present
    and performs authentication, authorization policies generation using
    generator functions from `AUTHENTICATION_POLICIES`.

    Arguments:
        :config: Pyramid Configurator instance.
        :raml_data: Instance of pyraml.parser.entities.RamlRoot.
    """
    log.info('Configuring auth policies')
    secured_by = filter(bool, (raml_data.securedBy or []))
    if not secured_by:
        log.info('API is not secured. `securedBy` attribute value missing.')
        return
    secured_by = secured_by[0]

    if secured_by not in raml_data.securitySchemes:
        raise ValueError(
            'Not defined security scheme used in `securedBy`: {}'.format(
                secured_by))

    scheme = raml_data.securitySchemes[secured_by]
    if scheme.type not in AUTHENTICATION_POLICIES:
        raise ValueError('Not supported security scheme type: {}'.format(
            scheme.type))

    # Setup Authentication policy
    policy_generator = AUTHENTICATION_POLICIES[scheme.type]
    params = dictset(scheme.settings)
    authn_policy = policy_generator(config, params)
    config.set_authentication_policy(authn_policy)

    # Setup Authorization policy
    authz_policy = ACLAuthorizationPolicy()
    config.set_authorization_policy(authz_policy)
