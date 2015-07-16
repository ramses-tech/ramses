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
    if Settings.asbool('enable_get_tunneling'):
        log.warning('GET tunneling enabled')
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

    log.info('Parsing RAML')
    parsed_raml = pyraml.parser.load(Settings['ramses.raml_schema'])

    log.info('Starting models generation')
    generate_models(config, raml_resources=parsed_raml.resources)

    if ramses_auth:
        from .auth import setup_auth_policies, get_authuser_model
        if getattr(config.registry, 'auth_model', None) is None:
            config.registry.auth_model = get_authuser_model()
        setup_auth_policies(config, parsed_raml)

    config.include('nefertari.elasticsearch')

    log.info('Starting server generation')
    generate_server(parsed_raml, config)

    log.info('Running nefertari.engine.setup_database')
    from nefertari.engine import setup_database
    setup_database(config)

    from nefertari.elasticsearch import ES
    ES.setup_mappings()

    if ramses_auth:
        config.include('ramses.auth')

    log.info('Server succesfully generated\n')
