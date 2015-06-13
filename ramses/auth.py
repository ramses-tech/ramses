"""
Auth module that contains all code needed for authentication/authorization
policies setup.

In particular:
    :includeme: Function that actually creates routes listed above and
        connects view to them
    :create_admin_user: Function that creates system/admin user
    :_setup_ticket_policy: Setup Pyramid AuthTktAuthenticationPolicy
    :_setup_apikey_policy: Setup nefertari.ApiKeyAuthenticationPolicy
    :setup_auth_policies: Runs generation of particular auth policy
"""
import logging

import transaction
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy

from nefertari.utils import dictset
from nefertari.json_httpexceptions import *
from nefertari.authentication.policies import ApiKeyAuthenticationPolicy
from nefertari.authentication.views import (
    TicketAuthenticationView, TokenAuthenticationView)

log = logging.getLogger(__name__)


def _setup_ticket_policy(config, params):
    """ Setup Pyramid AuthTktAuthenticationPolicy.

    Notes:
      * Initial `secret` params value is considered to be a name of config
        param that represents a cookie name.
      * `auth_model.get_groups_by_userid` is used as a `callback`.
      * Special processing is applied to boolean params to convert string
        values like 'True', 'true' to booleans. This is done because pyraml
        parser currently does not support setting value being a boolean.
      * Also connects basic routes to perform authentication actions.

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
        if key in params:
            params[key] = params.asbool(key)

    params['secret'] = config.registry.settings[params['secret']]

    auth_model = config.registry.auth_model
    params['callback'] = auth_model.get_groups_by_userid

    config.add_request_method(
        auth_model.get_authuser_by_userid, 'user', reify=True)

    policy = AuthTktAuthenticationPolicy(**params)

    class RamsesTicketAuthenticationView(TicketAuthenticationView):
        _model_class = config.registry.auth_model

    config.add_route('login', '/auth/login')
    config.add_view(
        view=RamsesTicketAuthenticationView,
        route_name='login', attr='login', request_method='POST')

    config.add_route('logout', '/auth/logout')
    config.add_view(
        view=RamsesTicketAuthenticationView,
        route_name='logout', attr='logout')

    config.add_route('register', '/auth/register')
    config.add_view(
        view=RamsesTicketAuthenticationView,
        route_name='register', attr='register', request_method='POST')

    return policy


def _setup_apikey_policy(config, params):
    """ Setup `nefertari.ApiKeyAuthenticationPolicy`.

    Notes:
      * User may provide model name in :params['user_model']: do define
        the name of the user model.
      * `auth_model.get_groups_by_token` is used to perform username & token
        check
      * `auth_model.get_token_credentials` is used to get username and token
        from userid
      * Also connects basic routes to perform authentication actions.

    Arguments:
        :config: Pyramid Configurator instance.
        :params: Nefertari dictset which contains security scheme `settings`.
    """
    log.info('Configuring ApiKey Authn policy')

    auth_model = config.registry.auth_model
    params['check'] = auth_model.get_groups_by_token
    params['credentials_callback'] = auth_model.get_token_credentials
    params['user_model'] = auth_model
    config.add_request_method(
        auth_model.get_authuser_by_name, 'user', reify=True)

    policy = ApiKeyAuthenticationPolicy(**params)

    class RamsesTokenAuthenticationView(TokenAuthenticationView):
        _model_class = auth_model

    config.add_route('token', '/auth/token')
    config.add_view(
        view=RamsesTokenAuthenticationView,
        route_name='token', attr='claim_token', request_method='POST')

    config.add_route('reset_token', '/auth/reset_token')
    config.add_view(
        view=RamsesTokenAuthenticationView,
        route_name='reset_token', attr='reset_token', request_method='POST')

    config.add_route('register', '/auth/register')
    config.add_view(
        view=RamsesTokenAuthenticationView,
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
    secured_by_all = raml_data.securedBy or []
    secured_by = [item for item in secured_by_all if item]
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
        auth_model = config.registry.auth_model
        s_user = settings['system.user']
        s_pass = settings['system.password']
        s_email = settings['system.email']
        user, created = auth_model.get_or_create(
            username=s_user,
            defaults=dict(
                password=s_pass,
                email=s_email,
                groups=['admin']
            ))
        if created:
            transaction.commit()
    except KeyError as e:
        log.error('Failed to create system user. Missing config: %s' % e)


def includeme(config):
    log.info('Creating admin user')
    create_admin_user(config)
