import logging
from contextlib import contextmanager

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

    :param raml_schema: RAML request body schema.
    :param mime_type: ContentType of the schema as a string from RAML
        file. Only JSON is currently supported.
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


def is_dynamic_uri(uri):
    """ Determine whether `uri` is a dynamic uri or not.

    Assumes a dynamic uri is one that ends with '}' which is a Pyramid
    way to define dynamic parts in uri.

    :param uri: URI as a string.
    """
    return uri.strip('/').endswith('}')


def clean_dynamic_uri(uri):
    """ Strips /, {, } from dynamic `uri`.

    :param uri: URI as a string.
    """
    return uri.replace('/', '').replace('{', '').replace('}', '')


def generate_model_name(name):
    """ Generate model name.

    :param name: String representing a field or route name.
    """
    model_name = inflection.camelize(name.strip('/'))
    return inflection.singularize(model_name)


def dynamic_part_name(raml_resource, clean_uri, pk_field):
    """ Generate a dynamic part for a resource :raml_resource:.

    A dynamic part is generated using 2 parts: :clean_uri: of the resource
    and the dynamic part of first dynamic child resources. If
    :raml_resource: has no dynamic child resources, 'id' is used as the
    2nd part.
    E.g. if your dynamic part on route 'stories' is named 'superId' then
    dynamic part will be 'stories_superId'.

    :param raml_resource: Instance of ramlfications.raml.ResourceNode for
        which dynamic part name is being generated.
    :param clean_uri: Cleaned URI of :raml_resource:
    :param pk_field: Model Primary Key field name.
    """
    subresources = get_resource_children(raml_resource)
    dynamic_uris = [res.path for res in subresources
                    if is_dynamic_uri(res.path)]
    if dynamic_uris:
        dynamic_part = extract_dynamic_part(dynamic_uris[0])
    else:
        dynamic_part = pk_field
    return '_'.join([clean_uri, dynamic_part])


def extract_dynamic_part(uri):
    """ Extract dynamic url part from :uri: string.

    :param uri: URI string that may contain dynamic part.
    """
    for part in uri.split('/'):
        part = part.strip()
        if part.startswith('{') and part.endswith('}'):
            return clean_dynamic_uri(part)


def resource_view_attrs(raml_resource, singular=False):
    """ Generate view method names needed for `raml_resource` view.

    Collects HTTP method names from resource siblings and dynamic children
    if exist. Collected methods are then translated  to
    `nefertari.view.BaseView` method names, each of which is used to
    process a particular HTTP method request.

    Maps of {HTTP_method: view_method} `collection_methods` and
    `item_methods` are used to convert collection and item methods
    respectively.

    :param raml_resource: Instance of ramlfications.raml.ResourceNode
    :param singular: Boolean indicating if resource is singular or not
    """
    from .views import collection_methods, item_methods
    # Singular resource doesn't have collection methods though
    # it looks like a collection
    if singular:
        collection_methods = item_methods

    siblings = get_resource_siblings(raml_resource)
    http_methods = [sibl.method.lower() for sibl in siblings]
    attrs = [collection_methods.get(method) for method in http_methods]

    # Check if resource has dynamic child resource like collection/{id}
    # If dynamic child resource exists, add its siblings' methods to attrs,
    # as both resources are handled by a single view
    children = get_resource_children(raml_resource)
    http_submethods = [child.method.lower() for child in children
                       if is_dynamic_uri(child.path)]
    attrs += [item_methods.get(method) for method in http_submethods]

    return set(filter(bool, attrs))


def resource_schema(raml_resource):
    """ Get schema properties of RAML resource :raml_resource:.

    Must be called with RAML resource that defines body schema. First
    body that defines schema is used. Schema is converted on return using
    'convert_schema'.

    :param raml_resource: Instance of ramlfications.raml.ResourceNode of
        POST method.
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

    :param raml_resource: Instance of ramlfications.raml.ResourceNode.
    """
    return raml_resource and is_dynamic_uri(raml_resource.path)


def get_static_parent(raml_resource, method=None):
    """ Get static parent resource of :raml_resource: with HTTP
    method :method:.

    :param raml_resource:Instance of ramlfications.raml.ResourceNode.
    :param method: HTTP method name which matching static resource
        must have.
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

    :param raml_resource: Instance of ramlfications.raml.ResourceNode.
    :param route_name: Name of the :raml_resource:.
    """
    static_parent = get_static_parent(raml_resource, method='POST')
    if static_parent is None:
        return False
    schema = resource_schema(static_parent) or {}
    properties = schema.get('properties', {})
    if route_name in properties:
        db_settings = properties[route_name].get('_db_settings', {})
        return db_settings.get('type') in ('dict', 'list')
    return False


def singular_subresource(raml_resource, route_name):
    """ Determine if :raml_resource: is a singular subresource.

    :param raml_resource: Instance of ramlfications.raml.ResourceNode.
    :param route_name: Name of the :raml_resource:.
    """
    static_parent = get_static_parent(raml_resource, method='POST')
    if static_parent is None:
        return False
    schema = resource_schema(static_parent) or {}
    properties = schema.get('properties', {})
    if route_name not in properties:
        return False

    db_settings = properties[route_name].get('_db_settings', {})
    is_obj = db_settings.get('type') == 'relationship'
    single_obj = not db_settings.get('uselist', True)
    return is_obj and single_obj


def is_callable_tag(tag):
    """ Determine whether :tag: is a valid callable string tag.

    String is assumed to be valid callable if it starts with '{{'
    and ends with '}}'.

    :param tag: String name of tag.
    """
    return (isinstance(tag, six.string_types) and
            tag.strip().startswith('{{') and
            tag.strip().endswith('}}'))


def resolve_to_callable(callable_name):
    """ Resolve string :callable_name: to a callable.

    :param callable_name: String representing callable name as registered
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
    """ Get siblings of :raml_resource:.

    :param raml_resource: Instance of ramlfications.raml.ResourceNode.
    """
    path = raml_resource.path
    return [res for res in raml_resource.root.resources
            if res.path == path]


def get_resource_children(raml_resource):
    """ Get children of :raml_resource:.

    :param raml_resource: Instance of ramlfications.raml.ResourceNode.
    """
    path = raml_resource.path
    return [res for res in raml_resource.root.resources
            if res.parent and res.parent.path == path]


def get_events_map():
    """ Prepare map of event subscribers.

    * Extends copies of BEFORE_EVENTS and AFTER_EVENTS maps with
        'set' action.
    * Returns map of {before/after: {action: event class(es)}}
    """
    from nefertari import events
    set_keys = ('create', 'update', 'replace', 'update_many', 'register')
    before_events = events.BEFORE_EVENTS.copy()
    before_events['set'] = [before_events[key] for key in set_keys]
    after_events = events.AFTER_EVENTS.copy()
    after_events['set'] = [after_events[key] for key in set_keys]
    return {
        'before': before_events,
        'after': after_events,
    }


@contextmanager
def patch_view_model(view_cls, model_cls):
    """ Patches view_cls.Model with model_cls.

    :param view_cls: View class "Model" param of which should be
        patched
    :param model_cls: Model class which should be used to patch
        view_cls.Model
    """
    original_model = view_cls.Model
    view_cls.Model = model_cls

    try:
        yield
    finally:
        view_cls.Model = original_model
