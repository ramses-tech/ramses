import pytest
from mock import Mock, patch, call

from ramses import generators
from .fixtures import engine_mock


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
        mock_handle.assert_called_once_with(resource, 'stories')
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
        mock_handle.assert_called_once_with(resource, 'stories')
        assert config.registry.auth_model == 'Foo'


# @pytest.mark.usefixtures('engine_mock')
# class TestGenerateServer(object):




# @pytest.mark.usefixtures('engine_mock')
# class TestConfigureResources(object):

#     @patch('ramses.generators.is_restful_uri')
#     def test_no_raml_resources(self, mock_rest):
#         config = Mock()
#         generators.configure_resources(
#             config, raml_resources={}, parsed_raml='',
#             parent_resource=None)
#         assert not config.get_root_resource.called
#         assert not mock_rest.called

#     def test_no_parent_not_restful_uri(self):
#         config = Mock()
#         with pytest.raises(ValueError) as ex:
#             generators.configure_resources(
#                 config, raml_resources={'/foo/bar': ''},
#                 parsed_raml='', parent_resource=None)
#         expected = 'Resource URI `/foo/bar` is not RESTful'
#         assert str(ex.value) == expected
#         config.get_root_resource.assert_called_once_with()

#     @patch('ramses.generators.singular_subresource')
#     def test_root_dynamic_resource(self, mock_singular):
#         config = Mock()
#         resource = Mock(resource={})
#         with pytest.raises(Exception) as ex:
#             generators.configure_resources(
#                 config, raml_resources={'/{id}': resource},
#                 parsed_raml='', parent_resource=None)
#         assert "Top-level resources can't be dynamic" in str(ex.value)
#         assert not mock_singular.called

#     @patch('ramses.generators.singular_subresource')
#     def test_dynamic_resource(self, mock_singular):
#         resource = Mock(resources={})
#         parent_resource = Mock(uid=1)
#         generators.configure_resources(
#             None, raml_resources={'/{id}': resource},
#             parsed_raml='', parent_resource=parent_resource)
#         assert not mock_singular.called

#     @patch('ramses.generators.singular_subresource')
#     @patch('ramses.generators.attr_subresource')
#     @patch('ramses.models.get_existing_model')
#     @patch('ramses.generators.generate_acl')
#     @patch('ramses.generators.resource_view_attrs')
#     @patch('ramses.generators.generate_rest_view')
#     def test_full_run(
#             self, generate_view, view_attrs, generate_acl, get_model,
#             attr_res, singular_res):
#         model_cls = Mock()
#         model_cls.pk_field.return_value = 'my_id'
#         attr_res.return_value = False
#         singular_res.return_value = False
#         get_model.return_value = model_cls
#         config = Mock()
#         resource = Mock(resources={})
#         parent_resource = Mock(uid=1)

#         generators.configure_resources(
#             config, raml_resources={'/stories': resource},
#             parsed_raml='foo', parent_resource=parent_resource)

#         singular_res.assert_called_once_with(resource, 'stories')
#         attr_res.assert_called_once_with(resource, 'stories')
#         get_model.assert_called_once_with('Story')
#         generate_acl.assert_called_once_with(
#             context_cls=model_cls,
#             raml_resource=resource,
#             parsed_raml='foo'
#         )
#         view_attrs.assert_called_once_with(resource, False)
#         generate_view.assert_called_once_with(
#             model_cls=model_cls,
#             attrs=view_attrs(),
#             attr_view=False,
#             singular=False
#         )
#         parent_resource.add.assert_called_once_with(
#             'story', 'stories',
#             id_name='stories_my_id',
#             factory=generate_acl(),
#             view=generate_view()
#         )

#     @patch('ramses.generators.singular_subresource')
#     @patch('ramses.generators.attr_subresource')
#     @patch('ramses.models.get_existing_model')
#     @patch('ramses.generators.generate_acl')
#     @patch('ramses.generators.resource_view_attrs')
#     @patch('ramses.generators.generate_rest_view')
#     def test_full_run_singular(
#             self, generate_view, view_attrs, generate_acl, get_model,
#             attr_res, singular_res):
#         attr_res.return_value = False
#         singular_res.return_value = True
#         config = Mock()
#         resource = Mock(resources={})
#         parent_resource = Mock(uid=1)
#         parent_resource.view.Model.pk_field.return_value = 'other_id'

#         generators.configure_resources(
#             config, raml_resources={'/stories': resource},
#             parsed_raml='foo', parent_resource=parent_resource)

#         singular_res.assert_called_once_with(resource, 'stories')
#         attr_res.assert_called_once_with(resource, 'stories')
#         get_model.assert_called_once_with('Story')
#         generate_acl.assert_called_once_with(
#             context_cls=parent_resource.view.Model,
#             raml_resource=resource,
#             parsed_raml='foo'
#         )
#         view_attrs.assert_called_once_with(resource, True)
#         generate_view.assert_called_once_with(
#             model_cls=parent_resource.view.Model,
#             attrs=view_attrs(),
#             attr_view=False,
#             singular=True
#         )
#         parent_resource.add.assert_called_once_with(
#             'story',
#             factory=generate_acl(),
#             view=generate_view()
#         )
#         assert generate_view()._singular_model == get_model()
