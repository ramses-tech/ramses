import pytest
from mock import Mock, patch

from nefertari.json_httpexceptions import (
    JHTTPNotFound, JHTTPMethodNotAllowed)
from nefertari.view import BaseView

from ramses import views
from .fixtures import config_mock, guards_engine_mock


class ViewTestBase(object):
    view_cls = None
    view_kwargs = dict(
        context={},
        _query_params={'foo': 'bar'},
        _json_params={'foo2': 'bar2'},
    )
    request_kwargs = dict(
        method='GET',
        accept=[''],
    )

    def _test_view(self):
        class View(self.view_cls, BaseView):
            _json_encoder = 'foo'

        request = Mock(**self.request_kwargs)
        return View(request=request, **self.view_kwargs)


class TestSetObjectACLMixin(object):
    def test_set_object_acl(self, guards_engine_mock):
        view = views.SetObjectACLMixin()
        view.request = 'foo'
        view._factory = Mock()
        obj = Mock(_acl=None)
        view.set_object_acl(obj)
        view._factory.assert_called_once_with(view.request)
        view._factory().generate_item_acl.assert_called_once_with(obj)
        field = guards_engine_mock.ACLField
        field.stringify_acl.assert_called_once_with(
            view._factory().generate_item_acl())
        assert obj._acl == field.stringify_acl()


class TestBaseView(ViewTestBase):
    view_cls = views.BaseView

    def test_init(self):
        view = self._test_view()
        assert view._query_params['_limit'] == 20

    def test_clean_id_name(self):
        view = self._test_view()
        view._resource = Mock(id_name='foo')
        assert view.clean_id_name == 'foo'
        view._resource = Mock(id_name='foo_bar')
        assert view.clean_id_name == 'bar'

    def test_resolve_kw(self):
        view = self._test_view()
        kwargs = {'foo_bar_qoo': 1, 'arg_val': 4, 'q': 3}
        assert view.resolve_kw(kwargs) == {'bar_qoo': 1, 'val': 4, 'q': 3}

    def test_location(self):
        view = self._test_view()
        view._resource = Mock(id_name='myid', uid='items')
        view._location(Mock(myid=123))
        view.request.route_url.assert_called_once_with(
            'items', myid=123)

    def test_location_split_id(self):
        view = self._test_view()
        view._resource = Mock(id_name='items_myid', uid='items')
        view._location(Mock(myid=123))
        view.request.route_url.assert_called_once_with(
            'items', items_myid=123)

    def test_get_collection_has_parent(self):
        view = self._test_view()
        view._parent_queryset = Mock(return_value=[1, 2, 3])
        view.Model = Mock()
        view.get_collection(name='ok')
        view._parent_queryset.assert_called_once_with()
        view.Model.filter_objects.assert_called_once_with(
            [1, 2, 3], _limit=20, foo='bar', name='ok')

    def test_get_collection_has_parent_empty_queryset(self):
        view = self._test_view()
        view._parent_queryset = Mock(return_value=[])
        view.Model = Mock()
        view.get_collection(name='ok')
        view._parent_queryset.assert_called_once_with()
        view.Model.filter_objects.assert_called_once_with(
            [], _limit=20, foo='bar', name='ok')

    def test_get_collection_no_parent(self):
        view = self._test_view()
        view._parent_queryset = Mock(return_value=None)
        view.Model = Mock()
        view.get_collection(name='ok')
        view._parent_queryset.assert_called_once_with()
        assert not view.Model.filter_objects.called
        view.Model.get_collection.assert_called_once_with(
            _limit=20, foo='bar', name='ok')

    def test_get_item_no_parent(self):
        view = self._test_view()
        view._parent_queryset = Mock(return_value=None)
        view.context = 1
        assert view.get_item(name='wqe') == 1

    def test_get_item_not_found_in_parent(self):
        view = self._test_view()
        view.Model = Mock(__name__='foo')
        view._get_context_key = Mock(return_value='123123')
        view._parent_queryset = Mock(return_value=[2, 3])
        view.context = 1
        with pytest.raises(JHTTPNotFound):
            view.get_item(name='wqe')

    def test_get_item_found_in_parent(self):
        view = self._test_view()
        view._parent_queryset = Mock(return_value=[1, 3])
        view.context = 1
        assert view.get_item(name='wqe') == 1

    def test_get_item_found_in_parent_context_callable(self):
        func = lambda x: x
        view = self._test_view()
        view._parent_queryset = Mock(return_value=[func, 3])
        view.reload_context = Mock()
        view.context = func
        assert view.get_item(name='wqe') is view.context
        view.reload_context.assert_called_once_with(
            es_based=False, name='wqe')

    def test_get_context_key(self):
        view = self._test_view()
        view._resource = Mock(id_name='foo')
        assert view._get_context_key(foo='bar') == 'bar'

    def test_parent_queryset(self):
        from pyramid.config import Configurator
        from ramses.acl import BaseACL
        config = Configurator()
        config.include('nefertari')
        root = config.get_root_resource()

        class View(self.view_cls, BaseView):
            _json_encoder = 'foo'

        user = root.add(
            'user', 'users', id_name='username',
            view=View, factory=BaseACL)
        user.add(
            'story', 'stories', id_name='prof_id',
            view=View, factory=BaseACL)
        view_cls = root.resource_map['user:story'].view
        view_cls._json_encoder = 'foo'

        request = Mock(
            registry=Mock(),
            path='/foo/foo',
            matchdict={'username': 'user12', 'prof_id': 4},
            accept=[''], method='GET'
        )
        request.params.mixed.return_value = {'foo1': 'bar1'}
        request.blank.return_value = request
        stories_view = view_cls(
            request=request,
            context={},
            _query_params={'foo1': 'bar1'},
            _json_params={'foo2': 'bar2'},)

        parent_view = stories_view._resource.parent.view
        with patch.object(parent_view, 'get_item') as get_item:
            parent_view.get_item = get_item
            result = stories_view._parent_queryset()
            get_item.assert_called_once_with(username='user12')
            assert result == get_item().stories

    def test_reload_context(self):
        class Factory(dict):
            item_model = None

            def __getitem__(self, key):
                return key

        view = self._test_view()
        view._factory = Factory
        view._get_context_key = Mock(return_value='foo')
        view.reload_context(es_based=False, arg='asd')
        view._get_context_key.assert_called_once_with(arg='asd')
        assert view.context == 'foo'


class TestCollectionView(ViewTestBase):
    view_cls = views.CollectionView

    def test_index(self):
        view = self._test_view()
        view.get_collection = Mock()
        resp = view.index(foo='bar')
        view.get_collection.assert_called_once_with()
        assert resp == view.get_collection()

    def test_show(self):
        view = self._test_view()
        view.get_item = Mock()
        resp = view.show(foo='bar')
        view.get_item.assert_called_once_with(foo='bar')
        assert resp == view.get_item()

    def test_create(self):
        view = self._test_view()
        view.set_object_acl = Mock()
        view.request.registry._root_resources = {
            'foo': Mock(auth=False)
        }
        view.Model = Mock()
        obj = Mock()
        obj.to_dict.return_value = {'id': 1}
        view.Model().save.return_value = obj
        view._location = Mock(return_value='/sadasd')
        resp = view.create(foo='bar')
        view.Model.assert_called_with(foo2='bar2')
        view.Model().save.assert_called_with(view.request)
        assert view.set_object_acl.call_count == 1
        assert resp == view.Model().save()

    def test_update(self):
        view = self._test_view()
        view.get_item = Mock()
        view._location = Mock(return_value='/sadasd')
        resp = view.update(foo=1)
        view.get_item.assert_called_once_with(foo=1)
        view.get_item().update.assert_called_once_with(
            {'foo2': 'bar2'}, view.request)
        assert resp == view.get_item().update()

    def test_replace(self):
        view = self._test_view()
        view.update = Mock()
        resp = view.replace(foo=1)
        view.update.assert_called_once_with(foo=1)
        assert resp == view.update()

    def test_delete(self):
        view = self._test_view()
        view.get_item = Mock()
        resp = view.delete(foo=1)
        view.get_item.assert_called_once_with(foo=1)
        view.get_item().delete.assert_called_once_with(
            view.request)
        assert resp is None

    def test_delete_many(self):
        view = self._test_view()
        view.Model = Mock(__name__='Mock')
        view.Model._delete_many.return_value = 123
        view.get_collection = Mock()
        resp = view.delete_many(foo=1)
        view.get_collection.assert_called_once_with()
        view.Model._delete_many.assert_called_once_with(
            view.get_collection(), view.request)
        assert resp == 123

    def test_update_many(self):
        view = self._test_view()
        view.Model = Mock(__name__='Mock')
        view.Model._update_many.return_value = 123
        view.get_collection = Mock()
        resp = view.update_many(qoo=1)
        view.get_collection.assert_called_once_with(_limit=20, foo='bar')
        view.Model._update_many.assert_called_once_with(
            view.get_collection(), {'foo2': 'bar2'},
            view.request)
        assert resp == 123


class TestESBaseView(ViewTestBase):
    view_cls = views.ESBaseView

    def test_parent_queryset_es(self):
        from pyramid.config import Configurator
        from ramses.acl import BaseACL

        class View(self.view_cls, BaseView):
            _json_encoder = 'foo'

        config = Configurator()
        config.include('nefertari')
        root = config.get_root_resource()
        user = root.add(
            'user', 'users', id_name='username',
            view=View, factory=BaseACL)
        user.add(
            'story', 'stories', id_name='prof_id',
            view=View, factory=BaseACL)
        view_cls = root.resource_map['user:story'].view
        view_cls._json_encoder = 'foo'

        request = Mock(
            registry=Mock(),
            path='/foo/foo',
            matchdict={'username': 'user12', 'prof_id': 4},
            accept=[''], method='GET'
        )
        request.params.mixed.return_value = {'foo1': 'bar1'}
        request.blank.return_value = request
        stories_view = view_cls(
            request=request,
            context={},
            _query_params={'foo1': 'bar1'},
            _json_params={'foo2': 'bar2'},)

        parent_view = stories_view._resource.parent.view
        with patch.object(parent_view, 'get_item_es') as get_item_es:
            parent_view.get_item_es = get_item_es
            result = stories_view._parent_queryset_es()
            get_item_es.assert_called_once_with(username='user12')
            assert result == get_item_es().stories

    def test_get_es_object_ids(self):
        view = self._test_view()
        view._resource = Mock(id_name='foobar')
        objects = [Mock(foobar=4), Mock(foobar=7)]
        assert sorted(view.get_es_object_ids(objects)) == ['4', '7']

    @patch('nefertari.elasticsearch.ES')
    def test_get_collection_es_no_parent(self, mock_es):
        mock_es.settings.asbool.return_value = False
        view = self._test_view()
        view._parent_queryset_es = Mock(return_value=None)
        view.Model = Mock(__name__='Foo')
        view.get_collection_es()
        mock_es.assert_called_once_with('Foo')
        mock_es().get_collection.assert_called_once_with(
            _limit=20, foo='bar')

    @patch('nefertari.elasticsearch.ES')
    def test_get_collection_es_parent_no_obj_ids(self, mock_es):
        mock_es.settings.asbool.return_value = False
        view = self._test_view()
        view._parent_queryset_es = Mock(return_value=[1, 2])
        view.Model = Mock(__name__='Foo')
        view.get_es_object_ids = Mock(return_value=None)
        result = view.get_collection_es()
        assert not mock_es().get_collection.called
        assert result == []

    @patch('nefertari.elasticsearch.ES')
    def test_get_collection_es_parent_with_ids(self, mock_es):
        mock_es.settings.asbool.return_value = False
        view = self._test_view()
        view._parent_queryset_es = Mock(return_value=['obj1', 'obj2'])
        view.Model = Mock(__name__='Foo')
        view.get_es_object_ids = Mock(return_value=[1, 2])
        view.get_collection_es()
        view.get_es_object_ids.assert_called_once_with(['obj1', 'obj2'])
        mock_es().get_collection.assert_called_once_with(
            _limit=20, foo='bar', id=[1, 2])

    def test_get_item_es_no_parent(self):
        view = self._test_view()
        view._get_context_key = Mock(return_value=1)
        view._parent_queryset_es = Mock(return_value=None)
        view.reload_context = Mock()
        view.context = 'foo'
        resp = view.get_item_es(a=4)
        view._get_context_key.assert_called_once_with(a=4)
        view._parent_queryset_es.assert_called_once_with()
        assert not view.reload_context.called
        assert resp == 'foo'

    def test_get_item_es_matching_id(self):
        view = self._test_view()
        view._get_context_key = Mock(return_value=1)
        view._parent_queryset_es = Mock(return_value=['obj1', 'obj2'])
        view.get_es_object_ids = Mock(return_value=[1, 2])
        view.reload_context = Mock()
        view.context = 'foo'
        resp = view.get_item_es(a=4)
        view.get_es_object_ids.assert_called_once_with(['obj1', 'obj2'])
        view._get_context_key.assert_called_once_with(a=4)
        view._parent_queryset_es.assert_called_once_with()
        assert not view.reload_context.called
        assert resp == 'foo'

    def test_get_item_es_not_matching_id(self):
        view = self._test_view()
        view._get_context_key = Mock(return_value=1)
        view._parent_queryset_es = Mock(return_value=['obj1', 'obj2'])
        view.get_es_object_ids = Mock(return_value=[2, 3])
        view.reload_context = Mock()
        view.Model = Mock(__name__='Foo')
        view.context = 'foo'
        with pytest.raises(JHTTPNotFound) as ex:
            view.get_item_es(a=4)
        assert 'Foo(id=1) resource not found' in str(ex.value)

    def test_get_item_es_callable_context(self):
        view = self._test_view()
        view._get_context_key = Mock(return_value=1)
        view._parent_queryset_es = Mock(return_value=['obj1', 'obj2'])
        view.get_es_object_ids = Mock(return_value=[1, 2])
        view.reload_context = Mock()
        view.context = lambda x: x
        resp = view.get_item_es(a=4)
        view.reload_context.assert_called_once_with(es_based=True, a=4)
        assert resp == view.context


class TestESCollectionView(ViewTestBase):
    view_cls = views.ESCollectionView

    def test_index(self):
        view = self._test_view()
        view.aggregate = Mock(side_effect=KeyError)
        view.get_collection_es = Mock()
        resp = view.index(foo=1)
        view.get_collection_es.assert_called_once_with()
        assert resp == view.get_collection_es()

    def test_show(self):
        view = self._test_view()
        view.get_item_es = Mock()
        resp = view.show(foo=1)
        view.get_item_es.assert_called_once_with(foo=1)
        assert resp == view.get_item_es()

    def test_update(self):
        view = self._test_view()
        view.get_item = Mock()
        view.reload_context = Mock()
        view._location = Mock(return_value='/sadasd')
        resp = view.update(foo=1)
        view.reload_context.assert_called_once_with(es_based=False, foo=1)
        view.get_item.assert_called_once_with(foo=1)
        view.get_item().update.assert_called_once_with(
            {'foo2': 'bar2'}, view.request)
        assert resp == view.get_item().update()

    def test_replace(self):
        view = self._test_view()
        view.update = Mock()
        resp = view.replace(foo=1)
        view.update.assert_called_once_with(foo=1)
        assert resp == view.update()

    def test_get_dbcollection_with_es(self):
        view = self._test_view()
        view._query_params['_limit'] = 50
        view.get_collection_es = Mock(return_value=[1, 2])
        view.Model = Mock()
        result = view.get_dbcollection_with_es(foo='bar')
        view.get_collection_es.assert_called_once_with()
        view.Model.filter_objects.assert_called_once_with([1, 2])
        assert result == view.Model.filter_objects()

    def test_delete_many(self):
        view = self._test_view()
        view.Model = Mock(__name__='Foo')
        view.Model._delete_many.return_value = 123
        view.get_dbcollection_with_es = Mock()
        result = view.delete_many(foo=1)
        view.get_dbcollection_with_es.assert_called_once_with(foo=1)
        view.Model._delete_many.assert_called_once_with(
            view.get_dbcollection_with_es(), view.request)
        assert result == 123

    def test_update_many(self):
        view = self._test_view()
        view.Model = Mock(__name__='Foo')
        view.Model._update_many.return_value = 123
        view.get_dbcollection_with_es = Mock()
        result = view.update_many(foo=1)
        view.get_dbcollection_with_es.assert_called_once_with(foo=1)
        view.Model._update_many.assert_called_once_with(
            view.get_dbcollection_with_es(), {'foo2': 'bar2'},
            view.request)
        assert result == 123


class TestItemSubresourceBaseView(ViewTestBase):
    view_cls = views.ItemSubresourceBaseView

    def test_get_context_key(self):
        view = self._test_view()
        parent = Mock(id_name='foobar')
        resource = Mock()
        resource.parent = parent
        view._resource = resource
        assert view._get_context_key(foobar=1, foo=2) == '1'

    def test_get_item(self):
        view = self._test_view()
        view._parent_queryset = Mock(return_value=[1, 2])
        view.reload_context = Mock()
        view.context = 1
        assert view.get_item(foo=4) == 1
        view._parent_queryset.assert_called_once_with()
        view.reload_context.assert_called_once_with(es_based=False, foo=4)


class TestItemAttributeView(ViewTestBase):
    view_cls = views.ItemAttributeView
    request_kwargs = dict(
        method='GET',
        accept=[''],
        path='user/1/settings'
    )

    def test_init(self):
        view = self._test_view()
        assert view.value_type is None
        assert view.unique
        assert view.attr == 'settings'

    def test_index(self):
        view = self._test_view()
        view.get_item = Mock()
        resp = view.index(foo=1)
        view.get_item.assert_called_once_with(foo=1)
        assert resp == view.get_item().settings

    def test_create(self):
        view = self._test_view()
        view.get_item = Mock()
        resp = view.create(foo=1)
        view.get_item.assert_called_once_with(foo=1)
        obj = view.get_item()
        obj.update_iterables.assert_called_once_with(
            {'foo2': 'bar2'}, 'settings',
            unique=True, value_type=None,
            request=view.request)
        assert resp == obj.settings


class TestItemSingularView(ViewTestBase):
    view_cls = views.ItemSingularView
    request_kwargs = dict(
        method='GET',
        accept=[''],
        path='user/1/profile',
        url='http://example.com',
    )

    def test_init(self):
        view = self._test_view()
        assert view.attr == 'profile'

    def test_show(self):
        view = self._test_view()
        view.get_item = Mock()
        resp = view.show(foo=1)
        view.get_item.assert_called_once_with(foo=1)
        assert resp == view.get_item().profile

    def test_create(self):
        view = self._test_view()
        view.set_object_acl = Mock()
        view.request.registry._root_resources = {
            'foo': Mock(auth=False)
        }
        view.get_item = Mock()
        view.Model = Mock()
        resp = view.create(foo=1)
        view.get_item.assert_called_once_with(foo=1)
        view.Model.assert_called_once_with(foo2='bar2')
        child = view.Model()
        child.save.assert_called_once_with(view.request)
        parent = view.get_item()
        parent.update.assert_called_once_with(
            {'profile': child.save()}, view.request)
        assert view.set_object_acl.call_count == 1
        assert resp == child.save()

    def test_update(self):
        view = self._test_view()
        view.get_item = Mock()
        resp = view.update(foo=1)
        view.get_item.assert_called_once_with(foo=1)
        child = view.get_item().profile
        child.update.assert_called_once_with(
            {'foo2': 'bar2'}, view.request)
        assert resp == child

    def test_replace(self):
        view = self._test_view()
        view.update = Mock()
        resp = view.replace(foo=1)
        view.update.assert_called_once_with(foo=1)
        assert resp == view.update()

    def test_delete(self):
        view = self._test_view()
        view.attr = 'profile'
        view.get_item = Mock()
        resp = view.delete(foo=1)
        assert resp is None
        view.get_item.assert_called_once_with(foo=1)
        parent = view.get_item()
        parent.profile.delete.assert_called_once_with(
            view.request)


class TestRestViewGeneration(object):

    @patch('ramses.views.NefertariBaseView._run_init_actions')
    def test_only_provided_attrs_are_available(self, run_init):
        config = config_mock()
        view_cls = views.generate_rest_view(
            config, model_cls='foo', attrs=['show', 'foobar'],
            es_based=True, attr_view=False, singular=False)
        view_cls._json_encoder = 'foo'
        assert issubclass(view_cls, views.ESCollectionView)
        request = Mock(**ViewTestBase.request_kwargs)
        view = view_cls(request=request, **ViewTestBase.view_kwargs)
        assert not hasattr(view_cls, 'foobar')

        try:
            view.show()
        except JHTTPMethodNotAllowed:
            raise Exception('Unexpected error')
        except Exception:
            pass
        with pytest.raises(JHTTPMethodNotAllowed):
            view.delete_many()
        with pytest.raises(JHTTPMethodNotAllowed):
            view.create()
        with pytest.raises(JHTTPMethodNotAllowed):
            view.delete()
        with pytest.raises(JHTTPMethodNotAllowed):
            view.update_many()
        with pytest.raises(JHTTPMethodNotAllowed):
            view.index()

    def test_singular_view(self):
        config = config_mock()
        view_cls = views.generate_rest_view(
            config, model_cls='foo', attrs=['show'],
            es_based=True, attr_view=False, singular=True)
        view_cls._json_encoder = 'foo'
        assert issubclass(view_cls, views.ItemSingularView)

    def test_attribute_view(self):
        config = config_mock()
        view_cls = views.generate_rest_view(
            config, model_cls='foo', attrs=['show'],
            es_based=True, attr_view=True, singular=False)
        view_cls._json_encoder = 'foo'
        assert issubclass(view_cls, views.ItemAttributeView)

    def test_escollection_view(self):
        config = config_mock()
        view_cls = views.generate_rest_view(
            config, model_cls='foo', attrs=['show'],
            es_based=True, attr_view=False, singular=False)
        view_cls._json_encoder = 'foo'
        assert issubclass(view_cls, views.ESCollectionView)
        assert issubclass(view_cls, views.CollectionView)

    def test_dbcollection_view(self):
        config = config_mock()
        view_cls = views.generate_rest_view(
            config, model_cls='foo', attrs=['show'],
            es_based=False, attr_view=False, singular=False)
        view_cls._json_encoder = 'foo'
        assert not issubclass(view_cls, views.ESCollectionView)
        assert issubclass(view_cls, views.CollectionView)

    def test_default_values(self):
        config = config_mock()
        view_cls = views.generate_rest_view(
            config, model_cls='foo', attrs=['show'])
        view_cls._json_encoder = 'foo'
        assert issubclass(view_cls, views.ESCollectionView)
        assert issubclass(view_cls, views.CollectionView)
        assert view_cls.Model == 'foo'

    def test_database_acls_option(self):
        from nefertari_guards.view import ACLFilterViewMixin
        config = config_mock()

        config.registry.database_acls = False
        view_cls = views.generate_rest_view(
            config, model_cls='foo', attrs=['show'],
            es_based=False, attr_view=False, singular=False)
        assert not issubclass(
            view_cls, ACLFilterViewMixin)
        assert not issubclass(
            view_cls, views.SetObjectACLMixin)

        config.registry.database_acls = True
        view_cls = views.generate_rest_view(
            config, model_cls='foo', attrs=['show'],
            es_based=False, attr_view=False, singular=False)
        assert issubclass(view_cls, views.SetObjectACLMixin)
        assert issubclass(view_cls, ACLFilterViewMixin)
