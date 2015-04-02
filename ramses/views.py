from nefertari.view import BaseView as NefertariBaseView
from nefertari.json_httpexceptions import (
    JHTTPCreated, JHTTPOk)

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
    'put':      'update',
    'patch':    'update',
    'delete':   'delete',
}


class BaseView(NefertariBaseView):
    """ Base view class that defines provides generic implementation
    for handling every supported HTTP method requests.

    """
    def __init__(self, *args, **kwargs):
        super(BaseView, self).__init__(*args, **kwargs)
        if self.request.method == 'GET':
            self._params.process_int_param('_limit', 20)

    def _location(self, obj):
        """ Get location of the `obj`

        Arguments:
            :obj: self._model_class instance.
        """
        id_name = self._resource.id_name or 'id'
        return self.request.route_url(
            self._resource.uid,
            **{id_name: getattr(obj, id_name)})

    def index(self):
        return self._model_class.get_collection(**self._params)

    def show(self, **kwargs):
        return self.context

    def create(self):
        obj = self._model_class(**self._params).save()
        return JHTTPCreated(
            location=self._location(obj),
            resource=obj.to_dict(request=self.request))

    def update(self, **kwargs):
        obj = self._model_class.get_resource(**kwargs)
        obj.update(self._params)
        return JHTTPOk('Updated', location=self._location(obj))

    def delete(self, **kwargs):
        self._model_class._delete(**kwargs)
        return JHTTPOk('Deleted')

    def delete_many(self):
        objects = self._model_class.get_collection(**self._params)
        count = objects.count()

        if self.needs_confirmation():
            return objects

        self._model_class._delete_many(objects)
        return JHTTPOk('Deleted %s %s(s) objects' % (
            count, self._model_class.__name__))

    def update_many(self):
        _limit = self._params.pop('_limit', None)
        objects = self._model_class.get_collection(_limit=_limit)
        self._model_class._update_many(objects, **self._params)
        return JHTTPOk('Updated %s %s(s) objects' % (
            objects.count(), self._model_class.__name__))


class ESBaseView(BaseView):
    """ Elasticsearch based view. Does collection reads from ES.

    """
    def index(self):
        from nefertari.elasticsearch import ES
        search_params = []
        if 'q' in self._params:
            search_params.append(self._params.pop('q'))
        self._raw_terms = ' AND '.join(search_params)

        return ES(self._model_class.__name__).get_collection(
            _raw_terms=self._raw_terms, **self._params)


def generate_rest_view(model_cls, attrs=None, es_based=True):
    """ Generate REST view for model class.

    Arguments:
        :model_cls: Generated DB model class.
        :attr: List of strings that represent names of view methods, new
            generated view should support. Not supported methods are replaced
            with property that raises AttributeError to display MethodNotAllowed
            error.
        :es_based: Boolean indicating if generated view should read from
            elasticsearch. If True - collection reads are performed from
            elasticsearch; database is used for reads instead. Defaults to True.
    """
    from nefertari.engine import JSONEncoder
    valid_attrs = collection_methods.values() + item_methods.values()
    missing_attrs = set(valid_attrs) - set(attrs)
    base_view_cls = ESBaseView if es_based else BaseView

    def _attr_error(*args, **kwargs):
        raise AttributeError

    class RESTView(base_view_cls):
        _json_encoder = JSONEncoder
        _model_class = model_cls

    for attr in missing_attrs:
        setattr(RESTView, attr, property(_attr_error))

    return RESTView
