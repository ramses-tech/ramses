import pytest
from mock import Mock, patch

from ramses import utils


class TestUtils(object):

    def test_contenttypes(self):
        assert utils.ContentTypes.JSON == 'application/json'
        assert utils.ContentTypes.TEXT_XML == 'text/xml'
        assert utils.ContentTypes.MULTIPART_FORMDATA == \
            'multipart/form-data'
        assert utils.ContentTypes.FORM_URLENCODED == \
            'application/x-www-form-urlencoded'

    def test_convert_schema_json(self):
        schema = utils.convert_schema({'foo': 'bar'}, 'application/json')
        assert schema == {'foo': 'bar'}

    def test_convert_schema_json_error(self):
        with pytest.raises(TypeError) as ex:
            utils.convert_schema('foo', 'application/json')
        assert 'Schema is not a valid JSON' in str(ex.value)

    def test_convert_schema_xml(self):
        assert utils.convert_schema({'foo': 'bar'}, 'text/xml') is None

    def test_is_restful_uri(self):
        assert utils.is_restful_uri('/collection')
        assert utils.is_restful_uri('/{id}')
        assert not utils.is_restful_uri('/collection/{id}')

    def test_is_dynamic_uri(self):
        assert utils.is_dynamic_uri('/{id}')
        assert not utils.is_dynamic_uri('/collection')

    def test_clean_dynamic_uri(self):
        clean = utils.clean_dynamic_uri('/{item_id}')
        assert clean == 'item_id'

    def test_generate_model_name(self):
        model_name = utils.generate_model_name('/collectionitems')
        assert model_name == 'Collectionitem'

    def test_find_dynamic_resource(self):
        resource = Mock(resources={'/items': 'foo', '/{id}': 'bar'})
        assert utils.find_dynamic_resource(resource) == 'bar'

    def test_find_dynamic_resource_no_dynamic(self):
        resource = Mock(resources={'/items': 'foo'})
        assert utils.find_dynamic_resource(resource) is None

    def test_find_dynamic_resource_no_resources(self):
        resource = Mock(resources=None)
        assert utils.find_dynamic_resource(resource) is None

    def test_dynamic_part_name(self):
        resource = Mock(resources={'/items': 'foo', '/{myid}': 'bar'})
        part_name = utils.dynamic_part_name(
            resource, 'stories', 'default_id')
        assert part_name == 'stories_myid'

    def test_dynamic_part_name_no_dynamic(self):
        resource = Mock(resources={'/items': 'foo'})
        part_name = utils.dynamic_part_name(
            resource, 'stories', 'default_id')
        assert part_name == 'stories_default_id'

    def test_dynamic_part_name_no_resources(self):
        resource = Mock(resources=None)
        part_name = utils.dynamic_part_name(
            resource, 'stories', 'default_id')
        assert part_name == 'stories_default_id'

    def test_resource_view_attrs_no_dynamic_subres(self):
        resource = Mock(
            resources={
                '/items': 'foo'},
            methods={
                'get': '', 'post': '', 'put': '',
                'patch': '', 'delete': ''}
        )
        attrs = utils.resource_view_attrs(resource, singular=False)
        assert attrs == set(['create', 'delete_many', 'index', 'update_many'])

    def test_resource_view_attrs_dynamic_subres(self):
        resource = Mock(
            resources={
                '/items': 'foo',
                '/{id}': Mock(methods={
                    'get': '', 'put': '', 'patch': '',
                    'DELETE': ''
                })
            },
            methods={
                'get': '', 'POST': '', 'put': '',
                'patch': '', 'delete': ''}
        )
        attrs = utils.resource_view_attrs(resource, singular=False)
        assert attrs == set([
            'create', 'delete_many', 'index', 'update_many',
            'show', 'update', 'delete'
        ])

    def test_resource_view_attrs_singular(self):
        resource = Mock(
            resources={
                '/items': 'foo',
            },
            methods={
                'get': '', 'POST': '', 'put': '',
                'patch': '', 'delete': ''}
        )
        attrs = utils.resource_view_attrs(resource, singular=True)
        assert attrs == set(['create', 'delete', 'show', 'update'])

    def test_resource_view_attrs_no_subresources(self):
        resource = Mock(
            resources=None,
            methods={
                'get': '', 'POST': '', 'put': '',
                'patch': '', 'delete': ''}
        )
        attrs = utils.resource_view_attrs(resource, singular=False)
        assert attrs == set(['create', 'delete_many', 'index', 'update_many'])

    def test_resource_view_attrs_no_methods(self):
        resource = Mock(
            resources={
                '/items': 'foo',
            },
            methods=None
        )
        attrs = utils.resource_view_attrs(resource, singular=False)
        assert attrs == set()

    def test_resource_view_attrs_dynamic_subres_no_methods(self):
        resource = Mock(
            resources={
                '/items': 'foo',
                '/{id}': Mock(methods=None)
            },
            methods={
                'get': '', 'POST': '', 'put': '',
                'patch': '', 'delete': ''}
        )
        attrs = utils.resource_view_attrs(resource, singular=False)
        assert attrs == set([
            'create', 'delete_many', 'index', 'update_many',
        ])

    def test_resource_view_attrs_not_supported_method(self):
        resource = Mock(
            resources={
                '/items': 'foo',
            },
            methods={'nice_method': ''}
        )
        attrs = utils.resource_view_attrs(resource, singular=False)
        assert attrs == set()

    def test_resource_schema(self):
        body = Mock(schema={'foo': 'bar'})
        method = Mock(body={'application/json': body})
        resource = Mock(methods={'post': method})
        assert utils.resource_schema(resource) == {'foo': 'bar'}
        resource = Mock(methods={'put': method})
        assert utils.resource_schema(resource) == {'foo': 'bar'}
        resource = Mock(methods={'patch': method})
        assert utils.resource_schema(resource) == {'foo': 'bar'}

    def test_resource_schema_methods_order(self):
        body = Mock(schema={'foo': 'bar'})
        method = Mock(body={'application/json': body})
        body2 = Mock(schema={'foo2': 'bar2'})
        method2 = Mock(body={'application/json': body2})
        resource = Mock(methods={
            'post': method,
            'patch': method2,
        })
        assert utils.resource_schema(resource) == {'foo': 'bar'}

    def test_resource_schema_no_propper_method(self):
        with pytest.raises(ValueError) as ex:
            utils.resource_schema(Mock(methods=None))
        assert str(ex.value) == 'No methods to setup database schema from'

        with pytest.raises(ValueError) as ex:
            utils.resource_schema(Mock(methods={'get': ''}))
        assert str(ex.value) == 'No methods to setup database schema from'

    def test_resource_schema_no_method_body(self):
        method = Mock(body=None)
        resource = Mock(methods={'post': method})
        assert utils.resource_schema(resource) is None

    def test_resource_schema_schema_none(self):
        body = Mock(schema=None)
        method = Mock(body={'application/json': body})
        resource = Mock(methods={'post': method})
        assert utils.resource_schema(resource) is None

    def test_resource_schema_invalid_content_type(self):
        body = Mock(schema={'foo': 'bar'})
        method = Mock(body={'dsadadasdasdasdasd': body})
        resource = Mock(methods={'post': method})
        assert utils.resource_schema(resource) is None

    def test_is_dynamic_resource_no_resource(self):
        assert not utils.is_dynamic_resource(None)

    def test_is_dynamic_resource_no_parent(self):
        resource = Mock(parentResource=None)
        assert not utils.is_dynamic_resource(resource)

    def test_is_dynamic_resource(self):
        resource = Mock()
        parent = Mock(resources={'/{id}': resource})
        resource.parentResource = parent
        assert utils.is_dynamic_resource(resource)

    def test_is_dynamic_resource_not_dynamic(self):
        resource = Mock()
        parent = Mock(resources={'/items': resource})
        resource.parentResource = parent
        assert not utils.is_dynamic_resource(resource)

    def test_is_dynamic_resource_no_resources(self):
        resource = Mock()
        parent = Mock(resources=None)
        resource.parentResource = parent
        assert not utils.is_dynamic_resource(resource)

    def test_get_static_parent(self):
        resource = Mock()
        parent = Mock(
            resources={'/{id}': resource},
            parentResource=Mock(resources=None))
        resource.parentResource = parent
        assert utils.get_static_parent(resource) is parent

    def test_get_static_parent_nested(self):
        resource = Mock()
        parent2 = Mock(
            parentResource=Mock(resources=None))
        parent = Mock(
            resources={'/{id}': resource},
            parentResource=parent2)
        parent2.resources = {'/{id}': parent}
        resource.parentResource = parent
        assert utils.get_static_parent(resource) is parent2

    @patch('ramses.utils.get_static_parent')
    @patch('ramses.utils.resource_schema')
    def test_attr_subresource_no_static_parent(self, mock_schema, mock_par):
        mock_par.return_value = None
        assert not utils.attr_subresource('foo', 1)
        mock_par.assert_called_once_with('foo')

    @patch('ramses.utils.get_static_parent')
    @patch('ramses.utils.resource_schema')
    def test_attr_subresource_no_schema(self, mock_schema, mock_par):
        parent = Mock()
        mock_par.return_value = parent
        mock_schema.return_value = None
        assert not utils.attr_subresource('foo', 1)
        mock_par.assert_called_once_with('foo')
        mock_schema.assert_called_once_with(parent)

    @patch('ramses.utils.get_static_parent')
    @patch('ramses.utils.resource_schema')
    def test_attr_subresource_not_attr(self, mock_schema, mock_par):
        parent = Mock()
        mock_par.return_value = parent
        mock_schema.return_value = {
            'properties': {
                'route_name': {
                    'type': 'string'
                }
            }
        }
        assert not utils.attr_subresource('resource', 'route_name')
        mock_par.assert_called_once_with('resource')
        mock_schema.assert_called_once_with(parent)

    @patch('ramses.utils.get_static_parent')
    @patch('ramses.utils.resource_schema')
    def test_attr_subresource_dict(self, mock_schema, mock_par):
        parent = Mock()
        mock_par.return_value = parent
        mock_schema.return_value = {
            'properties': {
                'route_name': {
                    'type': 'dict'
                },
                'route_name2': {
                    'type': 'list'
                }
            }
        }
        assert utils.attr_subresource('resource', 'route_name')
        mock_par.assert_called_once_with('resource')
        mock_schema.assert_called_once_with(parent)
        assert utils.attr_subresource('resource', 'route_name2')

    @patch('ramses.utils.get_static_parent')
    @patch('ramses.utils.resource_schema')
    def test_singular_subresource_no_static_parent(self, mock_schema, mock_par):
        mock_par.return_value = None
        assert not utils.singular_subresource('foo', 1)
        mock_par.assert_called_once_with('foo')

    @patch('ramses.utils.get_static_parent')
    @patch('ramses.utils.resource_schema')
    def test_singular_subresource_no_schema(self, mock_schema, mock_par):
        parent = Mock()
        mock_par.return_value = parent
        mock_schema.return_value = None
        assert not utils.singular_subresource('foo', 1)
        mock_par.assert_called_once_with('foo')
        mock_schema.assert_called_once_with(parent)

    @patch('ramses.utils.get_static_parent')
    @patch('ramses.utils.resource_schema')
    def test_singular_subresource_not_attr(self, mock_schema, mock_par):
        parent = Mock()
        mock_par.return_value = parent
        mock_schema.return_value = {
            'properties': {
                'route_name': {
                    'type': 'string'
                }
            }
        }
        assert not utils.singular_subresource('resource', 'route_name')
        mock_par.assert_called_once_with('resource')
        mock_schema.assert_called_once_with(parent)

    @patch('ramses.utils.get_static_parent')
    @patch('ramses.utils.resource_schema')
    def test_singular_subresource_dict(self, mock_schema, mock_par):
        parent = Mock()
        mock_par.return_value = parent
        mock_schema.return_value = {
            'properties': {
                'route_name': {
                    'type': 'relationship',
                    'args': {'uselist': False}
                },
            }
        }
        assert utils.singular_subresource('resource', 'route_name')
        mock_par.assert_called_once_with('resource')
        mock_schema.assert_called_once_with(parent)

    def test_closest_secured_by(self):
        parent = Mock(securedBy=['foo'])
        resource = Mock(securedBy=['bar'], parentResource=parent)
        assert utils.closest_secured_by(resource) == ['bar']

    def test_closest_secured_by_parent(self):
        parent = Mock(securedBy=['foo'])
        resource = Mock(securedBy=None, parentResource=parent)
        assert utils.closest_secured_by(resource) == ['foo']

    def test_closest_secured_no_secured(self):
        parent = Mock(securedBy=None, parentResource=None)
        resource = Mock(securedBy=None, parentResource=parent)
        assert utils.closest_secured_by(resource) == []
