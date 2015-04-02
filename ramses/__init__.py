from __future__ import print_function

import pyraml.parser
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from nefertari.acl import RootACL as NefertariRootACL

from .generators import generate_server


def includeme(config):
    config.include('nefertari.engine')
    config.include('nefertari')
    # config.include('nefertari.view')
    config.include('nefertari.elasticsearch')

    # Set root factory
    config.root_factory = NefertariRootACL

    print('Configuring auth policies')
    authz_policy = ACLAuthorizationPolicy()
    config.set_authorization_policy(authz_policy)
    authn_policy = AuthTktAuthenticationPolicy(
        config.registry.settings['auth_tkt_secret'])
    config.set_authentication_policy(authn_policy)

    print('Parsing RAML and startign server generation')
    parsed_raml = pyraml.parser.load(
        config.registry.settings['raml_schema'])
    generate_server(parsed_raml, config)

    print('\nRunning nefertari.engine.setup_database')
    from nefertari.engine import setup_database
    setup_database(config)

    print('Server succesfully generated\n')
