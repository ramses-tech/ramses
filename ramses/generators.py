from __future__ import print_function

import logging

from inflection import pluralize, singularize

from .views import generate_rest_view
from .acl import generate_acl
from .utils import (
    is_dynamic_uri, resource_view_attrs, generate_model_name,
    is_restful_uri, dynamic_part_name, get_resource_schema,
    attr_subresource, singular_subresource)


log = logging.getLogger(__name__)


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
    from .models import generate_model_cls, get_existing_model
    model_cls = get_existing_model(model_name)
    if model_cls is not None:
        return model_cls

    properties = get_resource_schema(raml_resource)
    if not properties:
        raise Exception('Missing schema for model `{}`'.format(model_name))

    log.info('Generating model class `{}`'.format(model_name))
    return generate_model_cls(
        properties=properties,
        model_name=model_name,
        raml_resource=raml_resource,
    )


def generate_model_cls(raml_resource, route_name):
    """ Renerate model class for :raml_resource: with name :route_name:

    Generates model name using `generate_model_name` util function and
    then generates model itself by calling `setup_data_model`.

    Arguments:
        :raml_resource: Instance of pyraml.entities.RamlResource.
        :route_name: String name of the resource.
    """
    model_name = generate_model_name(route_name)
    try:
        model_cls = setup_data_model(raml_resource, model_name)
    except ValueError as ex:
        raise ValueError('{}: {}'.format(model_name, str(ex)))
    return model_cls


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
        assumed to be a primary_key=True field when generating DB model.
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
        log.info('Configuring resource: `{}`. Parent: `{}`'.format(
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
        # If this is an attribute or singular resource, we don't need to
        # generate model
        is_singular = singular_subresource(raml_resource, route_name)
        is_attr_res = attr_subresource(raml_resource, route_name)
        if parent_arg is not None and (is_attr_res or is_singular):
            model_cls = parent_resource.view._model_class
        else:
            model_cls = generate_model_cls(raml_resource, route_name)

        resource_kwargs = {}

        # Generate ACL. Use GuestACL for now
        log.info('Generating ACL for `{}`'.format(route_name))
        resource_kwargs['factory'] = generate_acl(
            context_cls=model_cls,
            raml_resource=raml_resource,
        )

        # Generate dynamic part name
        if not is_singular:
            resource_kwargs['id_name'] = dynamic_part_name(
                raml_resource=raml_resource,
                clean_uri=clean_uri,
                id_field=model_cls.id_field())

        # Generate REST view
        log.info('Generating view for `{}`'.format(route_name))
        resource_kwargs['view'] = generate_rest_view(
            model_cls=model_cls,
            attrs=resource_view_attrs(raml_resource, is_singular),
            attr_view=is_attr_res,
            singular=is_singular,
        )

        # In case of singular resource, model still needs to be generated,
        # but we store it on a different view attribute
        if is_singular:
            resource_kwargs['view']._singular_model = generate_model_cls(
                raml_resource, route_name)

        # Create new nefertari resource
        log.info('Creating new resource for `{}`'.format(route_name))
        resource_args = (singularize(clean_uri),)

        if not is_singular:
            resource_args += (pluralize(clean_uri),)

        new_resource = parent_resource.add(*resource_args, **resource_kwargs)

        # Set new resource to view's '_resource' and '_factory' attrs to allow
        # performing' generic operations in view
        resource_kwargs['view']._resource = new_resource
        resource_kwargs['view']._factory = resource_kwargs['factory']

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
    log.info('Server generation started')
    # Setup resources
    configure_resources(config=config, raml_resources=parsed_raml.resources)
