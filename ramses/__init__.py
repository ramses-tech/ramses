import logging

import pyraml.parser
from nefertari.acl import RootACL as NefertariRootACL
from nefertari.utils import dictset

from .generators import generate_server, generate_models


log = logging.getLogger(__name__)


def includeme(config):
    Settings = dictset(config.registry.settings)
    config.include('nefertari.engine')
    config.include('nefertari')
    config.include('nefertari.view')

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
    root_auth = getattr(root, 'auth', False)

    log.info('Parsing RAML')
    parsed_raml = pyraml.parser.load(Settings['ramses.raml_schema'])

    log.info('Starting models generation')
    generate_models(config, raml_resources=parsed_raml.resources)

    if root_auth:
        if getattr(config.registry, 'auth_model', None) is None:
            from nefertari.authentication.models import get_authuser_model
            config.registry.auth_model = get_authuser_model()
        from .auth import setup_auth_policies
        setup_auth_policies(config, parsed_raml)

    config.include('nefertari.elasticsearch')

    log.info('Starting server generation')
    generate_server(parsed_raml, config)

    log.info('Running nefertari.engine.setup_database')
    from nefertari.engine import setup_database
    setup_database(config)

    from nefertari.elasticsearch import ES
    ES.setup_mappings()

    if root_auth:
        config.include('ramses.auth')

    log.info('Server succesfully generated\n')
