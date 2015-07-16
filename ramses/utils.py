import logging

import six
import inflection


log = logging.getLogger(__name__)


class ContentTypes(object):
    """ ContentType values.

    """
    JSON = 'application/json'
    TEXT_XML = 'text/xml'
    MULTIPART_FORMDATA = 'multipart/form-data'
    FORM_URLENCODED = 'application/x-www-form-urlencoded'


def convert_schema(raml_schema, mime_type):
    """ Restructure `raml_schema` to a dictionary that has 'properties'
    as well as other schema keys/values.

    The resulting dictionary looks like this::

    {
        "properties": {
            "field1": {
                "required": boolean,
                "type": ...,
                ...more field options
            },
            ...more properties
        },
        "public_fields": [...],
        "auth_fields": [...],
        ...more schema options
    }

    Arguments:
        :raml_schema: pyraml.entities.RamlBody.schema.
        :mime_type: ContentType of the schema as a string from RAML file. Only
            JSON is currently supported.
    """
    if mime_type == ContentTypes.JSON:
        if not isinstance(raml_schema, dict):
            raise TypeError(
                'Schema is not a valid JSON. Please check your '
                'schema syntax.\n{}...'.format(str(raml_schema)[:60]))
        return raml_schema
    if mime_type == ContentTypes.TEXT_XML:
        # Process XML schema
        pass


def is_restful_uri(uri):
    """ Check whether `uri` is a RESTful uri.

    Uri is assumed to be restful if it only contains a single token.
    E.g. 'stories' and 'users' but NOT 'stories/comments' and 'users/{id}'

    Arguments:
        :uri: URI as a string
    """
    uri = uri.strip('/')
    return '/' not in uri


def is_dynamic_uri(uri):
    """ Determine whether `uri` is a dynamic uri or not.

    Assumes a dynamic uri is one that ends with '}' which is a Pyramid
    way to define dynamic parts in uri.

    Arguments:
        :uri: URI as a string.
    """
    return uri.strip('/').endswith('}')


def clean_dynamic_uri(uri):
    """ Strips /, {, } from dynamic `uri`.

    Arguments:
        :uri: URI as a string.
    """
    return uri.replace('/', '').replace('{', '').replace('}', '')


def generate_model_name(name):
    """ Generate model name.

    Arguments:
        :name: String representing a field or route name.
    """
    model_name = inflection.camelize(name.strip('/'))
    return inflection.singularize(model_name)


def dynamic_part_name(raml_resource, clean_uri, pk_field):
    """ Generate a dynamic part for a resource :raml_resource:.

    A dynamic part is generated using 2 parts: :clean_uri: of the resource
    and the dynamic part of any dymanic subresources. If :raml_resource:
    has no dynamic subresources, 'id' is used as the 2nd part.
    E.g. if your dynamic part on route 'stories' is named 'superId' then
    dynamic part will be 'stories_superId'.

    Arguments:
        :raml_resource: Instance of pyraml.entities.RamlResource for which
            dynamic part name is being generated.
        :clean_uri: Cleaned URI of :raml_resource:
    """
    subresources = get_resource_children(raml_resource)
    dynamic_uris = [res.path for res in subresources
                    if is_dynamic_uri(res.path)]
    if dynamic_uris:
        dynamic_part = clean_dynamic_uri(dynamic_uris[0])
    else:
        dynamic_part = pk_field
    return '_'.join([clean_uri, dynamic_part])


def resource_view_attrs(raml_resource, singular=False):
    """ Generate view method names needed for `raml_resource` view.

    Collects HTTP method names from `raml_resource.methods` and
    dynamic child `methods` if a child exists. Collected methods are
    then translated  to `nefertari.view.BaseView` method names,
    each of which is used to process a particular HTTP method request.

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

    http_methods = list((raml_resource.methods or {}).keys())
    attrs = [collection_methods.get(m.lower()) for m in http_methods]

    # Check if resource has dynamic subresource like collection/{id}
    subresources = raml_resource.resources or {}
    dynamic_res = [res for uri, res in subresources.items()
                   if is_dynamic_uri(uri)]

    # If dynamic subresource exists, add its methods to attrs, as both
    # resources are handled by a single view
    if dynamic_res and dynamic_res[0].methods:
        http_submethods = list((dynamic_res[0].methods or {}).keys())
        attrs += [item_methods.get(m.lower()) for m in http_submethods]

    return set(filter(bool, attrs))


def resource_schema(raml_resource):
    """ Get schema properties of RAML resource :raml_resource:.

    Must be called with RAML resource that defines body schema.

    The process follows these steps:
      * :raml_resource: post, put, patch methods body schemas are checked
        to see if a schema is defined.
      * If found, the schema is restructured into a dictionary of form
        {field_name: {required: boolean, type: type_name}} and returned.

    Arguments:
        :raml_resource: Instance of pyraml.entities.RamlResource.
    """
    # NOTE: Must be called with resource that defines body schema
    log.info('Searching for model schema')
    if not raml_resource.body:
        raise ValueError('RAML resource has no body to setup database '
                         'schema from')

    for body in raml_resource.body:
        if body.schema:
            return convert_schema(body.schema, body.mime_type)
    log.debug('No model schema found.')


def is_dynamic_resource(raml_resource):
    """ Determine if :raml_resource: is a dynamic resource.

    Arguments:
        :raml_resource: Instance of pyraml.entities.RamlResource.
    """
    return raml_resource and is_dynamic_uri(raml_resource.path)


def get_static_parent(raml_resource, method=None):
    """ Get static parent resource of :raml_resource: with HTTP
    method :method:.

    Arguments:
        :raml_resource:Instance of pyraml.entities.RamlResource.
    """
    parent = raml_resource.parent
    while is_dynamic_resource(parent):
        parent = parent.parent

    if parent is None:
        return parent

    match_method = method is not None
    if match_method:
        if parent.method.upper() == method.upper():
            return parent
    else:
        return parent

    for res in parent.root.resources:
        if res.path == parent.path:
            if res.method.upper() == method.upper():
                return res


def attr_subresource(raml_resource, route_name):
    """ Determine if :raml_resource: is an attribute subresource.

    Attribute:
        :raml_resource: Instance of pyraml.entities.RamlResource.
        :route_name: Name of the :raml_resource:.
    """
    static_parent = get_static_parent(raml_resource, method='POST')
    if static_parent is None:
        return False
    schema = resource_schema(static_parent) or {}
    properties = schema.get('properties', {})
    return (route_name in properties and
            properties[route_name]['type'] in ('dict', 'list'))


def singular_subresource(raml_resource, route_name):
    """ Determine if :raml_resource: is a singular subresource.

    Attribute:
        :raml_resource: Instance of pyraml.entities.RamlResource.
        :route_name: Name of the :raml_resource:.
    """
    static_parent = get_static_parent(raml_resource, method='POST')
    if static_parent is None:
        return False
    schema = resource_schema(static_parent) or {}
    properties = schema.get('properties', {})
    if route_name not in properties:
        return False
    is_obj = properties[route_name]['type'] == 'relationship'
    args = properties[route_name].get('args', {})
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


def is_callable_tag(tag):
    """ Determine whether :tag: is a valid callable string tag.

    String is assumed to be valid callable if it starts with '{{'
    and ends with '}}'.
    """
    return (isinstance(tag, six.string_types) and
            tag.strip().startswith('{{') and
            tag.strip().endswith('}}'))


def resolve_to_callable(callable_name):
    """ Resolve string :callable_name: to a callable.

    Arguments:
        :callable_name: String representing callable name as registered
            in ramses registry or dotted import path of callable. Can be
            wrapped in double curly brackets, e.g. '{{my_callable}}'.
    """
    from . import registry
    clean_callable_name = callable_name.replace(
        '{{', '').replace('}}', '').strip()
    try:
        return registry.get(clean_callable_name)
    except KeyError:
        try:
            from zope.dottedname.resolve import resolve
            return resolve(clean_callable_name)
        except ImportError:
            raise ImportError(
                'Failed to load callable `{}`'.format(clean_callable_name))


def get_resource_siblings(raml_resource):
    path = raml_resource.path
    return [res for res in raml_resource.root.resources
            if res.path == path]


def get_resource_children(raml_resource):
    path = raml_resource.path
    return [res for res in raml_resource.root.resources
            if res.parent and res.parent.path == path]


def get_resource_direct_parents(raml_resource):
    return get_resource_siblings(raml_resource.parent)
