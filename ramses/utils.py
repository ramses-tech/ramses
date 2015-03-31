
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
