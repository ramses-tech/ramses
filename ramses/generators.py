import logging

from inflection import pluralize, singularize

from .views import generate_rest_view
from .acl import generate_acl
from .utils import (
    is_dynamic_uri, resource_view_attrs, generate_model_name,
    is_restful_uri, dynamic_part_name, resource_schema,
    attr_subresource, singular_subresource)


log = logging.getLogger(__name__)


def setup_data_model(raml_resource, model_name):
    """ Setup storage/data model and return generated model class.

    Process follows these steps:
      * Resource schema is found and restructured by `resource_schema`.
      * Model class is generated from properties dict using util function
        `generate_model_cls`.

    Arguments:
        :raml_resource: Instance of pyraml.entities.RamlResource.
        :model_name: String representing model name.
    """
    from .models import generate_model_cls, get_existing_model
    model_cls = get_existing_model(model_name)
    if model_cls is not None:
        return model_cls, False

    schema = resource_schema(raml_resource)
    if not schema:
        raise Exception('Missing schema for model `{}`'.format(model_name))

    log.info('Generating model class `{}`'.format(model_name))
    return generate_model_cls(
        schema=schema,
        model_name=model_name,
        raml_resource=raml_resource,
    )


def handle_model_generation(raml_resource, route_name):
    """ Generates model name and runs `setup_data_model` to get
    or generate actual model class.

    Arguments:
        :raml_resource: Instance of pyraml.entities.RamlResource.
        :route_name: String name of the resource.
    """
    model_name = generate_model_name(route_name)
    try:
        return setup_data_model(raml_resource, model_name)
    except ValueError as ex:
        raise ValueError('{}: {}'.format(model_name, str(ex)))


def configure_resources(config, raml_resources, parsed_raml,
                        parent_resource=None):
    """ Perform complete resource configuration process

    RAML data from `raml_resources` is used. Created resources
    are attached to `parent_resource` class which is an instance of
    `nefertari.resource.Resource`.

    This function iterates through resources data from `raml_resources` and
    generates: ACL, view, route, resource,
    database model. It is called recursively for configuring child resources.

    Things to consider:
      * Top-level resources must be collection names.
      * Resource nesting must look like collection/id/collection/id/...
      * No resources are explicitly created for dynamic (ending with '}')
        RAML resources as they are implicitly processed by parent collection
        resources.
      * Collection resources can only have 1 dynamic child resource.

    Arguments:
        :config: Pyramid Configurator instance
        :raml_resources: Map of {uri_string: pyraml.entities.RamlResource}
        :parsed_raml: Whole parsed RAML object
        :parent_resource: Instance of `nefertari.resource.Resource`
    """
    from .models import get_existing_model
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
                parsed_raml=parsed_raml,
                parent_resource=parent_resource)

        # Generate DB model
        # If this is an attribute or singular resource, we don't need to
        # generate model
        is_singular = singular_subresource(raml_resource, route_name)
        is_attr_res = attr_subresource(raml_resource, route_name)
        if parent_arg is not None and (is_attr_res or is_singular):
            model_cls = parent_resource.view._model_class
        else:
            model_name = generate_model_name(route_name)
            model_cls = get_existing_model(model_name)

        resource_kwargs = {}

        # Generate ACL. Use GuestACL for now
        log.info('Generating ACL for `{}`'.format(route_name))
        resource_kwargs['factory'] = generate_acl(
            context_cls=model_cls,
            raml_resource=raml_resource,
            parsed_raml=parsed_raml,
        )

        # Generate dynamic part name
        if not is_singular:
            resource_kwargs['id_name'] = dynamic_part_name(
                raml_resource=raml_resource,
                clean_uri=clean_uri,
                pk_field=model_cls.pk_field())

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
            model_name = generate_model_name(route_name)
            resource_kwargs['view']._singular_model = get_existing_model(
                model_name)

        # Create new nefertari resource
        log.info('Creating new resource for `{}`'.format(route_name))
        resource_args = (singularize(clean_uri),)

        if not is_singular:
            resource_args += (pluralize(clean_uri),)

        new_resource = parent_resource.add(*resource_args, **resource_kwargs)

        # Configure child resources if present
        configure_resources(
            config=config,
            raml_resources=raml_resource.resources,
            parsed_raml=parsed_raml,
            parent_resource=new_resource)


def generate_server(parsed_raml, config):
    """ Run server generation process.

    Arguments:
        :config: Pyramid Configurator instance.
        :parsed_raml: Parsed pyraml structure.
    """
    log.info('Server generation started')

    # Setup resources
    configure_resources(
        config=config, raml_resources=parsed_raml.resources,
        parsed_raml=parsed_raml)


def generate_models(config, raml_resources):
    """ Generate model for each resource in :raml_resources:

    Notes:
      * The DB model name is generated using singular titled version of current
        resource's url. E.g. for resource under url '/stories', model with
        name 'Story' will be generated.

    Arguments:
        :config: Pyramid Configurator instance
        :raml_resources: Map of {uri_string: pyraml.entities.RamlResource}
    """
    if not raml_resources:
        return

    for resource_uri, raml_resource in raml_resources.items():
        # No need to generate models for dynamic resource
        if is_dynamic_uri(resource_uri):
            return generate_models(
                config, raml_resources=raml_resource.resources)

        # Generate DB model
        # If this is an attribute resource we don't need to generate model
        route_name = resource_uri.strip('/')
        if not attr_subresource(raml_resource, route_name):
            log.info('Configuring model for route `{}`'.format(route_name))
            model_cls, is_auth_model = handle_model_generation(
                raml_resource, route_name)
            if is_auth_model:
                config.registry.auth_model = model_cls

        # Generate child models if present
        generate_models(config, raml_resources=raml_resource.resources)
