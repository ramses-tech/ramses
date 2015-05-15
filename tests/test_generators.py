import pytest
from mock import Mock, patch, call

from ramses import generators
from .fixtures import engine_mock


class TestGenerationHelpers(object):

    @patch('ramses.models.get_existing_model')
    def test_setup_data_model_existing_model(self, mock_get):
        mock_get.return_value = 1
        model, auth_model = generators.setup_data_model('foo', 'Bar')
        assert not auth_model
        assert model == 1
        mock_get.assert_called_once_with('Bar')

    @patch('ramses.generators.resource_schema')
    @patch('ramses.models.get_existing_model')
    def test_setup_data_model_no_schema(self, mock_get, mock_schema):
        mock_get.return_value = None
        mock_schema.return_value = None
        with pytest.raises(Exception) as ex:
            generators.setup_data_model('foo', 'Bar')
        assert str(ex.value) == 'Missing schema for model `Bar`'
        mock_get.assert_called_once_with('Bar')
        mock_schema.assert_called_once_with('foo')

    @patch('ramses.generators.resource_schema')
    @patch('ramses.models.generate_model_cls')
    @patch('ramses.models.get_existing_model')
    def test_setup_data_model_success(self, mock_get, mock_gen, mock_schema):
        mock_get.return_value = None
        mock_schema.return_value = {'field1': 'val1'}
        model = generators.setup_data_model('foo', 'Bar')
        mock_get.assert_called_once_with('Bar')
        mock_schema.assert_called_once_with('foo')
        mock_gen.assert_called_once_with(
            schema={'field1': 'val1'},
            model_name='Bar',
            raml_resource='foo')
        assert model == mock_gen()

    @patch('ramses.generators.setup_data_model')
    def test_handle_model_generation_value_err(self, mock_set):
        mock_set.side_effect = ValueError('strange error')
        with pytest.raises(ValueError) as ex:
            generators.handle_model_generation('foo', '/stories')
        assert str(ex.value) == 'Story: strange error'
        mock_set.assert_called_once_with('foo', 'Story')

    @patch('ramses.generators.setup_data_model')
    def test_handle_model_generation(self, mock_set):
        mock_set.return_value = ('Foo1', True)
        model, auth_model = generators.handle_model_generation(
            'foo', '/stories')
        mock_set.assert_called_once_with('foo', 'Story')
        assert model == 'Foo1'
        assert auth_model

    @patch('ramses.generators.configure_resources')
    def test_generate_server(self, mock_conf):
        parsed_raml = Mock(resources={'/users': 1})
        config = Mock()
        generators.generate_server(parsed_raml, config)
        mock_conf.assert_called_once_with(
            config=config, raml_resources={'/users': 1},
            parsed_raml=parsed_raml)


class TestGenerateModels(object):

    @patch('ramses.generators.is_dynamic_uri')
    def test_no_resources(self, mock_dyn):
        generators.generate_models(config=1, raml_resources={})
        assert not mock_dyn.called

    @patch('ramses.generators.handle_model_generation')
    def test_dynamic_uri(self, mock_handle):
        generators.generate_models(
            config=1, raml_resources={'/{id}': Mock(resources={})})
        assert not mock_handle.called

    @patch('ramses.generators.attr_subresource')
    @patch('ramses.generators.handle_model_generation')
    def test_attr_subresource(self, mock_handle, mock_attr):
        mock_attr.return_value = True
        resource = Mock(resources={})
        generators.generate_models(
            config=1, raml_resources={'/stories': resource})
        assert not mock_handle.called
        mock_attr.assert_called_once_with(resource, 'stories')

    @patch('ramses.generators.attr_subresource')
    @patch('ramses.generators.handle_model_generation')
    def test_non_auth_model(self, mock_handle, mock_attr):
        mock_attr.return_value = False
        mock_handle.return_value = ('Foo', False)
        config = Mock()
        resource = Mock(resources={})
        generators.generate_models(
            config=config, raml_resources={'/stories': resource})
        mock_attr.assert_called_once_with(resource, 'stories')
        mock_handle.assert_called_once_with(resource, 'stories')
        assert config.registry.auth_model != 'Foo'

    @patch('ramses.generators.attr_subresource')
    @patch('ramses.generators.handle_model_generation')
    def test_auth_model(self, mock_handle, mock_attr):
        mock_attr.return_value = False
        mock_handle.return_value = ('Foo', True)
        config = Mock()
        resource = Mock(resources={})
        generators.generate_models(
            config=config, raml_resources={'/stories': resource})
        mock_attr.assert_called_once_with(resource, 'stories')
        mock_handle.assert_called_once_with(resource, 'stories')
        assert config.registry.auth_model == 'Foo'

    @patch('ramses.generators.attr_subresource')
    @patch('ramses.generators.handle_model_generation')
    def test_recursion(self, mock_handle, mock_attr):
        mock_attr.return_value = False
        mock_handle.return_value = ('Foo', False)
        resource1 = Mock(resources={})
        resource2 = Mock(resources={'/users': resource1})
        generators.generate_models(
            config='', raml_resources={'/stories': resource2})
        mock_handle.assert_has_calls([
            call(resource2, 'stories'),
            call(resource1, 'users'),
        ])


class TestConfigureResources(object):

    @patch('ramses.generators.is_restful_uri')
    def test_no_raml_resources(self, mock_rest):
        config = Mock()
        generators.configure_resources(
            config, raml_resources={}, parsed_raml='',
            parent_resource=None)
        assert not config.get_root_resource.called
        assert not mock_rest.called

    def test_no_parent_not_restful_uri(self):
        config = Mock()
        with pytest.raises(ValueError) as ex:
            generators.configure_resources(
                config, raml_resources={'/foo/bar': ''},
                parsed_raml='', parent_resource=None)
        expected = 'Resource URI `/foo/bar` is not RESTful'
        assert str(ex.value) == expected
        config.get_root_resource.assert_called_once_with()

    @patch('ramses.generators.singular_subresource')
    def test_root_dynamic_resource(self, mock_singular):
        config = Mock()
        resource = Mock(resource={})
        with pytest.raises(Exception) as ex:
            generators.configure_resources(
                config, raml_resources={'/{id}': resource},
                parsed_raml='', parent_resource=None)
        assert "Top-level resources can't be dynamic" in str(ex.value)
        assert not mock_singular.called

    @patch('ramses.generators.singular_subresource')
    def test_dynamic_resource(self, mock_singular):
        resource = Mock(resources={})
        parent_resource = Mock(uid=1)
        generators.configure_resources(
            None, raml_resources={'/{id}': resource},
            parsed_raml='', parent_resource=parent_resource)
        assert not mock_singular.called

    @patch('ramses.generators.singular_subresource')
    @patch('ramses.generators.attr_subresource')
    @patch('ramses.models.get_existing_model')
    @patch('ramses.generators.generate_acl')
    @patch('ramses.generators.resource_view_attrs')
    @patch('ramses.generators.generate_rest_view')
    def test_full_run(
            self, generate_view, view_attrs, generate_acl, get_model,
            attr_res, singular_res):
        model_cls = Mock()
        model_cls.pk_field.return_value = 'my_id'
        attr_res.return_value = False
        singular_res.return_value = False
        get_model.return_value = model_cls
        config = Mock()
        resource = Mock(resources={})
        parent_resource = Mock(uid=1)

        generators.configure_resources(
            config, raml_resources={'/stories': resource},
            parsed_raml='foo', parent_resource=parent_resource)

        singular_res.assert_called_once_with(resource, 'stories')
        attr_res.assert_called_once_with(resource, 'stories')
        get_model.assert_called_once_with('Story')
        generate_acl.assert_called_once_with(
            context_cls=model_cls,
            raml_resource=resource,
            parsed_raml='foo'
        )
        view_attrs.assert_called_once_with(resource, False)
        generate_view.assert_called_once_with(
            model_cls=model_cls,
            attrs=view_attrs(),
            attr_view=False,
            singular=False
        )
        parent_resource.add.assert_called_once_with(
            'story', 'stories',
            id_name='stories_my_id',
            factory=generate_acl(),
            view=generate_view()
        )

    @patch('ramses.generators.singular_subresource')
    @patch('ramses.generators.attr_subresource')
    @patch('ramses.models.get_existing_model')
    @patch('ramses.generators.generate_acl')
    @patch('ramses.generators.resource_view_attrs')
    @patch('ramses.generators.generate_rest_view')
    def test_full_run_singular(
            self, generate_view, view_attrs, generate_acl, get_model,
            attr_res, singular_res):
        attr_res.return_value = False
        singular_res.return_value = True
        config = Mock()
        resource = Mock(resources={})
        parent_resource = Mock(uid=1)
        parent_resource.view._model_class.pk_field.return_value = 'other_id'

        generators.configure_resources(
            config, raml_resources={'/stories': resource},
            parsed_raml='foo', parent_resource=parent_resource)

        singular_res.assert_called_once_with(resource, 'stories')
        attr_res.assert_called_once_with(resource, 'stories')
        get_model.assert_called_once_with('Story')
        generate_acl.assert_called_once_with(
            context_cls=parent_resource.view._model_class,
            raml_resource=resource,
            parsed_raml='foo'
        )
        view_attrs.assert_called_once_with(resource, True)
        generate_view.assert_called_once_with(
            model_cls=parent_resource.view._model_class,
            attrs=view_attrs(),
            attr_view=False,
            singular=True
        )
        parent_resource.add.assert_called_once_with(
            'story',
            factory=generate_acl(),
            view=generate_view()
        )
        assert generate_view()._singular_model == get_model()
