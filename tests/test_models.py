import pytest
from mock import Mock, patch, call

from .fixtures import engine_mock, config_mock, guards_engine_mock


@pytest.mark.usefixtures('engine_mock')
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

    @patch('ramses.models.setup_data_model')
    @patch('ramses.models.get_existing_model')
    def test_prepare_relationship_model_exists(self, mock_get, mock_set):
        from ramses import models
        config = Mock()
        models.prepare_relationship(
            config, 'Story', 'raml_resource')
        mock_get.assert_called_once_with('Story')
        assert not mock_set.called

    @patch('ramses.models.get_existing_model')
    def test_prepare_relationship_resource_not_found(self, mock_get):
        from ramses import models
        config = Mock()
        resource = Mock(root=Mock(resources=[
            Mock(method='get', path='/stories'),
            Mock(method='options', path='/stories'),
            Mock(method='post', path='/items'),
        ]))
        mock_get.return_value = None
        with pytest.raises(ValueError) as ex:
            models.prepare_relationship(config, 'Story', resource)
        expected = ('Model `Story` used in relationship '
                    'is not defined')
        assert str(ex.value) == expected

    @patch('ramses.models.setup_data_model')
    @patch('ramses.models.get_existing_model')
    def test_prepare_relationship_resource_found(
            self, mock_get, mock_set):
        from ramses import models
        config = Mock()
        matching_res = Mock(method='post', path='/stories')
        resource = Mock(root=Mock(resources=[
            matching_res,
            Mock(method='options', path='/stories'),
            Mock(method='post', path='/items'),
        ]))
        mock_get.return_value = None
        config = config_mock()
        models.prepare_relationship(config, 'Story', resource)
        mock_set.assert_called_once_with(config, matching_res, 'Story')

    @patch('ramses.models.resource_schema')
    @patch('ramses.models.get_existing_model')
    def test_setup_data_model_existing_model(self, mock_get, mock_schema):
        from ramses import models
        config = Mock()
        mock_get.return_value = 1
        mock_schema.return_value = {"foo": "bar"}
        model, auth_model = models.setup_data_model(config, 'foo', 'Bar')
        assert not auth_model
        assert model == 1
        mock_get.assert_called_once_with('Bar')

    @patch('ramses.models.resource_schema')
    @patch('ramses.models.get_existing_model')
    def test_setup_data_model_existing_auth_model(self, mock_get, mock_schema):
        from ramses import models
        config = Mock()
        mock_get.return_value = 1
        mock_schema.return_value = {"_auth_model": True}
        model, auth_model = models.setup_data_model(config, 'foo', 'Bar')
        assert auth_model
        assert model == 1
        mock_get.assert_called_once_with('Bar')

    @patch('ramses.models.resource_schema')
    @patch('ramses.models.get_existing_model')
    def test_setup_data_model_no_schema(self, mock_get, mock_schema):
        from ramses import models
        config = Mock()
        mock_get.return_value = None
        mock_schema.return_value = None
        with pytest.raises(Exception) as ex:
            models.setup_data_model(config, 'foo', 'Bar')
        assert str(ex.value) == 'Missing schema for model `Bar`'
        mock_get.assert_called_once_with('Bar')
        mock_schema.assert_called_once_with('foo')

    @patch('ramses.models.resource_schema')
    @patch('ramses.models.generate_model_cls')
    @patch('ramses.models.get_existing_model')
    def test_setup_data_model_success(self, mock_get, mock_gen, mock_schema):
        from ramses import models
        mock_get.return_value = None
        mock_schema.return_value = {'field1': 'val1'}
        config = config_mock()
        model = models.setup_data_model(config, 'foo', 'Bar')
        mock_get.assert_called_once_with('Bar')
        mock_schema.assert_called_once_with('foo')
        mock_gen.assert_called_once_with(
            config,
            schema={'field1': 'val1'},
            model_name='Bar',
            raml_resource='foo')
        assert model == mock_gen()

    @patch('ramses.models.setup_data_model')
    def test_handle_model_generation_value_err(self, mock_set):
        from ramses import models
        config = Mock()
        mock_set.side_effect = ValueError('strange error')
        config = config_mock()
        with pytest.raises(ValueError) as ex:
            raml_resource = Mock(path='/stories')
            models.handle_model_generation(config, raml_resource)
        assert str(ex.value) == 'Story: strange error'
        mock_set.assert_called_once_with(config, raml_resource, 'Story')

    @patch('ramses.models.setup_data_model')
    def test_handle_model_generation(self, mock_set):
        from ramses import models
        config = Mock()
        mock_set.return_value = ('Foo1', True)
        config = config_mock()
        raml_resource = Mock(path='/stories')
        model, auth_model = models.handle_model_generation(
            config, raml_resource)
        mock_set.assert_called_once_with(config, raml_resource, 'Story')
        assert model == 'Foo1'
        assert auth_model


@patch('ramses.models.setup_fields_processors')
@patch('ramses.models.setup_model_event_subscribers')
@patch('ramses.models.registry')
@pytest.mark.usefixtures('engine_mock')
class TestGenerateModelCls(object):

    def _test_schema(self):
        return {
            'properties': {},
            '_auth_model': False,
            '_public_fields': ['public_field1'],
            '_auth_fields': ['auth_field1'],
            '_hidden_fields': ['hidden_field1'],
            '_nested_relationships': ['nested_field1'],
            '_nesting_depth': 3
        }

    @patch('ramses.models.resolve_to_callable')
    def test_simple_case(
            self, mock_res, mock_reg, mock_subscribers, mock_proc):
        from nefertari.authentication.models import AuthModelMethodsMixin
        from ramses import models
        config = config_mock()
        models.engine.FloatField.reset_mock()
        schema = self._test_schema()
        schema['properties']['progress'] = {
            "_db_settings": {
                "type": "float",
                "required": True,
                "default": 0,
            }
        }
        mock_reg.mget.return_value = {'foo': 'bar'}
        model_cls, auth_model = models.generate_model_cls(
            config, schema=schema, model_name='Story',
            raml_resource=None)
        assert not auth_model
        assert model_cls.__name__ == 'Story'
        assert hasattr(model_cls, 'progress')
        assert model_cls.__tablename__ == 'story'
        assert model_cls._public_fields == ['public_field1']
        assert model_cls._nesting_depth == 3
        assert model_cls._auth_fields == ['auth_field1']
        assert model_cls._hidden_fields == ['hidden_field1']
        assert model_cls._nested_relationships == ['nested_field1']
        assert model_cls.foo == 'bar'
        assert issubclass(model_cls, models.engine.ESBaseDocument)
        assert not issubclass(model_cls, AuthModelMethodsMixin)
        models.engine.FloatField.assert_called_once_with(
            default=0, required=True)
        mock_reg.mget.assert_called_once_with('Story')
        mock_subscribers.assert_called_once_with(
            config, model_cls, schema)
        mock_proc.assert_called_once_with(
            config, model_cls, schema)

    @patch('ramses.models.resolve_to_callable')
    def test_callable_default(
            self, mock_res, mock_reg, mock_subscribers, mock_proc):
        from ramses import models
        config = config_mock()
        models.engine.FloatField.reset_mock()
        schema = self._test_schema()
        schema['properties']['progress'] = {
            "_db_settings": {
                "type": "float",
                "default": "{{foobar}}",
            }
        }
        mock_res.return_value = 1
        model_cls, auth_model = models.generate_model_cls(
            config, schema=schema, model_name='Story',
            raml_resource=None)
        models.engine.FloatField.assert_called_with(
            default=1, required=False)
        mock_res.assert_called_once_with('{{foobar}}')

    def test_auth_model(self, mock_reg, mock_subscribers, mock_proc):
        from nefertari.authentication.models import AuthModelMethodsMixin
        from ramses import models
        config = config_mock()
        schema = self._test_schema()
        schema['properties']['progress'] = {'_db_settings': {}}
        schema['_auth_model'] = True
        mock_reg.mget.return_value = {'foo': 'bar'}

        model_cls, auth_model = models.generate_model_cls(
            config, schema=schema, model_name='Story',
            raml_resource=None)
        assert auth_model
        assert issubclass(model_cls, AuthModelMethodsMixin)

    def test_database_acls_option(
            self, mock_reg, mock_subscribers, mock_proc,
            guards_engine_mock):
        from ramses import models
        schema = self._test_schema()
        schema['properties']['progress'] = {'_db_settings': {}}
        schema['_auth_model'] = True
        mock_reg.mget.return_value = {'foo': 'bar'}
        config = config_mock()

        config.registry.database_acls = False
        model_cls, auth_model = models.generate_model_cls(
            config, schema=schema, model_name='Story1',
            raml_resource=None)
        assert not issubclass(model_cls, guards_engine_mock.DocumentACLMixin)

        config.registry.database_acls = True
        model_cls, auth_model = models.generate_model_cls(
            config, schema=schema, model_name='Story2',
            raml_resource=None)
        assert issubclass(model_cls, guards_engine_mock.DocumentACLMixin)

    def test_db_based_model(self, mock_reg, mock_subscribers, mock_proc):
        from nefertari.authentication.models import AuthModelMethodsMixin
        from ramses import models
        config = config_mock()
        schema = self._test_schema()
        schema['properties']['progress'] = {'_db_settings': {}}
        mock_reg.mget.return_value = {'foo': 'bar'}

        model_cls, auth_model = models.generate_model_cls(
            config, schema=schema, model_name='Story',
            raml_resource=None, es_based=False)
        assert issubclass(model_cls, models.engine.BaseDocument)
        assert not issubclass(model_cls, models.engine.ESBaseDocument)
        assert not issubclass(model_cls, AuthModelMethodsMixin)

    def test_no_db_settings(self, mock_reg, mock_subscribers, mock_proc):
        from ramses import models
        config = config_mock()
        schema = self._test_schema()
        schema['properties']['progress'] = {'type': 'pickle'}
        mock_reg.mget.return_value = {'foo': 'bar'}

        model_cls, auth_model = models.generate_model_cls(
            config, schema=schema, model_name='Story',
            raml_resource=None, es_based=False)
        assert not models.engine.PickleField.called

    def test_unknown_field_type(
            self, mock_reg, mock_subscribers, mock_proc):
        from ramses import models
        config = config_mock()
        schema = self._test_schema()
        schema['properties']['progress'] = {
            '_db_settings': {'type': 'foobar'}}
        mock_reg.mget.return_value = {'foo': 'bar'}

        with pytest.raises(ValueError) as ex:
            models.generate_model_cls(
                config, schema=schema, model_name='Story',
                raml_resource=None)
        assert str(ex.value) == 'Unknown type: foobar'

    @patch('ramses.models.prepare_relationship')
    def test_relationship_field(
            self, mock_prep, mock_reg, mock_subscribers, mock_proc):
        from ramses import models
        config = Mock()
        schema = self._test_schema()
        schema['properties']['progress'] = {
            '_db_settings': {
                'type': 'relationship',
                'document': 'FooBar',
            }
        }
        mock_reg.mget.return_value = {'foo': 'bar'}
        config = config_mock()
        models.generate_model_cls(
            config, schema=schema, model_name='Story',
            raml_resource=1)
        mock_prep.assert_called_once_with(
            config, 'FooBar', 1)

    def test_foreignkey_field(
            self, mock_reg, mock_subscribers, mock_proc):
        from ramses import models
        config = config_mock()
        schema = self._test_schema()
        schema['properties']['progress'] = {
            "_db_settings": {
                "type": "foreign_key",
                "ref_column_type": "string"
            }
        }
        mock_reg.mget.return_value = {'foo': 'bar'}
        models.generate_model_cls(
            config, schema=schema, model_name='Story',
            raml_resource=1)
        models.engine.ForeignKeyField.assert_called_once_with(
            required=False, ref_column_type=models.engine.StringField)

    def test_list_field(self, mock_reg, mock_subscribers, mock_proc):
        from ramses import models
        config = config_mock()
        schema = self._test_schema()
        schema['properties']['progress'] = {
            "_db_settings": {
                "type": "list",
                "item_type": "integer"
            }
        }
        mock_reg.mget.return_value = {'foo': 'bar'}
        models.generate_model_cls(
            config, schema=schema, model_name='Story',
            raml_resource=1)
        models.engine.ListField.assert_called_once_with(
            required=False, item_type=models.engine.IntegerField)

    def test_duplicate_field_name(
            self, mock_reg, mock_subscribers, mock_proc):
        from ramses import models
        config = config_mock()
        schema = self._test_schema()
        schema['properties']['_public_fields'] = {
            '_db_settings': {'type': 'interval'}}
        mock_reg.mget.return_value = {'foo': 'bar'}
        models.generate_model_cls(
            config, schema=schema, model_name='Story',
            raml_resource=1)
        assert not models.engine.IntervalField.called


class TestSubscribersSetup(object):

    @patch('ramses.models.resolve_to_callable')
    @patch('ramses.models.get_events_map')
    def test_setup_model_event_subscribers(self, mock_get, mock_resolve):
        from ramses import models
        mock_get.return_value = {'before': {'index': 'eventcls'}}
        mock_resolve.return_value = 1
        config = Mock()
        model_cls = 'mymodel'
        schema = {
            '_event_handlers': {
                'before_index': ['func1', 'func2']
            }
        }
        models.setup_model_event_subscribers(config, model_cls, schema)
        mock_get.assert_called_once_with()
        mock_resolve.assert_has_calls([call('func1'), call('func2')])
        config.subscribe_to_events.assert_has_calls([
            call(mock_resolve(), ['eventcls'], model='mymodel'),
            call(mock_resolve(), ['eventcls'], model='mymodel'),
        ])

    @patch('ramses.models.resolve_to_callable')
    @patch('ramses.models.engine')
    def test_setup_fields_processors(self, mock_eng, mock_resolve):
        from ramses import models
        config = Mock()
        schema = {
            'properties': {
                'stories': {
                    "_db_settings": {
                        "type": "relationship",
                        "document": "Story",
                        "backref_name": "owner",
                    },
                    "_processors": ["lowercase"],
                    "_backref_processors": ["backref_lowercase"]
                }
            }
        }

        models.setup_fields_processors(config, 'mymodel', schema)

        mock_resolve.assert_has_calls([
            call('lowercase'), call('backref_lowercase')])
        mock_eng.get_document_cls.assert_called_once_with('Story')
        config.add_field_processors.assert_has_calls([
            call([mock_resolve()], model='mymodel', field='stories'),
            call([mock_resolve()], model=mock_eng.get_document_cls(),
                 field='owner'),
        ])

    @patch('ramses.models.resolve_to_callable')
    @patch('ramses.models.engine')
    def test_setup_fields_processors_backref_not_rel(
            self, mock_eng, mock_resolve):
        from ramses import models
        config = Mock()
        schema = {
            'properties': {
                'stories': {
                    "_db_settings": {
                        "type": "wqeqweqwe",
                        "document": "Story",
                        "backref_name": "owner",
                    },
                    "_backref_processors": ["backref_lowercase"]
                }
            }
        }
        models.setup_fields_processors(config, 'mymodel', schema)
        assert not config.add_field_processors.called

    @patch('ramses.models.resolve_to_callable')
    @patch('ramses.models.engine')
    def test_setup_fields_processors_backref_no_doc(
            self, mock_eng, mock_resolve):
        from ramses import models
        config = Mock()
        schema = {
            'properties': {
                'stories': {
                    "_db_settings": {
                        "type": "relationship",
                        "backref_name": "owner",
                    },
                    "_backref_processors": ["backref_lowercase"]
                }
            }
        }
        models.setup_fields_processors(config, 'mymodel', schema)
        assert not config.add_field_processors.called

    @patch('ramses.models.resolve_to_callable')
    @patch('ramses.models.engine')
    def test_setup_fields_processors_backref_no_backname(
            self, mock_eng, mock_resolve):
        from ramses import models
        config = Mock()
        schema = {
            'properties': {
                'stories': {
                    "_db_settings": {
                        "type": "relationship",
                        "document": "Story",
                    },
                    "_backref_processors": ["backref_lowercase"]
                }
            }
        }
        models.setup_fields_processors(config, 'mymodel', schema)
        assert not config.add_field_processors.called
