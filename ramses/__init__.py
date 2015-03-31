import pyraml.parser
from .generators import generate_server


def includeme(config):
    parsed_raml = pyraml.parser.load(
        config.registry.settings['raml_schema'])
    generate_server(parsed_raml, config)
