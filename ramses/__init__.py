import pyraml.parser
from .generators import generate_views


def includeme(config):
    parsed_raml = pyraml.parser.load(
        config.registry.settings['raml_schema'])
    generate_views(parsed_raml, config)
