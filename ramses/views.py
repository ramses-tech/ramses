class BaseView(object):
    def __init__(self, request):
        self.request = request
        self.storage = request.registry.storage
        self.args = filter(bool, request.path.split('/'))


class RESTView(BaseView):
    def get(self):
        try:
            data = self.storage.get(*self.args)
            return {"status": "success", "data": data}
        except Exception as ex:
            return {"status": "error", "error": str(ex)}

    def post(self):
        try:
            item = self.storage.add_item(
                *self.args, item=self.request.json)
            return {"status": "created", "data": item}
        except Exception as ex:
            return {"status": "error", "error": str(ex)}

    def delete(self):
        try:
            self.storage.delete_item(
                *self.args, id_=self.request.json['id'])
            return {"status": "deleted"}
        except Exception as ex:
            return {"status": "error", "error": str(ex)}
