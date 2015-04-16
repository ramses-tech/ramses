import logging

import inflection


log = logging.getLogger(__name__)


class ContentTypes(object):
    """ ContentType values.

    """
    JSON = 'application/json'
    TEXT_XML = 'text/xml'
    MULTIPART_FORMDATA = 'multipart/form-data'
    FORM_URLENCODED = 'application/x-www-form-urlencoded'


def fields_dict(raml_schema, schema_ct):
    """ Restructure `raml_schema` to a dictionary that looks like
    {field_name: {required: boolean, type: type_name}, ...}

    Operations performer depend on a Content Type of `schema` which
    is passed as `schema_ct` argument.

    Arguments:
        :raml_schema: pyraml.entities.RamlBody.schema.
        :schema_ct: ContentType of the schema as a string from RAML file.
    """
    if schema_ct == ContentTypes.JSON:
        if not isinstance(raml_schema, dict):
            raise TypeError(
                'Schema is not a valid JSON. Please check your '
                'schema syntax.\n{}...'.format(str(raml_schema)[:60]))
        return raml_schema['properties']
    if schema_ct == ContentTypes.TEXT_XML:
        # Process XML schema
        pass


def is_restful_uri(uri):
    """ Check whether `uri` is a RESTful uri.

    Uri is assumed to be restful if it only contains a single token.
    E.g. 'stories', 'users' but NOT 'stories/comments', 'users/{id}'

    Arguments:
        :uri: URI as a string
    """
    uri = uri.strip('/')
    return '/' not in uri


def is_dynamic_uri(uri):
    """ Determine whether `uri` is a dynamic uri or not.

    Assumes dynamic uri is a uri that ends with '}' which is a Pyramid
    way to define dynamic parts in uri.

    Arguments:
        :uri: URI as a string.
    """
    return uri.endswith('}')


def clean_dynamic_uri(uri):
    """ Strips /, {, } from dynamic `uri`.

    Arguments:
        :uri: URI as a string.
    """
    return uri.replace('/', '').replace('{', '').replace('}', '')


def generate_model_name(name):
    """ Generate model name.

    Arguments:
        :name: String representing field or route name.
    """
    model_name = inflection.camelize(name.strip('/'))
    return inflection.singularize(model_name)


def find_dynamic_resource(raml_resource):
    """ Find dymanic resource in :raml_resource:'s resources.

    Arguments:
        :raml_resource: Instance of pyraml.entities.RamlResource.
    """
    subresources = raml_resource.resources or {}
    dynamic_resources = [res for uri, res in subresources.items()
                         if is_dynamic_uri(uri)]
    return dynamic_resources[0] if dynamic_resources else None


def dynamic_part_name(raml_resource, clean_uri, id_field):
    """ Generate dynamic part for resource :raml_resource:.

    Dynamic part is generated using 2 parts: :clean_uri: of the resource and
    dynamic part of dymanic subresource. If :raml_resource: has no dynamic
    subresources, 'id' is used as the 2nd part.
    E.g. if your dynamic part on route 'stories' is named 'superId' then dynamic
    part will be 'storied_superId'.

    Arguments:
        :raml_resource: Instance of pyraml.entities.RamlResource for which
            dynamic part name is being generated.
        :clean_uri: Cleaned URI of :raml_resource:
    """
    subresources = raml_resource.resources or {}
    dynamic_uris = [uri for uri in subresources.keys() if is_dynamic_uri(uri)]
    if dynamic_uris:
        dynamic_part = clean_dynamic_uri(dynamic_uris[0])
    else:
        dynamic_part = id_field
    return '_'.join([clean_uri, dynamic_part])


def resource_view_attrs(raml_resource, singular=False):
    """ Generate view methods names needed for `raml_resource` view.

    Collects HTTP method names from `raml_resource.methods` and
    dynamic child `methods` if child exists. Collected methods are
    then translated  to `nefertari.view.BaseView` methods' names
    each of which if used to process a particular HTTP method request.

    Maps of {HTTP_method: view_method} `collection_methods` and
    `item_methods` are used to convert collection and item methods
    respectively.

    Arguments:
        :raml_resource: Instance of pyraml.entities.RamlResource.
    """
    from .views import collection_methods, item_methods

    # Singular resource doesn't have collection methods though
    # it looks like a collection
    if singular:
        collection_methods = item_methods

    http_methods = (raml_resource.methods or {}).keys()
    attrs = [collection_methods.get(m.lower()) for m in http_methods]

    # Check if resource has dynamic subresource like collection/{id}
    subresources = raml_resource.resources or {}
    dynamic_res = [res for uri, res in subresources.items()
                   if is_dynamic_uri(uri)]

    # If dynamic subresource exists, add its methods to attrs, as both
    # resources are handled by a single view
    if dynamic_res and dynamic_res[0].methods:
        http_submethods = (dynamic_res[0].methods or {}).keys()
        attrs += [item_methods.get(m.lower()) for m in http_submethods]

    return set(filter(bool, attrs))


def get_resource_schema(raml_resource):
    """ Get schema of RAML resource :raml_resource:.

    Process follows these steps:
      * :raml_resource: post, put, patch methods body chemas are checked
        to see if any defines schema.
      * Found schema is restructured into dict of form
        {field_name: {required: boolean, type: type_name}} and returned.

    Arguments:
        :raml_resource: Instance of pyraml.entities.RamlResource.
    """
    log.info('Searching for model schema')
    schemas = (ContentTypes.JSON, ContentTypes.TEXT_XML)
    methods = raml_resource.methods or {}

    # Get 'schema' from particular methods' bodies
    method = (methods.get('post') or
              methods.get('put') or
              methods.get('patch'))
    if not method:
        raise ValueError('No methods to setup database schema from')

    # Find what schema from 'schemas' is defined
    body = method.body or {}
    for schema_ct in schemas:
        if schema_ct not in body:
            continue
        schema = body[schema_ct].schema
        if schema:
            return fields_dict(schema, schema_ct)
    log.debug('No model schema found.')


def is_dynamic_resource(raml_resource):
    """ Determine if :raml_resource: is a dynamic resource.

    Arguments:
        :raml_resource:Instance of pyraml.entities.RamlResource.
    """
    if not (raml_resource and raml_resource.parentResource):
        return False
    dyn = find_dynamic_resource(raml_resource.parentResource)
    return dyn is raml_resource


def get_static_parent(raml_resource):
    """ Get static parent resource of :raml_resource:.

    Arguments:
        :raml_resource:Instance of pyraml.entities.RamlResource.
    """
    parent = raml_resource.parentResource
    while is_dynamic_resource(parent):
        parent = parent.parentResource
    return parent


def attr_subresource(raml_resource, route_name):
    """ Determine if :raml_resource: is an attribute subresource.

    Attribute:
        :raml_resource: Instance of pyraml.entities.RamlResource.
        :route_name: Name of the :raml_resource:.
    """
    static_parent = get_static_parent(raml_resource)
    if static_parent is None:
        return False
    props = get_resource_schema(static_parent) or {}
    return (route_name in props and
            props[route_name]['type'] in ('dict', 'list'))


def singular_subresource(raml_resource, route_name):
    """ Determine if :raml_resource: is a singular subresource.

    Attribute:
        :raml_resource: Instance of pyraml.entities.RamlResource.
        :route_name: Name of the :raml_resource:.
    """
    static_parent = get_static_parent(raml_resource)
    if static_parent is None:
        return False
    props = get_resource_schema(static_parent) or {}
    if route_name not in props:
        return False
    is_obj = props[route_name]['type'] == 'relationship'
    args = props[route_name].get('args', {})
    single_obj = not args.get('uselist', True)
    return is_obj and single_obj


def closest_secured_by(raml_resource):
    """ Get closest securedBy attr valid for current resource.

    Finds the attr by going up the inheritance tree and stops
    when first 'securedBy' attr is met.

    Attributes:
        :raml_resource: Instance of pyraml.entities.RamlResource.
    """
    secured_by = []
    resource = raml_resource

    while not secured_by and resource:
        secured_by = resource.securedBy or []
        resource = resource.parentResource

    return secured_by
