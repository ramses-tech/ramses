import pyraml.parser
from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from nefertari.acl import RootACL as NefertariRootACL

from .generators import generate_server


def includeme(config):
    config.include('nefertari.engine')
    config.include('nefertari')

    # Set root factory
    config.root_factory = NefertariRootACL

    # Setup auth policies
    authz_policy = ACLAuthorizationPolicy()
    config.set_authorization_policy(authz_policy)
    authn_policy = AuthTktAuthenticationPolicy(
        config.registry.settings['auth_tkt_secret'])
    config.set_authentication_policy(authn_policy)

    # Parse RAML and generate server
    parsed_raml = pyraml.parser.load(
        config.registry.settings['raml_schema'])
    generate_server(parsed_raml, config)

    from nefertari.engine import setup_database
    setup_database(config)
