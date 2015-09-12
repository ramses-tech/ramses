import logging

import ramlfications
from nefertari.acl import RootACL as NefertariRootACL
from nefertari.utils import dictset


log = logging.getLogger(__name__)


def includeme(config):
    from .generators import generate_server, generate_models
    Settings = dictset(config.registry.settings)
    config.include('nefertari.engine')

    config.registry.database_acls = Settings.asbool('database_acls')
    if config.registry.database_acls:
        config.include('nefertari_guards')

    config.include('nefertari')
    config.include('nefertari.view')
    config.include('nefertari.json_httpexceptions')

    # Process nefertari settings
    if Settings.asbool('enable_get_tunneling'):
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
    raml_root = ramlfications.parse(Settings['ramses.raml_schema'])

    log.info('Starting models generation')
    generate_models(config, raml_resources=raml_root.resources)

    if root_auth:
        from .auth import setup_auth_policies, get_authuser_model
        if getattr(config.registry, 'auth_model', None) is None:
            config.registry.auth_model = get_authuser_model()
        setup_auth_policies(config, raml_root)

    config.include('nefertari.elasticsearch')

    log.info('Starting server generation')
    generate_server(raml_root, config)

    log.info('Running nefertari.engine.setup_database')
    from nefertari.engine import setup_database
    setup_database(config)

    from nefertari.elasticsearch import ES
    ES.setup_mappings()

    if root_auth:
        config.include('ramses.auth')

    log.info('Server succesfully generated\n')
