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

    def test_is_dynamic_uri(self):
        assert utils.is_dynamic_uri('/{id}')
        assert not utils.is_dynamic_uri('/collection')

    def test_clean_dynamic_uri(self):
        clean = utils.clean_dynamic_uri('/{item_id}')
        assert clean == 'item_id'

    def test_generate_model_name(self):
        resource = Mock(path='/zoo/alien-users')
        model_name = utils.generate_model_name(resource)
        assert model_name == 'AlienUser'

    @patch.object(utils, 'get_resource_children')
    def test_dynamic_part_name(self, get_children):
        get_children.return_value = [
            Mock(path='/items'), Mock(path='/{myid}')]
        resource = Mock()
        part_name = utils.dynamic_part_name(
            resource, 'stories', 'default_id')
        assert part_name == 'stories_myid'
        get_children.assert_called_once_with(resource)

    @patch.object(utils, 'get_resource_children')
    def test_dynamic_part_name_no_dynamic(self, get_children):
        get_children.return_value = [Mock(path='/items')]
        resource = Mock()
        part_name = utils.dynamic_part_name(
            resource, 'stories', 'default_id')
        assert part_name == 'stories_default_id'
        get_children.assert_called_once_with(resource)

    @patch.object(utils, 'get_resource_children')
    def test_dynamic_part_name_no_resources(self, get_children):
        get_children.return_value = []
        resource = Mock(resources=None)
        part_name = utils.dynamic_part_name(
            resource, 'stories', 'default_id')
        assert part_name == 'stories_default_id'
        get_children.assert_called_once_with(resource)

    def test_extract_dynamic_part(self):
        assert utils.extract_dynamic_part('/stories/{id}/foo') == 'id'
        assert utils.extract_dynamic_part('/stories/{id}') == 'id'

    def test_extract_dynamic_part_fail(self):
        assert utils.extract_dynamic_part('/stories/id') is None

    def _get_mock_method_resources(self, *methods):
        return [Mock(method=meth) for meth in methods]

    @patch.object(utils, 'get_resource_children')
    @patch.object(utils, 'get_resource_siblings')
    def test_resource_view_attrs_no_dynamic_subres(self, get_sib, get_child):
        get_child.return_value = []
        get_sib.return_value = self._get_mock_method_resources(
            'get', 'post', 'put', 'patch', 'delete')
        resource = Mock()
        attrs = utils.resource_view_attrs(resource, singular=False)
        get_sib.assert_called_once_with(resource)
        get_child.assert_called_once_with(resource)
        assert attrs == set(['create', 'delete_many', 'index', 'update_many'])

    @patch.object(utils, 'get_resource_children')
    @patch.object(utils, 'get_resource_siblings')
    def test_resource_view_attrs_dynamic_subres(self, get_sib, get_child):
        get_child.return_value = self._get_mock_method_resources(
            'get', 'put', 'patch', 'delete')
        get_sib.return_value = self._get_mock_method_resources(
            'get', 'post', 'put', 'patch', 'delete')
        resource = Mock()
        attrs = utils.resource_view_attrs(resource, singular=False)
        get_sib.assert_called_once_with(resource)
        get_child.assert_called_once_with(resource)
        assert attrs == set([
            'create', 'delete_many', 'index', 'update_many',
            'show', 'update', 'delete', 'replace'
        ])

    @patch.object(utils, 'get_resource_children')
    @patch.object(utils, 'get_resource_siblings')
    def test_resource_view_attrs_singular(self, get_sib, get_child):
        get_child.return_value = []
        get_sib.return_value = self._get_mock_method_resources(
            'get', 'post', 'put', 'patch', 'delete')
        resource = Mock()
        attrs = utils.resource_view_attrs(resource, singular=True)
        get_sib.assert_called_once_with(resource)
        get_child.assert_called_once_with(resource)
        assert attrs == set(['create', 'delete', 'show', 'update', 'replace'])

    @patch.object(utils, 'get_resource_children')
    @patch.object(utils, 'get_resource_siblings')
    def test_resource_view_attrs_no_subresources(self, get_sib, get_child):
        child_res = self._get_mock_method_resources('get')
        child_res[0].path = '/items'
        get_child.return_value = child_res
        get_sib.return_value = self._get_mock_method_resources(
            'get', 'post', 'put', 'patch', 'delete')
        resource = Mock()
        attrs = utils.resource_view_attrs(resource, singular=False)
        get_sib.assert_called_once_with(resource)
        get_child.assert_called_once_with(resource)
        assert attrs == set(['create', 'delete_many', 'index', 'update_many'])

    @patch.object(utils, 'get_resource_children')
    @patch.object(utils, 'get_resource_siblings')
    def test_resource_view_attrs_no_methods(self, get_sib, get_child):
        get_sib.return_value = []
        get_child.return_value = []
        resource = Mock()
        attrs = utils.resource_view_attrs(resource, singular=False)
        get_sib.assert_called_once_with(resource)
        get_child.assert_called_once_with(resource)
        assert attrs == set()

    @patch.object(utils, 'get_resource_children')
    @patch.object(utils, 'get_resource_siblings')
    def test_resource_view_attrs_not_supported_method(
            self, get_sib, get_child):
        get_sib.return_value = []
        get_child.return_value = self._get_mock_method_resources(
            'nice_method')
        resource = Mock()
        attrs = utils.resource_view_attrs(resource, singular=False)
        assert attrs == set()

    def test_resource_schema_no_body(self):
        resource = Mock(body=None)
        with pytest.raises(ValueError) as ex:
            utils.resource_schema(resource)
        expected = 'RAML resource has no body to setup database'
        assert expected in str(ex.value)

    def test_resource_schema_no_schemas(self):
        resource = Mock(body=[Mock(schema=None), Mock(schema='')])
        assert utils.resource_schema(resource) is None

    def test_resource_schema_success(self):
        resource = Mock(body=[
            Mock(schema={'foo': 'bar'},
                 mime_type=utils.ContentTypes.JSON)
        ])
        assert utils.resource_schema(resource) == {'foo': 'bar'}

    def test_is_dynamic_resource_no_resource(self):
        assert not utils.is_dynamic_resource(None)

    def test_is_dynamic_resource_dynamic(self):
        resource = Mock(path='/{id}')
        assert utils.is_dynamic_resource(resource)

    def test_is_dynamic_resource_not_dynamic(self):
        resource = Mock(path='/stories')
        assert not utils.is_dynamic_resource(resource)

    def test_get_static_parent(self):
        parent = Mock(path='/stories', method='post')
        resource = Mock(path='/{id}')
        resource.parent = parent
        assert utils.get_static_parent(resource, method='post') is parent

    def test_get_static_parent_none(self):
        resource = Mock(path='/{id}')
        resource.parent = None
        assert utils.get_static_parent(resource, method='post') is None

    def test_get_static_parent_wrong_parent_method(self):
        root = Mock(resources=[
            Mock(path='/stories', method='options'),
            Mock(path='/users', method='post'),
            Mock(path='/stories', method='post'),
        ])
        parent = Mock(path='/stories', method='get', root=root)
        resource = Mock(path='/{id}')
        resource.parent = parent
        res = utils.get_static_parent(resource, method='post')
        assert res.method == 'post'
        assert res.path == '/stories'

    def test_get_static_parent_without_method_parent_present(self):
        root = Mock(resources=[
            Mock(path='/stories', method='options'),
            Mock(path='/stories', method='post'),
        ])
        parent = Mock(path='/stories', method='get', root=root)
        resource = Mock(path='/{id}')
        resource.parent = parent
        res = utils.get_static_parent(resource)
        assert res.method == 'get'
        assert res.path == '/stories'

    def test_get_static_parent_none_found_in_root(self):
        root = Mock(resources=[
            Mock(path='/stories', method='get'),
        ])
        parent = Mock(path='/stories', method='options', root=root)
        resource = Mock(path='/{id}')
        resource.parent = parent
        assert utils.get_static_parent(resource, method='post') is None

    @patch('ramses.utils.get_static_parent')
    @patch('ramses.utils.resource_schema')
    def test_attr_subresource_no_static_parent(self, mock_schema, mock_par):
        mock_par.return_value = None
        assert not utils.attr_subresource('foo', 1)
        mock_par.assert_called_once_with('foo', method='POST')

    @patch('ramses.utils.get_static_parent')
    @patch('ramses.utils.resource_schema')
    def test_attr_subresource_no_schema(self, mock_schema, mock_par):
        parent = Mock()
        mock_par.return_value = parent
        mock_schema.return_value = None
        assert not utils.attr_subresource('foo', 1)
        mock_par.assert_called_once_with('foo', method='POST')
        mock_schema.assert_called_once_with(parent)

    @patch('ramses.utils.get_static_parent')
    @patch('ramses.utils.resource_schema')
    def test_attr_subresource_not_attr(self, mock_schema, mock_par):
        parent = Mock()
        mock_par.return_value = parent
        mock_schema.return_value = {
            'properties': {
                'route_name': {
                    '_db_settings': {
                        'type': 'string'
                    }
                }
            }
        }
        assert not utils.attr_subresource('resource', 'route_name')
        mock_par.assert_called_once_with('resource', method='POST')
        mock_schema.assert_called_once_with(parent)

    @patch('ramses.utils.get_static_parent')
    @patch('ramses.utils.resource_schema')
    def test_attr_subresource_dict(self, mock_schema, mock_par):
        parent = Mock()
        mock_par.return_value = parent
        mock_schema.return_value = {
            'properties': {
                'route_name': {
                    '_db_settings': {
                        'type': 'dict'
                    }
                },
                'route_name2': {
                    '_db_settings': {
                        'type': 'list'
                    }
                }
            }
        }
        assert utils.attr_subresource('resource', 'route_name')
        mock_par.assert_called_once_with('resource', method='POST')
        mock_schema.assert_called_once_with(parent)
        assert utils.attr_subresource('resource', 'route_name2')

    @patch('ramses.utils.get_static_parent')
    @patch('ramses.utils.resource_schema')
    def test_singular_subresource_no_static_parent(self, mock_schema, mock_par):
        mock_par.return_value = None
        assert not utils.singular_subresource('foo', 1)
        mock_par.assert_called_once_with('foo', method='POST')

    @patch('ramses.utils.get_static_parent')
    @patch('ramses.utils.resource_schema')
    def test_singular_subresource_no_schema(self, mock_schema, mock_par):
        parent = Mock()
        mock_par.return_value = parent
        mock_schema.return_value = None
        assert not utils.singular_subresource('foo', 1)
        mock_par.assert_called_once_with('foo', method='POST')
        mock_schema.assert_called_once_with(parent)

    @patch('ramses.utils.get_static_parent')
    @patch('ramses.utils.resource_schema')
    def test_singular_subresource_not_attr(self, mock_schema, mock_par):
        parent = Mock()
        mock_par.return_value = parent
        mock_schema.return_value = {
            'properties': {
                'route_name': {
                    '_db_settings': {
                        'type': 'string'
                    }
                }
            }
        }
        assert not utils.singular_subresource('resource', 'route_name')
        mock_par.assert_called_once_with('resource', method='POST')
        mock_schema.assert_called_once_with(parent)

    @patch('ramses.utils.get_static_parent')
    @patch('ramses.utils.resource_schema')
    def test_singular_subresource_dict(self, mock_schema, mock_par):
        parent = Mock()
        mock_par.return_value = parent
        mock_schema.return_value = {
            'properties': {
                'route_name': {
                    '_db_settings': {
                        'type': 'relationship',
                        'uselist': False
                    }
                },
            }
        }
        assert utils.singular_subresource('resource', 'route_name')
        mock_par.assert_called_once_with('resource', method='POST')
        mock_schema.assert_called_once_with(parent)

    def test_is_callable_tag_not_str(self):
        assert not utils.is_callable_tag(1)
        assert not utils.is_callable_tag(None)

    def test_is_callable_tag_not_tag(self):
        assert not utils.is_callable_tag('foobar')

    def test_is_callable_tag(self):
        assert utils.is_callable_tag('{{foobar}}')

    def test_resolve_to_callable_not_found(self):
        with pytest.raises(ImportError) as ex:
            utils.resolve_to_callable('{{foobar}}')
        assert str(ex.value) == 'Failed to load callable `foobar`'

    def test_resolve_to_callable_registry(self):
        from ramses import registry

        @registry.add
        def foo():
            pass

        func = utils.resolve_to_callable('{{foo}}')
        assert func is foo
        func = utils.resolve_to_callable('foo')
        assert func is foo

    def test_resolve_to_callable_dotted_path(self):
        from datetime import datetime
        func = utils.resolve_to_callable('{{datetime.datetime}}')
        assert func is datetime
        func = utils.resolve_to_callable('datetime.datetime')
        assert func is datetime

    def test_get_events_map(self):
        from nefertari import events
        events_map = utils.get_events_map()
        after, before = events_map['after'], events_map['before']
        after_set, before_set = after.pop('set'), before.pop('set')
        assert sorted(events.BEFORE_EVENTS.keys()) == sorted(
            before.keys())
        assert sorted(events.AFTER_EVENTS.keys()) == sorted(
            after.keys())
        assert after_set == [
            events.AfterCreate,
            events.AfterUpdate,
            events.AfterReplace,
            events.AfterUpdateMany,
            events.AfterRegister,
        ]
        assert before_set == [
            events.BeforeCreate,
            events.BeforeUpdate,
            events.BeforeReplace,
            events.BeforeUpdateMany,
            events.BeforeRegister,
        ]

    def test_patch_view_model(self):
        view_cls = Mock()
        model1 = Mock()
        model2 = Mock()
        view_cls.Model = model1

        with utils.patch_view_model(view_cls, model2):
            view_cls.Model()

        assert view_cls.Model is model1
        assert not model1.called
        model2.assert_called_once_with()

    def test_get_route_name(self):
        resource_uri = '/foo-=-=-=-123'
        assert utils.get_route_name(resource_uri) == 'foo123'

    def test_get_resource_uri(self):
        resource = Mock(path='/foobar/zoo ')
        assert utils.get_resource_uri(resource) == 'zoo'
