import pytest
from mock import Mock, patch, call

from .fixtures import engine_mock


class TestHelperFunctions(object):

    @patch('ramses.models.engine')
    def test_get_existing_model_not_found(self, mock_eng):
        from ramses import models
        mock_eng.get_document_cls.side_effect = ValueError
        model_cls = models.get_existing_model('Foo')
        assert model_cls is None
        mock_eng.get_document_cls.assert_called_once_with('Foo')

    @patch('ramses.models.engine')
    def test_get_existing_model_found(self, mock_eng):
        from ramses import models
        mock_eng.get_document_cls.return_value = 1
        model_cls = models.get_existing_model('Foo')
        assert model_cls == 1
        mock_eng.get_document_cls.assert_called_once_with('Foo')

    @patch('ramses.models.find_dynamic_resource')
    @patch('ramses.models.get_existing_model')
    def test_prepare_relationship_model_exists(self, mock_get, mock_find):
        from ramses import models
        models.prepare_relationship('foobar', 'Story', 'raml_resource')
        mock_get.assert_called_once_with('Story')
        assert not mock_find.called

    @patch('ramses.models.find_dynamic_resource')
    @patch('ramses.models.get_existing_model')
    def test_prepare_relationship_no_subresource(self, mock_get, mock_find):
        from ramses import models
        mock_get.return_value = None
        mock_find.return_value = Mock(resources={'/foo': 'bar'})
        with pytest.raises(ValueError) as ex:
            models.prepare_relationship('foobar', 'Story', 'raml_resource')
        expected = ('Model `Story` used in relationship `foobar` '
                    'is not defined')
        assert str(ex.value) == expected
        mock_get.assert_called_once_with('Story')
        mock_find.assert_called_once_with('raml_resource')

    @patch('ramses.generators.setup_data_model')
    @patch('ramses.models.find_dynamic_resource')
    @patch('ramses.models.get_existing_model')
    def test_prepare_relationship(self, mock_get, mock_find, mock_setup):
        from ramses import models
        mock_get.return_value = None
        mock_find.return_value = Mock(
            resources={'/foobar': 'stories_resource'})
        models.prepare_relationship('foobar', 'Story', 'raml_resource')
        mock_get.assert_called_once_with('Story')
        mock_find.assert_called_once_with('raml_resource')
        mock_setup.assert_called_once_with('stories_resource', 'Story')


@patch('ramses.models.registry')
@pytest.mark.usefixtures('engine_mock')
class TestGenerateModelCls(object):

    def _test_schema(self):
        return {
            'properties': {},
            'auth_model': False,
            'public_fields': ['public_field1'],
            'auth_fields': ['auth_field1'],
            'nested_relationships': ['nested_field1']
        }

    def test_simple_case(self, mock_reg):
        from ramses import models
        schema = self._test_schema()
        schema['properties']['progress'] = {
            "required": True,
            "type": "float",
            "args": {
                "default": 0,
                "before_validation": ["zoo"],
                "after_validation": ["foo"]
            }
        }
        mock_reg.get.return_value = 1
        mock_reg.mget.return_value = {'foo': 'bar'}
        model_cls, auth_model = models.generate_model_cls(
            schema=schema, model_name='Story', raml_resource=None)
        assert not auth_model
        assert model_cls.__name__ == 'Story'
        assert hasattr(model_cls, 'progress')
        assert model_cls.__tablename__ == 'story'
        assert model_cls._public_fields == ['public_field1']
        assert model_cls._auth_fields == ['auth_field1']
        assert model_cls._nested_relationships == ['nested_field1']
        assert model_cls.foo == 'bar'
        assert issubclass(model_cls, models.engine.ESBaseDocument)
        assert not issubclass(model_cls, models.AuthModelDefaultMixin)
        models.engine.FloatField.assert_called_once_with(
            default=0, required=True, before_validation=[1],
            after_validation=[1])
        mock_reg.get.assert_has_calls([call('zoo'), call('foo')])
        mock_reg.mget.assert_called_once_with('Story')

    def test_auth_model(self, mock_reg):
        from ramses import models
        schema = self._test_schema()
        schema['properties']['progress'] = {}
        schema['auth_model'] = True
        mock_reg.mget.return_value = {'foo': 'bar'}

        model_cls, auth_model = models.generate_model_cls(
            schema=schema, model_name='Story', raml_resource=None)
        assert auth_model
        assert issubclass(model_cls, models.AuthModelDefaultMixin)

    def test_db_based_model(self, mock_reg):
        from ramses import models
        schema = self._test_schema()
        schema['properties']['progress'] = {}
        mock_reg.mget.return_value = {'foo': 'bar'}

        model_cls, auth_model = models.generate_model_cls(
            schema=schema, model_name='Story', raml_resource=None,
            es_based=False)
        assert issubclass(model_cls, models.engine.BaseDocument)
        assert not issubclass(model_cls, models.engine.ESBaseDocument)
        assert not issubclass(model_cls, models.AuthModelDefaultMixin)

    def test_unknown_field_type(self, mock_reg):
        from ramses import models
        schema = self._test_schema()
        schema['properties']['progress'] = {'type': 'foobar'}
        mock_reg.mget.return_value = {'foo': 'bar'}

        with pytest.raises(ValueError) as ex:
            models.generate_model_cls(
                schema=schema, model_name='Story', raml_resource=None)
        assert str(ex.value) == 'Unknown type: foobar'

    @patch('ramses.models.prepare_relationship')
    def test_relationship_field(self, mock_prep, mock_reg):
        from ramses import models
        schema = self._test_schema()
        schema['properties']['progress'] = {
            'type': 'relationship',
            'args': {'document': 'FooBar'}
        }
        mock_reg.mget.return_value = {'foo': 'bar'}
        models.generate_model_cls(
            schema=schema, model_name='Story', raml_resource=1)
        mock_prep.assert_called_once_with('progress', 'FooBar', 1)

    def test_foreignkey_field(self, mock_reg):
        from ramses import models
        schema = self._test_schema()
        schema['properties']['progress'] = {
            "type": "foreign_key",
            "args": {
                "ref_column_type": "string"
            }
        }
        mock_reg.mget.return_value = {'foo': 'bar'}
        models.generate_model_cls(
            schema=schema, model_name='Story', raml_resource=1)
        models.engine.ForeignKeyField.assert_called_once_with(
            required=False, ref_column_type=models.engine.StringField,
            before_validation=[], after_validation=[])

    def test_list_field(self, mock_reg):
        from ramses import models
        schema = self._test_schema()
        schema['properties']['progress'] = {
            "type": "list",
            "args": {
                "item_type": "integer"
            }
        }
        mock_reg.mget.return_value = {'foo': 'bar'}
        models.generate_model_cls(
            schema=schema, model_name='Story', raml_resource=1)
        models.engine.ListField.assert_called_once_with(
            required=False, item_type=models.engine.IntegerField,
            before_validation=[], after_validation=[])

    def test_duplicate_field_name(self, mock_reg):
        from ramses import models
        schema = self._test_schema()
        schema['properties']['_public_fields'] = {'type': 'interval'}
        mock_reg.mget.return_value = {'foo': 'bar'}
        models.generate_model_cls(
            schema=schema, model_name='Story', raml_resource=1)
        assert not models.engine.IntervalField.called
