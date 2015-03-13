def _validator(required, _type):
    types = dict(
        string=lambda x: isinstance(x, basestring),
        number=lambda x: isinstance(x, float),
        integer=lambda x: isinstance(x, int),
        boolean=lambda x: isinstance(x, bool),
        date=lambda x: x,
        file=lambda x: x
    )

    def validator(value):
        if required and value is None:
            raise ValueError('Missing required field')
        if _type not in types:
            raise ValueError('Unknown type: {}'.format(_type))
        type_validator = types[_type]
        if value is not None and not type_validator(value):
            raise ValueError('Value has invalid type')
    return validator


class Item(object):
    def __getitem__(self, field):
        return getattr(self, field)

    def __setitem__(self, field, value):
        return setattr(self, field, value)

    def update_from_dict(self, obj):
        for field, value in obj.items():
            self[field] = value

    def __init__(self, obj):
        self.update_from_dict(obj)

    def __json__(self, request):
        return self.__dict__


class DemoStorage(dict):
    def add_model(self, model):
        self[model] = {
            'validators': {},
            'objects': {},
        }

    def _validate_item(self, model, item):
        validators = self[model]['validators']
        invalid_fields = set(item.keys()) - set(validators.keys())
        if invalid_fields:
            raise ValueError('Invalid fields provided: {}'.format(
                invalid_fields))
        for field, validator in validators.items():
            try:
                validator(item.get(field))
            except ValueError as ex:
                raise ValueError('{}: {}'.format(field, ex))

    def setup_schema(self, model, schema):
        validators = self[model]['validators']
        for field, props in schema.items():
            validators[field] = _validator(
                props['required'], props['type'])

    def get_collection(self, model):
        return self[model]['objects'].values()

    def get_item(self, model, id_):
        return self[model]['objects'].get(int(id_))

    def add_item(self, model, item):
        objects = self[model]['objects']
        if 'id' not in item:
            item['id'] = max(objects.keys() + [0]) + 1
        self._validate_item(model, item)
        item['_type'] = model
        item_id = item['id']
        objects[item_id] = Item(item)
        return objects[item_id]

    def delete_item(self, model, id_):
        del self[model]['objects'][int(id_)]

    def update_item(self, model, id_, item):
        self._validate_item(item)
        self[model]['objects'][int(id_)].update_from_dict(item)

    def get(self, *args):
        if len(args) > 1:
            return self.get_item(*args)
        return self.get_collection(*args)
