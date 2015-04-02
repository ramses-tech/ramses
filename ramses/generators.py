from __future__ import print_function

from inflection import pluralize, singularize
from nefertari.acl import GuestACL

from .views import generate_rest_view
from .acl import generate_acl
from .utils import (
    ContentTypes, fields_dict, is_dynamic_uri,
    clean_dynamic_uri, resource_view_attrs, resource_model_name)


def setup_data_model(config, raml_resource, model_name):
    """ Setup storage/data model and return generated model class.

    Process follows these steps:
      * `raml_resource` post, put, patch methods body chemas are checked
        to see if any defines schema.
      * Found schema is restructured into dict of form
        {field_name: {required: boolean, type: type_name}}
      * Model class is generated from properties dict using util function
        `generate_model_cls`.

    Arguments:
        :config: Pyramid Configurator instance.
        :raml_resource: Instance of pyraml.entities.RamlResource.
        :model_name: String representing model name.
    """
    from .models import generate_model_cls
    print('Configuring storage model `{}`'.format(model_name))
    schemas = (ContentTypes.JSON, ContentTypes.TEXT_XML)
    methods = raml_resource.methods or {}

    # Get 'schema' from particular methods' bodies
    method = (methods.get('post') or
              methods.get('put') or
              methods.get('patch'))
    if not method:
        raise ValueError('No methods to setup database schema from')

    # Find what schema from 'schemas' is defined
    for schema_ct in schemas:
        if schema_ct not in method.body:
            continue
        schema = method.body[schema_ct].schema
        if schema:
            # Restructure arbitrary schema to dict or {name: {...: ...}}
            properties = fields_dict(schema, schema_ct)
            print('Generating model class `{}`'.format(model_name))
            return generate_model_cls(
                properties=properties,
                model_name=model_name,
            )
    else:
        raise Exception('Missing schema for route `{}`'.format())


def configure_resources(config, raml_resources, parent_resource=None):
    """ Perform complete resources' configuration process

    Resources RAML data from `raml_resources` is used. Created resources
    are attached to `parent_resource` class which is an instance if
    `nefertari.resource.Resource`.

    Function iterates through resources data from `raml_resources` and
    generates full set of objects required: ACL, view, route, resource,
    database model. Is called recursively for configuring child resources.

    Things to consider:
      * Top-level resources must be collection names.
      * Resources nesting must look like collection/id/collection/id/...
      * No resources are explicitly created for dynamic (ending with '}')
        RAML resources as they are implicitly processed by parent collection
        resource.
      * DB model name is generated using parent routes' uid and current
        resource name. E.g. parent uid is 'users:stories' and current resource
        is '/comments'. DB model name will be 'UsersStoriesComment'.
      * Dynamic resource uri is added to parent resource as 'id_name' attr.
        You are encouraged to name dynamic route using field 'id', as it is
        assumed to be a Primary Key field when generating DB model.
        E.g. if you have stories/{id}, 'stories' resource will be init
        with id_name='id'.
      * Collection resource may only have 1 dynamic child resource.

    Arguments:
        :config: Pyramid Configurator instance.
        :raml_resource: Map of {uri_string: pyraml.entities.RamlResource}.
        :parent_resource: Instance of `nefertari.resource.Resource`.
    """
    if not raml_resources:
        return

    # Use root factory for root-level resources
    if parent_resource is None:
        parent_resource = config.get_root_resource()

    for resource_uri, raml_resource in raml_resources.items():
        clean_uri = route_name = resource_uri.strip('/')
        print('\nConfiguring resource: `{}`. Parent: `{}`'.format(
            route_name, parent_resource.uid or 'root'))

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

        # Generate DB model
        model_name = resource_model_name(parent_resource, route_name)
        try:
            model_cls = setup_data_model(config, raml_resource, model_name)
        except ValueError as ex:
            raise ValueError('{}: {}'.format(route_name, str(ex)))

        resource_kwargs = {}

        # Generate ACL. Use GuestACL for now
        print('Generating ACL for `{}`'.format(route_name))
        resource_kwargs['factory'] = generate_acl(
            context_cls=model_cls,
            base_cls=GuestACL,
        )

        # If one of subresources has dynamic part, the name of part is
        # the name of the field that should be used to get a particular object
        # from collection
        subresources = raml_resource.resources or {}
        dynamic_uris = [uri for uri in subresources.keys()
                        if is_dynamic_uri(uri)]

        if dynamic_uris:
            resource_kwargs['id_name'] = clean_dynamic_uri(dynamic_uris[0])

        # Generate REST view
        print('Generating view for `{}`'.format(route_name))
        resource_kwargs['view'] = generate_rest_view(
            model_cls=model_cls,
            attrs=resource_view_attrs(raml_resource),
        )

        # Create new nefertari route
        print('Creating new resource for `{}`'.format(route_name))
        new_resource = parent_resource.add(
            singularize(clean_uri), pluralize(clean_uri),
            **resource_kwargs)

        # Set new resource to view's '_resource' attr to allow performing
        # generic operations in view
        resource_kwargs['view']._resource = new_resource

        # Configure child resources if present
        configure_resources(
            config=config,
            raml_resources=raml_resource.resources,
            parent_resource=new_resource)


def generate_server(parsed_raml, config):
    """ Run server generation process.

    Arguments:
        :config: Pyramid Configurator instance.
        :parsed_raml: Parsed pyraml structure.
    """
    print('Server generation started')
    # Setup resources
    configure_resources(config=config, raml_resources=parsed_raml.resources)
