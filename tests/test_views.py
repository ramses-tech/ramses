import pytest
from mock import Mock, patch

from nefertari.json_httpexceptions import (
    JHTTPNotFound, JHTTPCreated, JHTTPOk, JHTTPMethodNotAllowed)

from ramses import views


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
        request = Mock(**self.request_kwargs)
        return self.view_cls(request=request, **self.view_kwargs)


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
        view._model_class = Mock()
        view.get_collection(name='ok')
        view._parent_queryset.assert_called_once_with()
        view._model_class.filter_objects.assert_called_once_with(
            [1, 2, 3], _limit=20, foo='bar', name='ok')

    def test_get_collection_has_parent_empty_queryset(self):
        view = self._test_view()
        view._parent_queryset = Mock(return_value=[])
        view._model_class = Mock()
        view.get_collection(name='ok')
        view._parent_queryset.assert_called_once_with()
        view._model_class.filter_objects.assert_called_once_with(
            [], _limit=20, foo='bar', name='ok')

    def test_get_collection_no_parent(self):
        view = self._test_view()
        view._parent_queryset = Mock(return_value=None)
        view._model_class = Mock()
        view.get_collection(name='ok')
        view._parent_queryset.assert_called_once_with()
        assert not view._model_class.filter_objects.called
        view._model_class.get_collection.assert_called_once_with(
            _limit=20, foo='bar', name='ok')

    def test_get_item_no_parent(self):
        view = self._test_view()
        view._parent_queryset = Mock(return_value=None)
        view.context = 1
        assert view.get_item(name='wqe') == 1

    def test_get_item_not_found_in_parent(self):
        view = self._test_view()
        view._model_class = Mock(__name__='foo')
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
        user = root.add(
            'user', 'users', id_name='username',
            view=views.BaseView, factory=BaseACL)
        user.add(
            'story', 'stories', id_name='prof_id',
            view=views.BaseView, factory=BaseACL)
        view_cls = root.resource_map['user:story'].view

        request = Mock(
            registry={'foo': 'bar'},
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
            __context_class__ = None

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
        view.index(foo='bar')
        view.get_collection.assert_called_once_with()

    def test_show(self):
        view = self._test_view()
        view.get_item = Mock()
        view.show(foo='bar')
        view.get_item.assert_called_once_with(foo='bar')

    def test_create(self):
        view = self._test_view()
        view.request.registry._root_resources = {
            'foo': Mock(auth=False)
        }
        view._model_class = Mock()
        obj = Mock()
        obj.to_dict.return_value = {'id': 1}
        view._model_class().save.return_value = obj
        view._location = Mock(return_value='/sadasd')
        resp = view.create(foo='bar')
        view._model_class.assert_called_with(foo2='bar2')
        view._model_class().save.assert_called_with(
            refresh_index=None)
        assert isinstance(resp, JHTTPCreated)
        assert resp.location == '/sadasd'

    def test_update(self):
        view = self._test_view()
        view.get_item = Mock()
        view._location = Mock(return_value='/sadasd')
        resp = view.update(foo=1)
        view.get_item.assert_called_once_with(foo=1)
        view.get_item().update.assert_called_once_with(
            {'foo2': 'bar2'}, refresh_index=None)
        assert isinstance(resp, JHTTPOk)

    def test_replace(self):
        view = self._test_view()
        view.update = Mock()
        view.replace(foo=1)
        view.update.assert_called_once_with(foo=1)

    def test_delete(self):
        view = self._test_view()
        view.get_item = Mock()
        resp = view.delete(foo=1)
        view.get_item.assert_called_once_with(foo=1)
        view.get_item().delete.assert_called_once_with(
            refresh_index=None)
        assert isinstance(resp, JHTTPOk)

    def test_delete_many_needs_confirm(self):
        view = self._test_view()
        view._model_class = Mock()
        view.get_collection = Mock()
        view.needs_confirmation = Mock(return_value=True)
        resp = view.delete_many(foo=1)
        view.get_collection.assert_called_once_with()
        view._model_class.count.assert_called_once_with(view.get_collection())
        assert resp == view.get_collection()

    def test_delete_many(self):
        view = self._test_view()
        view._model_class = Mock(__name__='Mock')
        view.get_collection = Mock()
        view.needs_confirmation = Mock(return_value=False)
        resp = view.delete_many(foo=1)
        view.get_collection.assert_called_once_with()
        view._model_class.count.assert_called_once_with(view.get_collection())
        view._model_class._delete_many.assert_called_once_with(
            view.get_collection(), refresh_index=None)
        assert isinstance(resp, JHTTPOk)

    def test_update_many(self):
        view = self._test_view()
        view._model_class = Mock(__name__='Mock')
        view.get_collection = Mock()
        resp = view.update_many(qoo=1)
        view.get_collection.assert_called_once_with(_limit=20, foo='bar')
        view._model_class._update_many.assert_called_once_with(
            view.get_collection(), foo2='bar2',
            refresh_index=None)
        assert isinstance(resp, JHTTPOk)


class TestESBaseView(ViewTestBase):
    view_cls = views.ESBaseView

    def test_get_raw_terms(self):
        view = self._test_view()
        view._query_params['q'] = 'foo'
        assert view._get_raw_terms() == 'foo'

    def test_parent_queryset_es(self):
        from pyramid.config import Configurator
        from ramses.acl import BaseACL
        config = Configurator()
        config.include('nefertari')
        root = config.get_root_resource()
        user = root.add(
            'user', 'users', id_name='username',
            view=views.ESBaseView, factory=BaseACL)
        user.add(
            'story', 'stories', id_name='prof_id',
            view=views.ESBaseView, factory=BaseACL)
        view_cls = root.resource_map['user:story'].view

        request = Mock(
            registry={'foo': 'bar'},
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
        view = self._test_view()
        view._parent_queryset_es = Mock(return_value=None)
        view._model_class = Mock(__name__='Foo')
        view.get_collection_es(arg=1)
        mock_es.assert_called_once_with('Foo')
        mock_es().get_collection.assert_called_once_with(
            _raw_terms='', _limit=20, foo='bar')

    @patch('nefertari.elasticsearch.ES')
    def test_get_collection_es_parent_no_obj_ids(self, mock_es):
        view = self._test_view()
        view._parent_queryset_es = Mock(return_value=[1, 2])
        view._model_class = Mock(__name__='Foo')
        view.get_es_object_ids = Mock(return_value=None)
        result = view.get_collection_es(arg=1)
        assert not mock_es().get_collection.called
        assert result == []

    @patch('nefertari.elasticsearch.ES')
    def test_get_collection_es_parent_with_ids(self, mock_es):
        view = self._test_view()
        view._parent_queryset_es = Mock(return_value=['obj1', 'obj2'])
        view._model_class = Mock(__name__='Foo')
        view.get_es_object_ids = Mock(return_value=[1, 2])
        view.get_collection_es(arg=7)
        view.get_es_object_ids.assert_called_once_with(['obj1', 'obj2'])
        mock_es().get_collection.assert_called_once_with(
            _raw_terms='', _limit=20, foo='bar', id=[1, 2])

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
        view._model_class = Mock(__name__='Foo')
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
        view.get_collection_es.assert_called_once_with(foo=1)
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
        view.update(foo=1)
        view.reload_context.assert_called_once_with(es_based=False, foo=1)
        view.get_item.assert_called_once_with(foo=1)
        view.get_item().update.assert_called_once_with(
            {'foo2': 'bar2'}, refresh_index=None)

    def test_replace(self):
        view = self._test_view()
        view.update = Mock()
        view.replace(foo=1)
        view.update.assert_called_once_with(foo=1)

    def test_get_dbcollection_with_es(self):
        view = self._test_view()
        view._query_params['_limit'] = 50
        view.get_collection_es = Mock(return_value=[1, 2])
        view._model_class = Mock()
        result = view.get_dbcollection_with_es(foo='bar')
        view.get_collection_es.assert_called_once_with(foo='bar')
        view._model_class.filter_objects.assert_called_once_with(
            [1, 2], _limit=50)
        assert result == view._model_class.filter_objects()

    def test_delete_many_need_confirmation(self):
        view = self._test_view()
        view.needs_confirmation = Mock(return_value=True)
        view._model_class = Mock()
        view.get_dbcollection_with_es = Mock()
        result = view.delete_many(foo=1)
        view.get_dbcollection_with_es.assert_called_once_with(foo=1)
        view._model_class.count.assert_called_once_with(
            view.get_dbcollection_with_es())
        assert result == view.get_dbcollection_with_es()
        assert not view._model_class._delete_many.called

    def test_delete_many(self):
        view = self._test_view()
        view.needs_confirmation = Mock(return_value=False)
        view._model_class = Mock(__name__='Foo')
        view.get_dbcollection_with_es = Mock()
        result = view.delete_many(foo=1)
        view.get_dbcollection_with_es.assert_called_once_with(foo=1)
        view._model_class.count.assert_called_once_with(
            view.get_dbcollection_with_es())
        view._model_class._delete_many.assert_called_once_with(
            view.get_dbcollection_with_es(), refresh_index=None)
        assert isinstance(result, JHTTPOk)

    def test_update_many(self):
        view = self._test_view()
        view.needs_confirmation = Mock(return_value=False)
        view._model_class = Mock(__name__='Foo')
        view.get_dbcollection_with_es = Mock()
        result = view.update_many(foo=1)
        view.get_dbcollection_with_es.assert_called_once_with(foo=1)
        view._model_class.count.assert_called_once_with(
            view.get_dbcollection_with_es())
        view._model_class._update_many.assert_called_once_with(
            view.get_dbcollection_with_es(), foo2='bar2',
            refresh_index=None)
        assert isinstance(result, JHTTPOk)


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
            refresh_index=None)
        assert isinstance(resp, JHTTPCreated)


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
        view.request.registry._root_resources = {
            'foo': Mock(auth=False)
        }
        view.get_item = Mock()
        view._singular_model = Mock()
        resp = view.create(foo=1)
        assert isinstance(resp, JHTTPCreated)
        view.get_item.assert_called_once_with(foo=1)
        view._singular_model.assert_called_once_with(foo2='bar2')
        child = view._singular_model()
        child.save.assert_called_once_with(refresh_index=None)
        parent = view.get_item()
        parent.update.assert_called_once_with(
            {'profile': child.save()}, refresh_index=None)

    def test_update(self):
        view = self._test_view()
        view.get_item = Mock()
        resp = view.update(foo=1)
        assert isinstance(resp, JHTTPOk)
        view.get_item.assert_called_once_with(foo=1)
        child = view.get_item().profile
        child.update.assert_called_once_with(
            {'foo2': 'bar2'}, refresh_index=None)

    def test_replace(self):
        view = self._test_view()
        view.update = Mock()
        view.replace(foo=1)
        view.update.assert_called_once_with(foo=1)

    def test_delete(self):
        view = self._test_view()
        view.attr = 'profile'
        view.get_item = Mock()
        resp = view.delete(foo=1)
        assert isinstance(resp, JHTTPOk)
        view.get_item.assert_called_once_with(foo=1)
        parent = view.get_item()
        parent.profile.delete.assert_called_once_with(
            refresh_index=None)


@patch('ramses.views.engine')
class TestRestViewGeneration(object):

    @patch('ramses.views.ESCollectionView._run_init_actions')
    def test_only_provided_attrs_are_available(self, run_init, mock_eng):
        view_cls = views.generate_rest_view(
            model_cls='foo', attrs=['show', 'foobar'],
            es_based=True, attr_view=False, singular=False)
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

    def test_singular_view(self, mock_eng):
        view_cls = views.generate_rest_view(
            model_cls='foo', attrs=['show'],
            es_based=True, attr_view=False, singular=True)
        assert issubclass(view_cls, views.ItemSingularView)

    def test_attribute_view(self, mock_eng):
        view_cls = views.generate_rest_view(
            model_cls='foo', attrs=['show'],
            es_based=True, attr_view=True, singular=False)
        assert issubclass(view_cls, views.ItemAttributeView)

    def test_escollection_view(self, mock_eng):
        view_cls = views.generate_rest_view(
            model_cls='foo', attrs=['show'],
            es_based=True, attr_view=False, singular=False)
        assert issubclass(view_cls, views.ESCollectionView)
        assert issubclass(view_cls, views.CollectionView)

    def test_dbcollection_view(self, mock_eng):
        view_cls = views.generate_rest_view(
            model_cls='foo', attrs=['show'],
            es_based=False, attr_view=False, singular=False)
        assert not issubclass(view_cls, views.ESCollectionView)
        assert issubclass(view_cls, views.CollectionView)

    def test_default_values(self, mock_eng):
        view_cls = views.generate_rest_view(
            model_cls='foo', attrs=['show'])
        assert issubclass(view_cls, views.ESCollectionView)
        assert issubclass(view_cls, views.CollectionView)
        assert view_cls._model_class == 'foo'
        assert view_cls._json_encoder == mock_eng.JSONEncoder
