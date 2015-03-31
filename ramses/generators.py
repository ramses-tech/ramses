from __future__ import print_function

from .views import RESTView
from .objects import DemoStorage
from .utils import (
    ContentTypes, fields_dict, make_route_name, is_dynamic_uri)


def setup_storage_schema(config, resource, route_name):
    schemas = (ContentTypes.JSON, ContentTypes.TEXT_XML)
    methods = resource.methods or {}
    method = (methods.get('post') or
              methods.get('put'))
    if not method:
        print('No methods to setup database schema from. '
              'Route: {}'.format(route_name))
        return

    for schema_name in schemas:
        if schema_name not in method.body:
            continue
        schema = method.body[schema_name].schema
        if schema:
            properties = fields_dict(schema, schema_name)
            config.registry.storage.setup_schema(
                route_name, properties)
            break
    else:
        raise Exception('Missing schema for route `{}`'.format())


def setup_methods_handlers(config, resource, route_name):
    if not resource.methods:
        print('No methods to handle. Route: {}'.format(route_name))

    for method_name, method in resource.methods.items():
        config.add_view(
            RESTView,
            route_name=route_name,
            renderer='json',
            attr=method_name,
            request_method=method_name.upper())

        print('{}:\t{}{}'.format(
            method_name.upper(), (config.route_prefix or ''),
            route_name.replace('_', '/')))


def configure_resources(config, resources, uri_prefix=''):
    for resource_uri, resource in resources.items():
        resource_uri = uri_prefix + resource_uri
        route_name = make_route_name(resource_uri)
        config.add_route(route_name, resource_uri)

        # Do not setup model for dynamic routes for now
        # Do not generate schema for dynamic routes for now
        if not is_dynamic_uri(resource_uri):
            config.registry.storage.add_model(route_name)
            setup_storage_schema(config, resource, route_name)

        setup_methods_handlers(config, resource, route_name)

        if resource.resources:
            configure_resources(config, resource.resources, resource_uri)


def generate_server(parsed_raml, config):
    # Setup storage
    config.registry.storage = DemoStorage()

    # Setup resources
    configure_resources(config, parsed_raml.resources)
