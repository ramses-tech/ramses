import logging

import pyraml.parser
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from nefertari.acl import RootACL as NefertariRootACL
from nefertari.utils import dictset

from .generators import generate_server


log = logging.getLogger(__name__)


def includeme(config):
    Settings = dictset(config.registry.settings)
    config.include('nefertari.engine')
    config.include('nefertari')
    config.include('nefertari.view')
    config.include('nefertari.elasticsearch')

    # Set root factory
    config.root_factory = NefertariRootACL

    # Enable authentication
    root = config.get_root_resource()
    root.auth = Settings.asbool('auth', False)

    log.info('Configuring auth policies')
    authz_policy = ACLAuthorizationPolicy()
    config.set_authorization_policy(authz_policy)

    from .auth import AuthUser
    authn_policy = AuthTktAuthenticationPolicy(
        Settings['auth_tkt_secret'],
        callback=AuthUser.groupfinder,
        hashalg='sha512',
        cookie_name='ramses_auth_tkt',
        http_only=True,
    )
    config.set_authentication_policy(authn_policy)

    log.info('Parsing RAML and startign server generation')
    parsed_raml = pyraml.parser.load(
        Settings['raml_schema'])
    generate_server(parsed_raml, config)

    log.info('Running nefertari.engine.setup_database')
    from nefertari.engine import setup_database
    setup_database(config)

    config.include('ramses.auth', route_prefix='/auth')

    log.info('Server succesfully generated\n')
