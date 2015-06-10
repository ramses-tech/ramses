import logging

import six
from nefertari.view import BaseView as NefertariBaseView, ESAggregationMixin
from nefertari.json_httpexceptions import (
    JHTTPCreated, JHTTPOk, JHTTPNotFound)
from nefertari import engine


log = logging.getLogger(__name__)

"""
Maps of {HTTP_method: neferteri view method name}

"""
collection_methods = {
    'get':      'index',
    'post':     'create',
    'put':      'update_many',
    'patch':    'update_many',
    'delete':   'delete_many',
}
item_methods = {
    'get':      'show',
    'post':     'create',
    'put':      'update',
    'patch':    'update',
    'delete':   'delete',
}


class BaseView(NefertariBaseView):
    """ Base view class for other all views that defines few helper methods.

    Use `self.get_collection` and `self.get_item` to get access to set of
    objects and object respectively which are valid at current level.
    """
    def __init__(self, *args, **kwargs):
        super(BaseView, self).__init__(*args, **kwargs)
        if self.request.method == 'GET':
            self._query_params.process_int_param('_limit', 20)

    @property
    def clean_id_name(self):
        id_name = self._resource.id_name
        if '_' in id_name:
            return id_name.split('_', 1)[1]
        else:
            return id_name

    def resolve_kw(self, kwargs):
        """ Resolve :kwargs: like `story_id: 1` to the form of `id: 1`.

        """
        resolved = {}
        for key, value in kwargs.items():
            split = key.split('_', 1)
            if len(split) > 1:
                key = split[1]
            resolved[key] = value
        return resolved

    def _location(self, obj):
        """ Get location of the `obj`

        Arguments:
            :obj: self._model_class instance.
        """
        field_name = self.clean_id_name
        return self.request.route_url(
            self._resource.uid,
            **{self._resource.id_name: getattr(obj, field_name)})

    def _parent_queryset(self):
        """ Get queryset of parent view.

        Generated queryset is used to run queries in the current level view.
        """
        parent = self._resource.parent
        if hasattr(parent, 'view'):
            req = self.request.blank(self.request.path)
            req.registry = self.request.registry
            req.matchdict = {
                parent.id_name: self.request.matchdict.get(parent.id_name)}
            parent_view = parent.view(parent.view._factory, req)
            obj = parent_view.get_item(**req.matchdict)
            if isinstance(self, ItemSubresourceBaseView):
                return
            prop = self._resource.collection_name
            return getattr(obj, prop, None)

    def get_collection(self, **kwargs):
        """ Get objects collection taking into account generated queryset
        of parent view.

        This method allows working with nested resources properly. Thus a
        queryset returned by this method will be a subset of its parent
        view's queryset, thus filtering out objects that don't belong to
        the parent object.
        """
        self._query_params.update(kwargs)
        objects = self._parent_queryset()
        if objects is not None:
            return self._model_class.filter_objects(
                objects, **self._query_params)
        return self._model_class.get_collection(**self._query_params)

    def get_item(self, **kwargs):
        """ Get collection item taking into account generated queryset
        of parent view.

        This method allows working with nested resources properly. Thus an item
        returned by this method will belong to its parent view's queryset, thus
        filtering out objects that don't belong to the parent object.

        Returns an object from the applicable ACL. If ACL wasn't applied, it is
        applied explicitly.
        """
        if six.callable(self.context):
            self.reload_context(es_based=False, **kwargs)

        objects = self._parent_queryset()
        if objects is not None and self.context not in objects:
            raise JHTTPNotFound('{}({}) not found'.format(
                self._model_class.__name__,
                self._get_context_key(**kwargs)))

        return self.context

    def _get_context_key(self, **kwargs):
        """ Get value of `self._resource.id_name` from :kwargs: """
        return str(kwargs.get(self._resource.id_name))

    def reload_context(self, es_based, **kwargs):
        """ Reload `self.context` object into a DB or ES object.

        A reload is performed by getting the object ID from :kwargs: and then
        getting a context key item from the new instance of `self._factory`
        which is an ACL class used by the current view.

        Arguments:
            :es_based: Boolean. Whether to init ACL ac es-based or not. This
                affects the backend which will be queried - either DB or ES
            :kwargs: Kwargs that contain value for current resource 'id_name'
                key
        """
        from .acl import BaseACL
        key = self._get_context_key(**kwargs)
        kwargs = {'request': self.request}
        if issubclass(self._factory, BaseACL):
            kwargs['es_based'] = es_based

        acl = self._factory(**kwargs)
        if acl.__context_class__ is None:
            acl.__context_class__ = self._model_class

        self.context = acl[key]


class CollectionView(BaseView):
    """ View that works with database and implements handlers for all
    available CRUD operations.

    """
    def index(self, **kwargs):
        return self.get_collection()

    def show(self, **kwargs):
        return self.get_item(**kwargs)

    def create(self, **kwargs):
        obj = self._model_class(**self._json_params)
        obj = obj.save(refresh_index=self.refresh_index)
        return JHTTPCreated(
            location=self._location(obj),
            resource=obj.to_dict(),
            encoder=self._json_encoder,
            request=self.request)

    def update(self, **kwargs):
        obj = self.get_item(**kwargs)
        obj.update(self._json_params, refresh_index=self.refresh_index)
        return JHTTPOk('Updated', location=self._location(obj))

    def replace(self, **kwargs):
        return self.update(**kwargs)

    def delete(self, **kwargs):
        obj = self.get_item(**kwargs)
        obj.delete(refresh_index=self.refresh_index)
        return JHTTPOk('Deleted')

    def delete_many(self, **kwargs):
        objects = self.get_collection()
        count = self._model_class.count(objects)

        if self.needs_confirmation():
            return objects

        self._model_class._delete_many(
            objects, refresh_index=self.refresh_index)
        return JHTTPOk('Deleted %s %s(s) objects' % (
            count, self._model_class.__name__))

    def update_many(self, **kwargs):
        objects = self.get_collection(**self._query_params)
        count = self._model_class.count(objects)
        self._model_class._update_many(
            objects, refresh_index=self.refresh_index, **self._json_params)
        return JHTTPOk('Updated %s %s(s) objects' % (
            count, self._model_class.__name__))


class ESBaseView(BaseView):
    """ Elasticsearch base view that fetches data from ES.

    Implements analogues of _parent_queryset, get_collection, get_item
    fetching data from ES instead of database.

    Use `self.get_collection_es` and `self.get_item_es` to get access
    to the set of objects and individual object respectively which are
    valid at the current level.
    """
    def _get_raw_terms(self):
        search_params = []
        if 'q' in self._query_params:
            search_params.append(self._query_params.pop('q'))
        _raw_terms = ' AND '.join(search_params)
        return _raw_terms

    def _parent_queryset_es(self):
        """ Get queryset (list of object IDs) of parent view.

        The generated queryset is used to run queries in the current level's
        view.
        """
        parent = self._resource.parent
        if hasattr(parent, 'view'):
            req = self.request.blank(self.request.path)
            req.registry = self.request.registry
            req.matchdict = {
                parent.id_name: self.request.matchdict.get(parent.id_name)}
            parent_view = parent.view(parent.view._factory, req)
            obj = parent_view.get_item_es(**req.matchdict)
            prop = self._resource.collection_name
            objects_ids = getattr(obj, prop, None)
            return objects_ids

    def get_es_object_ids(self, objects):
        """ Return IDs of :objects: if they are not IDs already. """
        id_field = self.clean_id_name
        ids = [getattr(obj, id_field, obj) for obj in objects]
        return list(set(str(id_) for id_ in ids))

    def get_collection_es(self, **kwargs):
        """ Get ES objects collection taking into account the generated
        queryset of parent view.

        This method allows working with nested resources properly. Thus a
        queryset returned by this method will be a subset of its parent view's
        queryset, thus filtering out objects that don't belong to the parent
        object.
        """
        from nefertari.elasticsearch import ES
        es = ES(self._model_class.__name__)
        objects_ids = self._parent_queryset_es()

        if objects_ids is not None:
            objects_ids = self.get_es_object_ids(objects_ids)

            if not objects_ids:
                return []
            self._query_params['id'] = objects_ids
        return es.get_collection(
            _raw_terms=self._get_raw_terms(),
            **self._query_params)

    def get_item_es(self, **kwargs):
        """ Get ES collection item taking into account generated queryset
        of parent view.

        This method allows working with nested resources properly. Thus an item
        returned by this method will belong to its parent view's queryset, thus
        filtering out objects that don't belong to the parent object.

        Returns an object retrieved from the applicable ACL. If an ACL wasn't
        applied, it is applied explicitly.
        """
        item_id = self._get_context_key(**kwargs)
        objects_ids = self._parent_queryset_es()
        if objects_ids is not None:
            objects_ids = self.get_es_object_ids(objects_ids)

        if six.callable(self.context):
            self.reload_context(es_based=True, **kwargs)

        if (objects_ids is not None) and (item_id not in objects_ids):
            raise JHTTPNotFound('{}(id={}) resource not found'.format(
                self._model_class.__name__, item_id))

        return self.context


class ESCollectionView(ESAggregationMixin, ESBaseView, CollectionView):
    """ View that reads data from ES.

    Write operations are inherited from :CollectionView:
    """
    def index(self, **kwargs):
        try:
            return self.aggregate()
        except KeyError:
            return self.get_collection_es(**kwargs)

    def show(self, **kwargs):
        return self.get_item_es(**kwargs)

    def update(self, **kwargs):
        """ Explicitly reload context with DB usage to get access
        to complete DB object.
        """
        self.reload_context(es_based=False, **kwargs)
        return super(ESCollectionView, self).update(**kwargs)

    def delete(self, **kwargs):
        """ Explicitly reload context with DB usage to get access
        to complete DB object.
        """
        self.reload_context(es_based=False, **kwargs)
        return super(ESCollectionView, self).delete(**kwargs)

    def get_dbcollection_with_es(self, **kwargs):
        """ Get DB objects collection by first querying ES. """
        es_objects = self.get_collection_es(**kwargs)
        db_objects = self._model_class.filter_objects(
            es_objects, _limit=self._query_params.get('_limit'))
        return db_objects

    def delete_many(self, **kwargs):
        """ Delete multiple objects from collection.

        First ES is queried, then the results are used to query the DB.
        This is done to make sure deleted objects are those filtered
        by ES in the 'index' method (so user deletes what he saw).
        """
        db_objects = self.get_dbcollection_with_es(**kwargs)
        count = self._model_class.count(db_objects)

        if self.needs_confirmation():
            return db_objects

        self._model_class._delete_many(
            db_objects, refresh_index=self.refresh_index)
        return JHTTPOk('Deleted %s %s(s) objects' % (
            count, self._model_class.__name__))

    def update_many(self, **kwargs):
        """ Update multiple objects from collection.

        First ES is queried, then the results are used to query DB.
        This is done to make sure updated objects are those filtered
        by ES in the 'index' method (so user updates what he saw).
        """
        db_objects = self.get_dbcollection_with_es(**kwargs)
        count = self._model_class.count(db_objects)

        self._model_class._update_many(
            db_objects, refresh_index=self.refresh_index, **self._json_params)
        return JHTTPOk('Updated %s %s(s) objects' % (
            count, self._model_class.__name__))


class ItemSubresourceBaseView(BaseView):
    """ Base class for all subresources of collection item resources which
    don't represent a collection of their own.
    E.g. /users/{id}/profile, where 'profile' is a singular resource or
    /users/{id}/some_action, where the 'some_action' action may be
    performed when requesting this route.

    Subclass ItemSubresourceBaseView in your project when you want to
    define a subroute and view of an item route defined in RAML and
    generated by ramses.
    Use `self.get_item` to get an object on which actions are being
    performed.

    Moved into a separate class so all item subresources have a common
    base class, thus making checks like `isinstance(view, baseClass)` easier.
    Also to override `_get_context_key` to return parent resource's id_name
    and `get_item` to reload context on each access.
    """

    def _get_context_key(self, **kwargs):
        """ Get value of `self._resource.parent.id_name` from :kwargs: """
        return str(kwargs.get(self._resource.parent.id_name))

    def get_item(self, **kwargs):
        """ Reload context on each access. """
        self.reload_context(es_based=False, **kwargs)
        return super(ItemSubresourceBaseView, self).get_item(**kwargs)


class ItemAttributeView(ItemSubresourceBaseView):
    """ View used to work with attribute resources.

    Attribute resources represent field: ListField, DictField.

    You may subclass ItemAttributeView in your project when you want to
    define custom attribute subroute and view of a item route defined in
    RAML and generated by ramses.
    """
    def __init__(self, *args, **kw):
        super(ItemAttributeView, self).__init__(*args, **kw)
        self.attr = self.request.path.split('/')[-1]
        self.value_type = None
        self.unique = True

    def index(self, **kwargs):
        obj = self.get_item(**kwargs)
        return getattr(obj, self.attr)

    def create(self, **kwargs):
        obj = self.get_item(**kwargs)
        obj.update_iterables(
            self._json_params, self.attr,
            unique=self.unique,
            value_type=self.value_type,
            refresh_index=self.refresh_index)
        return JHTTPCreated(
            resource=getattr(obj, self.attr, None),
            encoder=self._json_encoder)


class ItemSingularView(ItemSubresourceBaseView):
    """ View used to work with singular resources.

    Singular resources represent a one-to-one relationship.
    E.g. users/1/profile.

    You may subclass ItemSingularView in your project when you want to define
    a custom singular subroute and view of an item route defined in RAML and
    generated by ramses.
    If you decide to do so, make sure to set `self._singular_model` to a model
    class, instances of which will be processed by this view.
    """
    _singular_model = None

    def __init__(self, *args, **kw):
        super(ItemSingularView, self).__init__(*args, **kw)
        self.attr = self.request.path.split('/')[-1]

    def fill_null_values(self, model_cls=None):
        return super(ItemSingularView, self).fill_null_values(
            model_cls=self._singular_model)

    def convert_ids2objects(self, model_cls=None):
        return super(ItemSingularView, self).convert_ids2objects(
            model_cls=self._singular_model)

    def show(self, **kwargs):
        parent_obj = self.get_item(**kwargs)
        return getattr(parent_obj, self.attr)

    def create(self, **kwargs):
        parent_obj = self.get_item(**kwargs)
        obj = self._singular_model(**self._json_params)
        obj = obj.save(refresh_index=self.refresh_index)
        parent_obj.update({self.attr: obj}, refresh_index=self.refresh_index)
        return JHTTPCreated(
            resource=getattr(parent_obj, self.attr),
            encoder=self._json_encoder,
            request=self.request)

    def update(self, **kwargs):
        parent_obj = self.get_item(**kwargs)
        obj = getattr(parent_obj, self.attr)
        obj.update(self._json_params, refresh_index=self.refresh_index)
        return JHTTPOk('Updated', location=self.request.url)

    def replace(self, **kwargs):
        return self.update(**kwargs)

    def delete(self, **kwargs):
        parent_obj = self.get_item(**kwargs)
        obj = getattr(parent_obj, self.attr)
        obj.delete(refresh_index=self.refresh_index)
        return JHTTPOk('Deleted')


def generate_rest_view(model_cls, attrs=None, es_based=True,
                       attr_view=False, singular=False):
    """ Generate REST view for a model class.

    Arguments:
        :model_cls: Generated DB model class.
        :attr: List of strings that represent names of view methods, new
            generated view should support. Not supported methods are replaced
            with property that raises AttributeError to display MethodNotAllowed
            error.
        :es_based: Boolean indicating if generated view should read from
            elasticsearch. If True - collection reads are performed from
            elasticsearch; database is used for reads instead. Defaults to True.
        :attr_view: Boolean indicating if ItemAttributeView should be used as a
            base class for generated view.
        :singular: Boolean indicating if ItemSingularView should be used as a
            base class for generated view.
    """
    valid_attrs = (list(collection_methods.values()) +
                   list(item_methods.values()))
    missing_attrs = set(valid_attrs) - set(attrs)

    if singular:
        base_view_cls = ItemSingularView
    elif attr_view:
        base_view_cls = ItemAttributeView
    elif es_based:
        base_view_cls = ESCollectionView
    else:
        base_view_cls = CollectionView

    def _attr_error(*args, **kwargs):
        raise AttributeError

    class RESTView(base_view_cls):
        _json_encoder = engine.JSONEncoder
        _model_class = model_cls

    for attr in missing_attrs:
        setattr(RESTView, attr, property(_attr_error))

    return RESTView
