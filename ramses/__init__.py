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

    # Process nefertari settings
    if Settings.asbool('debug'):
        log.warning('*** DEBUG DEBUG DEBUG mode ***')
        config.add_tween('nefertari.tweens.get_tunneling')

    if Settings.asbool('cors.enable'):
        config.add_tween('nefertari.tweens.cors')

    if Settings.asbool('ssl_middleware.enable'):
        config.add_tween('nefertari.tweens.ssl')

    if Settings.asbool('request_timing.enable'):
        config.add_tween('nefertari.tweens.request_timing')

    # Set root factory
    config.root_factory = NefertariRootACL

    # Process auth settings
    root = config.get_root_resource()
    ramses_auth = Settings.asbool('ramses.auth', False)
    root.auth = ramses_auth

    if ramses_auth:
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
        Settings['ramses.raml_schema'])
    generate_server(parsed_raml, config)

    log.info('Running nefertari.engine.setup_database')
    from nefertari.engine import setup_database
    setup_database(config)

    if ramses_auth:
        config.include('ramses.auth', route_prefix='/auth')

    log.info('Server succesfully generated\n')
