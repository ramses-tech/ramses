"""
Auth module that contains all code needed for authentication/authorization
policies setup.

In particular:
    :includeme: Function that actually creates routes listed above and
        connects view to them
    :create_system_user: Function that creates system/admin user
    :_setup_ticket_policy: Setup Pyramid AuthTktAuthenticationPolicy
    :_setup_apikey_policy: Setup nefertari.ApiKeyAuthenticationPolicy
    :setup_auth_policies: Runs generation of particular auth policy
"""
import logging

import transaction
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.security import Allow, ALL_PERMISSIONS
import cryptacular.bcrypt

from nefertari.utils import dictset
from nefertari.json_httpexceptions import *
from nefertari.authentication.policies import ApiKeyAuthenticationPolicy

log = logging.getLogger(__name__)


class ACLAssignRegisterMixin(object):
    """ Mixin that sets ``User._acl`` field after user is registered. """
    def register(self, *args, **kwargs):
        response = super(ACLAssignRegisterMixin, self).register(
            *args, **kwargs)

        user = self.request._user
        mapping = self.request.registry._model_collections
        if not user._acl and self.Model.__name__ in mapping:
            from nefertari_guards import engine as guards_engine
            factory = mapping[self.Model.__name__].view._factory
            acl = factory(self.request).generate_item_acl(user)
            acl = guards_engine.ACLField.stringify_acl(acl)
            user.update({'_acl': acl})

        return response


def _setup_ticket_policy(config, params):
    """ Setup Pyramid AuthTktAuthenticationPolicy.

    Notes:
      * Initial `secret` params value is considered to be a name of config
        param that represents a cookie name.
      * `auth_model.get_groups_by_userid` is used as a `callback`.
      * Also connects basic routes to perform authentication actions.

    :param config: Pyramid Configurator instance.
    :param params: Nefertari dictset which contains security scheme
        `settings`.
    """
    from nefertari.authentication.views import (
        TicketAuthRegisterView, TicketAuthLoginView,
        TicketAuthLogoutView)

    log.info('Configuring Pyramid Ticket Authn policy')
    if 'secret' not in params:
        raise ValueError(
            'Missing required security scheme settings: secret')
    params['secret'] = config.registry.settings[params['secret']]

    auth_model = config.registry.auth_model
    params['callback'] = auth_model.get_groups_by_userid

    config.add_request_method(
        auth_model.get_authuser_by_userid, 'user', reify=True)

    policy = AuthTktAuthenticationPolicy(**params)

    RegisterViewBase = TicketAuthRegisterView
    if config.registry.database_acls:
        class RegisterViewBase(ACLAssignRegisterMixin,
                               TicketAuthRegisterView):
            pass

    class RamsesTicketAuthRegisterView(RegisterViewBase):
        Model = config.registry.auth_model

    class RamsesTicketAuthLoginView(TicketAuthLoginView):
        Model = config.registry.auth_model

    class RamsesTicketAuthLogoutView(TicketAuthLogoutView):
        Model = config.registry.auth_model

    common_kw = {
        'prefix': 'auth',
        'factory': 'nefertari.acl.AuthenticationACL',
    }

    root = config.get_root_resource()
    root.add('register', view=RamsesTicketAuthRegisterView, **common_kw)
    root.add('login', view=RamsesTicketAuthLoginView, **common_kw)
    root.add('logout', view=RamsesTicketAuthLogoutView, **common_kw)

    return policy


def _setup_apikey_policy(config, params):
    """ Setup `nefertari.ApiKeyAuthenticationPolicy`.

    Notes:
      * User may provide model name in :params['user_model']: do define
        the name of the user model.
      * `auth_model.get_groups_by_token` is used to perform username and
        token check
      * `auth_model.get_token_credentials` is used to get username and
        token from userid
      * Also connects basic routes to perform authentication actions.

    Arguments:
        :config: Pyramid Configurator instance.
        :params: Nefertari dictset which contains security scheme `settings`.
    """
    from nefertari.authentication.views import (
        TokenAuthRegisterView, TokenAuthClaimView,
        TokenAuthResetView)
    log.info('Configuring ApiKey Authn policy')

    auth_model = config.registry.auth_model
    params['check'] = auth_model.get_groups_by_token
    params['credentials_callback'] = auth_model.get_token_credentials
    params['user_model'] = auth_model
    config.add_request_method(
        auth_model.get_authuser_by_name, 'user', reify=True)

    policy = ApiKeyAuthenticationPolicy(**params)

    RegisterViewBase = TokenAuthRegisterView
    if config.registry.database_acls:
        class RegisterViewBase(ACLAssignRegisterMixin,
                               TokenAuthRegisterView):
            pass

    class RamsesTokenAuthRegisterView(RegisterViewBase):
        Model = auth_model

    class RamsesTokenAuthClaimView(TokenAuthClaimView):
        Model = auth_model

    class RamsesTokenAuthResetView(TokenAuthResetView):
        Model = auth_model

    common_kw = {
        'prefix': 'auth',
        'factory': 'nefertari.acl.AuthenticationACL',
    }

    root = config.get_root_resource()
    root.add('register', view=RamsesTokenAuthRegisterView, **common_kw)
    root.add('token', view=RamsesTokenAuthClaimView, **common_kw)
    root.add('reset_token', view=RamsesTokenAuthResetView, **common_kw)

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


def setup_auth_policies(config, raml_root):
    """ Setup authentication, authorization policies.

    Performs basic validation to check all the required values are present
    and performs authentication, authorization policies generation using
    generator functions from `AUTHENTICATION_POLICIES`.

    :param config: Pyramid Configurator instance.
    :param raml_root: Instance of ramlfications.raml.RootNode.
    """
    log.info('Configuring auth policies')
    secured_by_all = raml_root.secured_by or []
    secured_by = [item for item in secured_by_all if item]
    if not secured_by:
        log.info('API is not secured. `secured_by` attribute '
                 'value missing.')
        return
    secured_by = secured_by[0]

    schemes = {scheme.name: scheme
               for scheme in raml_root.security_schemes}
    if secured_by not in schemes:
        raise ValueError(
            'Undefined security scheme used in `secured_by`: {}'.format(
                secured_by))

    scheme = schemes[secured_by]
    if scheme.type not in AUTHENTICATION_POLICIES:
        raise ValueError('Unsupported security scheme type: {}'.format(
            scheme.type))

    # Setup Authentication policy
    policy_generator = AUTHENTICATION_POLICIES[scheme.type]
    params = dictset(scheme.settings or {})
    authn_policy = policy_generator(config, params)
    config.set_authentication_policy(authn_policy)

    # Setup Authorization policy
    authz_policy = ACLAuthorizationPolicy()
    config.set_authorization_policy(authz_policy)


def create_system_user(config):
    log.info('Creating system user')
    crypt = cryptacular.bcrypt.BCRYPTPasswordManager()
    settings = config.registry.settings
    try:
        auth_model = config.registry.auth_model
        s_user = settings['system.user']
        s_pass = str(crypt.encode(settings['system.password']))
        s_email = settings['system.email']
        defaults = dict(
            password=s_pass,
            email=s_email,
            groups=['admin'],
        )
        if config.registry.database_acls:
            defaults['_acl'] = [(Allow, 'g:admin', ALL_PERMISSIONS)]

        user, created = auth_model.get_or_create(
            username=s_user, defaults=defaults)
        if created:
            transaction.commit()
    except KeyError as e:
        log.error('Failed to create system user. Missing config: %s' % e)


def get_authuser_model():
    """ Define and return AuthUser model using nefertari base classes """
    from nefertari.authentication.models import AuthUserMixin
    from nefertari import engine

    class AuthUser(AuthUserMixin, engine.BaseDocument):
        __tablename__ = 'ramses_authuser'

    return AuthUser


def includeme(config):
    create_system_user(config)
