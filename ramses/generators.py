from .views import RESTView
from .objects import DemoStorage


def _make_route_name(name):
    route_name = name.strip('/')
    route_name = route_name.replace('/', '_').replace('{', '')
    route_name = route_name.replace('}', '')
    return route_name


def _setup_schema(config, method_spec, route_name):
    if 'application/json' not in method_spec.body:
        raise Exception(
            'Missing JSON POST schema for route `{}`'.format(route_name))
    schema = method_spec.body['application/json'].schema
    config.registry.storage.setup_schema(
        route_name, schema['properties'])


def setup_resource(config, resource_uri, resource, uri_prefix=''):
    resource_uri = uri_prefix + resource_uri
    route_name = _make_route_name(resource_uri)
    config.add_route(route_name, resource_uri)

    if not uri_prefix:
        config.registry.storage.add_model(route_name)

    if resource.methods:
        for method, method_spec in resource.methods.items():

            if method == 'post' and method_spec.body:
                _setup_schema(config, method_spec, route_name)

            config.add_view(
                RESTView,
                route_name=route_name,
                renderer='json',
                attr=method,
                request_method=method.upper())
            print '{}:\t{}{}'.format(
                method.upper(), (config.route_prefix or ''),
                resource_uri)

    if resource.resources:
        for subresource_uri, subresource in resource.resources.items():
            setup_resource(config, subresource_uri, subresource, resource_uri)


def generate_views(parsed_raml, config):
    resources = parsed_raml.resources
    config.registry.storage = DemoStorage()
    for resource_uri, resource in resources.items():
        setup_resource(config, resource_uri, resource)
