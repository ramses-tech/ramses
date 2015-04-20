"""
Auth module that contains all code needed for authentication/authorization
systems to run.

In particular:
    :AuthUser: Class that is meant to be User class in Auth system.
    :TicketAuthenticationView: View for auth operations to use with Pyramid
        ticket-based auth. Is registered with '/auth' prefix and makes
        available routes:
            /auth/login (POST): Login the user with 'login' and 'password'
            /auth/logout: Logout user
            /auth/register (POST): Register new user
    :TokenAuthenticationView: View for auth operations to use with
        nefertari.ApiKeyAuthenticationPolicy token-based auth. Is registered
        with '/auth' prefix and makes available routes:
            /auth/register (POST): Register new user
            /auth/token (POST): Claim current token by submitting 'login' and
              'password'
            /auth/token_reset (POST): Reset current token by submitting 'login'
              and 'password'
    :includeme: Function that actually creates routes listed above and
        connects view to them.
    :create_admin_user: Function that creates system/admin user.

"""
import logging

import cryptacular.bcrypt
from pyramid.security import authenticated_userid, remember, forget
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy

from nefertari import engine as eng
from nefertari.utils import dictset
from nefertari.json_httpexceptions import *
from nefertari.view import BaseView
from nefertari.authentication import ApiKeyAuthenticationPolicy

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
    groups = eng.ListField(
        item_type=eng.StringField,
        choices=['admin', 'user'], default=['user'])

    uid = property(lambda self: str(self.id))

    def verify_password(self, password):
        return crypt.check(self.password, password)

    @classmethod
    def get_api_credentials(cls, userid, request):
        """ Get username and api token for user with id of :userid: """
        try:
            user = cls.get_resource(id=userid)
        except JHTTPNotFound:
            forget(request)
        if user:
            return user.username, user.api_key.token
        return None, None

    @classmethod
    def authenticate_token(cls, username, token, request):
        """ Get user's groups if user with :username: exists and his api key
        token equals to :token:
        """
        try:
            user = cls.get_resource(username=username)
        except JHTTPNotFound:
            forget(request)
        if user and user.api_key.token == token:
            return ['g:%s' % g for g in user.groups]

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
    def groupfinder(cls, userid, request):
        try:
            user = cls.get_resource(id=userid)
        except JHTTPNotFound:
            forget(request)
        else:
            if user:
                return ['g:%s' % g for g in user.groups]

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
    def get_auth_user_by_id(cls, request):
        _id = authenticated_userid(request)
        if _id:
            return cls.get_resource(id=_id)

    @classmethod
    def get_auth_user_by_name(cls, request):
        username = authenticated_userid(request)
        if username:
            return cls.get_resource(username=username)


class TicketAuthenticationView(BaseView):
    """ View that defines basic auth operations that may be performed
    when using Pyramid Ticket authentication.
    """
    _model_class = AuthUser

    def register(self):
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


class TokenAuthenticationView(BaseView):
    """ View that defines basic operations that may be performed when using
    nefertari.ApiKeyAuthenticationPolicy.
    """
    _model_class = AuthUser

    def register(self):
        user, created = self._model_class.create_account(self._params)

        if not created:
            raise JHTTPConflict('Looks like you already have an account.')

        headers = remember(self.request, user.uid)
        return JHTTPOk('Registered', headers=headers)

    def claim_token(self, **params):
        self._params.update(params)
        success, self.user = self._model_class.authenticate(self._params)

        if success:
            headers = remember(self.request, self.user.uid)
            return JHTTPOk('Token claimed', headers=headers)
        if self.user:
            raise JHTTPUnauthorized('Wrong login or password')
        else:
            raise JHTTPNotFound('User not found')

    def token_reset(self, **params):
        response = self.claim_token(**params)
        if not self.user:
            return response

        self.user.api_key.reset_token()
        headers = remember(self.request, self.user.uid)
        return JHTTPOk('Registered', headers=headers)


def _setup_ticket_policy(config, params):
    """ Setup Pyramid AuthTktAuthenticationPolicy.

    Notes:
      * Initial `secret` params value is considered to be a name of config
        param that represents a cookie name.
      * `AuthUser.groupfinder` is used as a `callback`.
      * Special processing is applied to boolean params to convert string
        values like 'True', 'true' to booleans. This is done because pyraml
        parser currently does not support setting value being a boolean.
      * Also connects basic routes to perform authn actions.

    Arguments:
        :config: Pyramid Configurator instance.
        :params: Nefertari dictset which contains security scheme `settings`.
    """
    log.info('Configuring Pyramid Ticket Authn policy')
    if 'secret' not in params:
        raise ValueError(
            'Missing required security scheme settings: secret')
    bool_keys = ('secure', 'include_ip', 'http_only', 'wild_domain', 'debug',
                 'parent_domain')
    for key in bool_keys:
        params[key] = params.asbool(key)

    params['secret'] = config.registry.settings[params['secret']]
    params['callback'] = AuthUser.groupfinder

    policy = AuthTktAuthenticationPolicy(**params)

    config.add_request_method(AuthUser.get_auth_user_by_id, 'user', reify=True)

    config.add_route('login', '/auth/login')
    config.add_view(
        view=TicketAuthenticationView,
        route_name='login', attr='login', request_method='POST')

    config.add_route('logout', '/auth/logout')
    config.add_view(
        view=TicketAuthenticationView,
        route_name='logout', attr='logout')

    config.add_route('register', '/auth/register')
    config.add_view(
        view=TicketAuthenticationView,
        route_name='register', attr='register', request_method='POST')

    return policy


def _setup_apikey_policy(config, params):
    """ Setup `nefertari.ApiKeyAuthenticationPolicy`.

    Notes:
      * User may provide model name in :params['user_model']: do define
        the name of the user model.
      * `AuthUser.authenticate_token` is used to perform username & token check
      * `AuthUser.get_api_credentials` is used to get username and token from
        userid
      * Also connects basic routes to perform authn actions.

    Arguments:
        :config: Pyramid Configurator instance.
        :params: Nefertari dictset which contains security scheme `settings`.
    """
    log.info('Configuring ApiKey Authn policy')
    params['check'] = AuthUser.authenticate_token
    params['credentials_callback'] = AuthUser.get_api_credentials
    params['user_model'] = params.get('user_model') or 'AuthUser'
    policy = ApiKeyAuthenticationPolicy(**params)

    config.add_request_method(AuthUser.get_auth_user_by_name,
                              'user', reify=True)

    config.add_route('token', '/auth/token')
    config.add_view(
        view=TokenAuthenticationView,
        route_name='token', attr='claim_token', request_method='POST')

    config.add_route('token_reset', '/auth/token_reset')
    config.add_view(
        view=TokenAuthenticationView,
        route_name='token_reset', attr='token_reset', request_method='POST')

    config.add_route('register', '/auth/register')
    config.add_view(
        view=TokenAuthenticationView,
        route_name='register', attr='register', request_method='POST')

    return policy


""" Map of `security_scheme_type`: `generator_function`, where:

  * `security_scheme_type`: String that represents RAML security scheme type
    name that should be used to apply a particular authentication system.
  * `generator_function`: Function that receives instance of Pyramid
    Configurator instance and dictset of security scheme settings and returns
    generated Pyramid authentication policy instance.

"""
AUTHENTICATION_POLICIES = {
    'x-ApiKey': _setup_apikey_policy,
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
    params = dictset(scheme.settings or {})
    authn_policy = policy_generator(config, params)
    config.set_authentication_policy(authn_policy)

    # Setup Authorization policy
    authz_policy = ACLAuthorizationPolicy()
    config.set_authorization_policy(authz_policy)


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
                groups=['admin']
            ))
        if created:
            import transaction
            transaction.commit()
    except KeyError as e:
        log.error('Failed to create system user. Missing config: %s' % e)


def includeme(config):
    log.info('Creating admin user')

    create_admin_user(config)
