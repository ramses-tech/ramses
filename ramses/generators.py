from __future__ import print_function

from inflection import pluralize, singularize

from .views import generate_rest_view
from .acl import generate_acl
from .utils import (
    is_dynamic_uri, resource_view_attrs, generate_model_name,
    is_restful_uri, dynamic_part_name, get_resource_schema,
    attr_subresource)


def setup_data_model(raml_resource, model_name):
    """ Setup storage/data model and return generated model class.

    Process follows these steps:
      * Resource schema is found and restructured by `get_resource_schema`.
      * Model class is generated from properties dict using util function
        `generate_model_cls`.

    Arguments:
        :raml_resource: Instance of pyraml.entities.RamlResource.
        :model_name: String representing model name.
    """
    from .models import generate_model_cls
    properties = get_resource_schema(raml_resource)
    if not properties:
        raise Exception('Missing schema for route `{}`'.format())

    print('Generating model class `{}`'.format(model_name))
    return generate_model_cls(
        properties=properties,
        model_name=model_name,
        raml_resource=raml_resource,
    )


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
    parent_arg = parent_resource
    if parent_resource is None:
        parent_resource = config.get_root_resource()

    for resource_uri, raml_resource in raml_resources.items():
        if not is_restful_uri(resource_uri):
            raise ValueError('Resource URI `{}` is not RESTful'.format(
                resource_uri))

        clean_uri = route_name = resource_uri.strip('/')
        print('\nConfiguring resource: `{}`. Parent: `{}`'.format(
            route_name, parent_resource.uid or 'root'))

        # No need to setup routes/views for dynamic resource as it was already
        # setup when parent was configured.
        if is_dynamic_uri(resource_uri):
            if parent_arg is None:
                raise Exception("Top-level resources can't be dynamic and must "
                                "represent collections instead")
            return configure_resources(
                config=config,
                raml_resources=raml_resource.resources,
                parent_resource=parent_resource)

        # Generate DB model
        is_attr_res = False
        # If this is an attribute resource, we don't need to generate model
        if parent_arg is not None and attr_subresource(raml_resource, route_name):
            is_attr_res = True
            model_cls = parent_resource.view._model_class
        else:
            model_name = generate_model_name(route_name)
            try:
                model_cls = setup_data_model(raml_resource, model_name)
            except ValueError as ex:
                raise ValueError('{}: {}'.format(route_name, str(ex)))

        resource_kwargs = {}

        # Generate ACL. Use GuestACL for now
        print('Generating ACL for `{}`'.format(route_name))
        resource_kwargs['factory'] = generate_acl(
            context_cls=model_cls,
            raml_resource=raml_resource,
        )

        # Generate dynamic part name
        resource_kwargs['id_name'] = dynamic_part_name(raml_resource, clean_uri)

        # Generate REST view
        print('Generating view for `{}`'.format(route_name))
        resource_kwargs['view'] = generate_rest_view(
            model_cls=model_cls,
            attrs=resource_view_attrs(raml_resource),
            attr_view=is_attr_res,
        )

        # Create new nefertari resource
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
