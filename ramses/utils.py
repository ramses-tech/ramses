from __future__ import print_function
import inflection


class ContentTypes(object):
    JSON = 'application/json'
    TEXT_XML = 'text/xml'
    MULTIPART_FORMDATA = 'multipart/form-data'
    FORM_URLENCODED = 'application/x-www-form-urlencoded'


def fields_dict(schema, schema_name):
    if schema_name == ContentTypes.JSON:
        return schema['properties']
    if schema_name == ContentTypes.TEXT_XML:
        # Process XML schema
        pass


def make_route_name(name):
    route_name = name.strip('/')
    route_name = route_name.replace('/', '_').replace('{', '')
    route_name = route_name.replace('}', '')
    return route_name


def is_dynamic_uri(uri):
    return uri.endswith('}')


def unwrap_dynamic_uri(uri):
    return uri.replace('/', '').replace('{', '').strip('}', '')


def resource_model_name(resource):
    return inflection.camelize(resource.uid.replace(':', '_'))


def resource_view_attrs(raml_resource):
    from .views import collection_methods, item_methods

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
