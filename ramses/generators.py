from __future__ import print_function

from inflection import pluralize, singularize
from nefertari.acl import GuestACL

from .views import generate_rest_view
from .acl import generate_acl
from .objects import DemoStorage
from .utils import (
    ContentTypes, fields_dict, make_route_name, is_dynamic_uri,
    unwrap_dynamic_uri)
from .models import generate_model_cls


def setup_storage_model(config, resource, route_name):
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
            return generate_model_cls(properties, resource)
    else:
        raise Exception('Missing schema for route `{}`'.format())


def configure_resources(config, raml_resources, parent_resource=None):
    if not raml_resources:
        return

    # Use root factory for root-level resources
    if parent_resource is None:
        parent_resource = config.get_root_resource()

    for resource_uri, raml_resource in raml_resources.items():
        clean_uri = resource_uri.strip('/')
        route_name = make_route_name(resource_uri)

        # No need to setup routes/views for dynamic resource as it was already
        # setup when parent was configured.
        if is_dynamic_uri(resource_uri):
            if parent_resource is None:
                raise Exception("Top-level resources can't be dynamic and must "
                                "represent collections instead")
            return configure_resources(
                config=config,
                raml_resources=raml_resource.resources,
                parent_resource=parent_resource)

        # This should generate a DB model
        model_cls = setup_storage_model(config, raml_resource, route_name)

        # Generate ACL. Use GuestACL for now
        acl = generate_acl(context_cls=model_cls, base_cls=GuestACL)

        # Generate REST view
        view = generate_rest_view(
            model_cls=model_cls,
            methods=(raml_resource.methods or {}).keys())

        kwargs = {'factory': acl, 'view': view}

        # If one of subresources has dynamic part, the name of part is
        # the name of the field that should be used to get a particular object
        # from collection
        subresources = raml_resource.resources or {}
        dynamic_uris = [u for u in subresources if is_dynamic_uri(u)]
        if dynamic_uris:
            kwargs['id_name'] = unwrap_dynamic_uri(dynamic_uris[0])

        # Create new nefertari route
        new_resource = parent_resource.add(
            singularize(clean_uri), pluralize(clean_uri),
            **kwargs)

        # Configure child resources if present
        configure_resources(
            config=config,
            raml_resources=raml_resource.resources,
            parent_resource=new_resource)


def generate_server(parsed_raml, config):
    # Setup storage
    config.registry.storage = DemoStorage()

    # Setup resources
    configure_resources(config=config, raml_resources=parsed_raml.resources)
