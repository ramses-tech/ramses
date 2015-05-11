import pytest
from mock import Mock

from nefertari.json_httpexceptions import (
    JHTTPNotFound, JHTTPCreated, JHTTPOk)

from ramses import views


view_kwargs = dict(
    context={},
    _query_params={'foo': 'bar'},
    _json_params={'foo2': 'bar2'},
)
request_kwargs = dict(
    method='GET',
    accept=[''],
)


class TestBaseView(object):
    def _simple_view(self):
        request = Mock(**request_kwargs)
        return views.BaseView(request=request, **view_kwargs)

    def test_init(self):
        view = self._simple_view()
        assert view._query_params['_limit'] == 20

    def test_clean_id_name(self):
        view = self._simple_view()
        view._resource = Mock(id_name='foo')
        assert view.clean_id_name == 'foo'
        view._resource = Mock(id_name='foo_bar')
        assert view.clean_id_name == 'bar'

    def test_resolve_kw(self):
        view = self._simple_view()
        kwargs = {'foo_bar_qoo': 1, 'arg_val': 4, 'q': 3}
        assert view.resolve_kw(kwargs) == {'bar_qoo': 1, 'val': 4, 'q': 3}

    def test_location(self):
        view = self._simple_view()
        view._resource = Mock(id_name='myid', uid='items')
        view._location(Mock(myid=123))
        view.request.route_url.assert_called_once_with(
            'items', myid=123)

    def test_location_split_id(self):
        view = self._simple_view()
        view._resource = Mock(id_name='items_myid', uid='items')
        view._location(Mock(myid=123))
        view.request.route_url.assert_called_once_with(
            'items', items_myid=123)

    def test_get_collection_has_parent(self):
        view = self._simple_view()
        view._parent_queryset = Mock(return_value=[1, 2, 3])
        view._model_class = Mock()
        view.get_collection(name='ok')
        view._parent_queryset.assert_called_once_with()
        view._model_class.filter_objects.assert_called_once_with(
            [1, 2, 3], _limit=20, foo='bar', name='ok')

    def test_get_collection_has_parent_empty_queryset(self):
        view = self._simple_view()
        view._parent_queryset = Mock(return_value=[])
        view._model_class = Mock()
        view.get_collection(name='ok')
        view._parent_queryset.assert_called_once_with()
        view._model_class.filter_objects.assert_called_once_with(
            [], _limit=20, foo='bar', name='ok')

    def test_get_collection_no_parent(self):
        view = self._simple_view()
        view._parent_queryset = Mock(return_value=None)
        view._model_class = Mock()
        view.get_collection(name='ok')
        view._parent_queryset.assert_called_once_with()
        assert not view._model_class.filter_objects.called
        view._model_class.get_collection.assert_called_once_with(
            _limit=20, foo='bar', name='ok')

    def test_get_item_no_parent(self):
        view = self._simple_view()
        view._parent_queryset = Mock(return_value=None)
        view.context = 1
        assert view.get_item(name='wqe') == 1

    def test_get_item_not_found_in_parent(self):
        view = self._simple_view()
        view._model_class = Mock(__name__='foo')
        view._get_context_key = Mock(return_value='123123')
        view._parent_queryset = Mock(return_value=[2, 3])
        view.context = 1
        with pytest.raises(JHTTPNotFound):
            view.get_item(name='wqe')

    def test_get_item_found_in_parent(self):
        view = self._simple_view()
        view._parent_queryset = Mock(return_value=[1, 3])
        view.context = 1
        assert view.get_item(name='wqe') == 1

    def test_get_item_found_in_parent_context_callable(self):
        func = lambda x: x
        view = self._simple_view()
        view._parent_queryset = Mock(return_value=[func, 3])
        view.reload_context = Mock()
        view.context = func
        assert view.get_item(name='wqe') is view.context
        view.reload_context.assert_called_once_with(
            es_based=False, name='wqe')

    def test_get_context_key(self):
        view = self._simple_view()
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

        get_item = Mock()
        stories_view._resource.parent.view.get_item = get_item
        result = stories_view._parent_queryset()
        get_item.assert_called_once_with(username='user12')
        assert result == get_item().stories

    def test_reload_context(self):
        class Factory(dict):
            __context_class__ = None
            def __getitem__(self, key):
                return key

        view = self._simple_view()
        view._factory = Factory
        view._get_context_key = Mock(return_value='foo')
        view.reload_context(es_based=False, arg='asd')
        view._get_context_key.assert_called_once_with(arg='asd')
        assert view.context == 'foo'


class TestCollectionView(object):
    def _simple_view(self):
        request = Mock(**request_kwargs)
        return views.CollectionView(request=request, **view_kwargs)

    def test_index(self):
        view = self._simple_view()
        view.get_collection = Mock()
        view.index(foo='bar')
        view.get_collection.assert_called_once_with()

    def test_show(self):
        view = self._simple_view()
        view.get_item = Mock()
        view.show(foo='bar')
        view.get_item.assert_called_once_with(foo='bar')

    def test_create(self):
        view = self._simple_view()
        view._model_class = Mock()
        obj = Mock()
        obj.to_dict.return_value = {'id': 1}
        view._model_class().save.return_value = obj
        view._location = Mock(return_value='/sadasd')
        resp = view.create(foo='bar')
        view._model_class.assert_called_with(foo2='bar2')
        view._model_class().save.assert_called_with()
        assert isinstance(resp, JHTTPCreated)
        assert resp.location == '/sadasd'

    def test_update(self):
        view = self._simple_view()
        view.get_item = Mock()
        view._location = Mock(return_value='/sadasd')
        resp = view.update(foo=1)
        view.get_item.assert_called_once_with(foo=1)
        view.get_item().update.assert_called_once_with({'foo2': 'bar2'})
        assert isinstance(resp, JHTTPOk)

    def test_delete(self):
        view = self._simple_view()
        view._model_class = Mock()
        resp = view.delete(foo=1)
        view._model_class._delete.assert_called_once_with(foo=1)
        assert isinstance(resp, JHTTPOk)

    def test_delete_many_needs_confirm(self):
        view = self._simple_view()
        view._model_class = Mock()
        view.get_collection = Mock()
        view.needs_confirmation = Mock(return_value=True)
        resp = view.delete_many(foo=1)
        view.get_collection.assert_called_once_with()
        view._model_class.count.assert_called_once_with(view.get_collection())
        assert resp == view.get_collection()

    def test_delete_many(self):
        view = self._simple_view()
        view._model_class = Mock(__name__='Mock')
        view.get_collection = Mock()
        view.needs_confirmation = Mock(return_value=False)
        resp = view.delete_many(foo=1)
        view.get_collection.assert_called_once_with()
        view._model_class.count.assert_called_once_with(view.get_collection())
        view._model_class._delete_many.assert_called_once_with(
            view.get_collection())
        assert isinstance(resp, JHTTPOk)

    def test_update_many(self):
        view = self._simple_view()
        view._model_class = Mock(__name__='Mock')
        view.get_collection = Mock()
        resp = view.update_many(qoo=1)
        view.get_collection.assert_called_once_with(_limit=20, foo='bar')
        view._model_class._update_many.assert_called_once_with(
            view.get_collection(), foo2='bar2')
        assert isinstance(resp, JHTTPOk)
