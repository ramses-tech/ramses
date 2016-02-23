import pytest
from mock import Mock, patch, call

from ramses import generators
from .fixtures import engine_mock, config_mock


class TestHelperFunctions(object):
    @patch.object(generators, 'get_static_parent')
    def test_get_nefertari_parent_resource_no_parent(self, mock_get):
        mock_get.return_value = None
        assert generators._get_nefertari_parent_resource(1, 2, 3) == 3
        mock_get.assert_called_once_with(1)

    @patch.object(generators, 'get_static_parent')
    def test_get_nefertari_parent_resource_parent_not_defined(
            self, mock_get):
        mock_get.return_value = Mock(path='foo')
        assert generators._get_nefertari_parent_resource(
            1, {}, 3) == 3
        mock_get.assert_called_once_with(1)

    @patch.object(generators, 'get_static_parent')
    def test_get_nefertari_parent_resource_parent_defined(
            self, mock_get):
        mock_get.return_value = Mock(path='foo')
        assert generators._get_nefertari_parent_resource(
            1, {'foo': 'bar'}, 3) == 'bar'
        mock_get.assert_called_once_with(1)

    @patch.object(generators, 'generate_resource')
    def test_generate_server_no_resources(self, mock_gen):
        generators.generate_server(Mock(resources=None), 'foo')
        assert not mock_gen.called

    @patch.object(generators, '_get_nefertari_parent_resource')
    @patch.object(generators, 'generate_resource')
    def test_generate_server_resources_generated(
            self, mock_gen, mock_get):
        config = Mock()
        resources = [
            Mock(path='/foo'),
            Mock(path='/bar'),
        ]
        generators.generate_server(Mock(resources=resources), config)
        assert mock_get.call_count == 2
        mock_gen.assert_has_calls([
            call(config, resources[0], mock_get()),
            call(config, resources[1], mock_get()),
        ])

    @patch.object(generators, '_get_nefertari_parent_resource')
    @patch.object(generators, 'generate_resource')
    def test_generate_server_call_per_path(
            self, mock_gen, mock_get):
        config = Mock()
        resources = [
            Mock(path='/foo'),
            Mock(path='/foo'),
        ]
        generators.generate_server(Mock(resources=resources), config)
        assert mock_get.call_count == 1
        mock_gen.assert_called_once_with(config, resources[0], mock_get())


@pytest.mark.usefixtures('engine_mock')
class TestGenerateModels(object):

    @patch('ramses.generators.is_dynamic_uri')
    def test_no_resources(self, mock_dyn):
        generators.generate_models(config=1, raml_resources=[])
        assert not mock_dyn.called

    @patch('ramses.models.handle_model_generation')
    def test_dynamic_uri(self, mock_handle):
        generators.generate_models(
            config=1, raml_resources=[Mock(path='/{id}')])
        assert not mock_handle.called

    @patch('ramses.models.handle_model_generation')
    def test_no_post_resources(self, mock_handle):
        generators.generate_models(config=1, raml_resources=[
            Mock(path='/stories', method='get'),
            Mock(path='/stories', method='options'),
            Mock(path='/stories', method='patch'),
        ])
        assert not mock_handle.called

    @patch('ramses.generators.attr_subresource')
    @patch('ramses.models.handle_model_generation')
    def test_attr_subresource(self, mock_handle, mock_attr):
        mock_attr.return_value = True
        resource = Mock(path='/stories', method='POST')
        generators.generate_models(config=1, raml_resources=[resource])
        assert not mock_handle.called
        mock_attr.assert_called_once_with(resource, 'stories')

    @patch('ramses.generators.attr_subresource')
    @patch('ramses.models.handle_model_generation')
    def test_non_auth_model(self, mock_handle, mock_attr):
        mock_attr.return_value = False
        mock_handle.return_value = ('Foo', False)
        config = Mock()
        resource = Mock(path='/stories', method='POST')
        generators.generate_models(
            config=config, raml_resources=[resource])
        mock_attr.assert_called_once_with(resource, 'stories')
        mock_handle.assert_called_once_with(config, resource)
        assert config.registry.auth_model != 'Foo'

    @patch('ramses.generators.attr_subresource')
    @patch('ramses.models.handle_model_generation')
    def test_auth_model(self, mock_handle, mock_attr):
        mock_attr.return_value = False
        mock_handle.return_value = ('Foo', True)
        config = Mock()
        resource = Mock(path='/stories', method='POST')
        generators.generate_models(
            config=config, raml_resources=[resource])
        mock_attr.assert_called_once_with(resource, 'stories')
        mock_handle.assert_called_once_with(config, resource)
        assert config.registry.auth_model == 'Foo'


class TestGenerateResource(object):
    def test_dynamic_root_parent(self):
        raml_resource = Mock(path='/foobar/{id}')
        parent_resource = Mock(is_root=True)
        config = config_mock()
        with pytest.raises(Exception) as ex:
            generators.generate_resource(
                config, raml_resource, parent_resource)

        expected = ("Top-level resources can't be dynamic and must "
                    "represent collections instead")
        assert str(ex.value) == expected

    def test_dynamic_not_root_parent(self):
        raml_resource = Mock(path='/foobar/{id}')
        parent_resource = Mock(is_root=False)
        config = config_mock()
        new_resource = generators.generate_resource(
            config, raml_resource, parent_resource)
        assert new_resource is None

    @patch('ramses.generators.dynamic_part_name')
    @patch('ramses.generators.singular_subresource')
    @patch('ramses.generators.attr_subresource')
    @patch('ramses.models.get_existing_model')
    @patch('ramses.generators.generate_acl')
    @patch('ramses.generators.resource_view_attrs')
    @patch('ramses.generators.generate_rest_view')
    def test_full_run(
            self, generate_view, view_attrs, generate_acl, get_model,
            attr_res, singular_res, mock_dyn):
        mock_dyn.return_value = 'fooid'
        model_cls = Mock()
        model_cls.pk_field.return_value = 'my_id'
        attr_res.return_value = False
        singular_res.return_value = False
        get_model.return_value = model_cls
        raml_resource = Mock(path='/stories')
        parent_resource = Mock(is_root=False, uid=1)
        config = config_mock()

        res = generators.generate_resource(
            config, raml_resource, parent_resource)
        get_model.assert_called_once_with('Story')
        generate_acl.assert_called_once_with(
            config, model_cls=model_cls, raml_resource=raml_resource)
        mock_dyn.assert_called_once_with(
            raml_resource=raml_resource,
            route_name='stories', pk_field='my_id')
        view_attrs.assert_called_once_with(raml_resource, False)
        generate_view.assert_called_once_with(
            config,
            model_cls=model_cls,
            attrs=view_attrs(),
            attr_view=False,
            singular=False
        )
        parent_resource.add.assert_called_once_with(
            'story', 'stories',
            id_name='fooid',
            factory=generate_acl(),
            view=generate_view()
        )
        assert res == parent_resource.add()

    @patch('ramses.generators.dynamic_part_name')
    @patch('ramses.generators.singular_subresource')
    @patch('ramses.generators.attr_subresource')
    @patch('ramses.models.get_existing_model')
    @patch('ramses.generators.generate_acl')
    @patch('ramses.generators.resource_view_attrs')
    @patch('ramses.generators.generate_rest_view')
    def test_full_run_singular(
            self, generate_view, view_attrs, generate_acl, get_model,
            attr_res, singular_res, mock_dyn):
        mock_dyn.return_value = 'fooid'
        model_cls = Mock()
        model_cls.pk_field.return_value = 'my_id'
        attr_res.return_value = False
        singular_res.return_value = True
        get_model.return_value = model_cls
        raml_resource = Mock(path='/stories')
        parent_resource = Mock(is_root=False, uid=1)
        parent_resource.view.Model.pk_field.return_value = 'other_id'

        config = config_mock()
        res = generators.generate_resource(
            config, raml_resource, parent_resource)
        get_model.assert_called_once_with('Story')
        generate_acl.assert_called_once_with(
            config, model_cls=parent_resource.view.Model,
            raml_resource=raml_resource)
        assert not mock_dyn.called
        view_attrs.assert_called_once_with(raml_resource, True)
        generate_view.assert_called_once_with(
            config,
            model_cls=parent_resource.view.Model,
            attrs=view_attrs(),
            attr_view=False,
            singular=True
        )
        parent_resource.add.assert_called_once_with(
            'story',
            factory=generate_acl(),
            view=generate_view()
        )
        assert res == parent_resource.add()
