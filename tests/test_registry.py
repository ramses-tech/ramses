import pytest

from .fixtures import clear_registry
from ramses import registry


@pytest.mark.usefixtures('clear_registry')
class TestRegistry(object):

    def test_add_decorator(self):
        @registry.add
        def foo(*args, **kwargs):
            return args, kwargs

        assert registry.registry['foo'] is foo
        assert list(registry.registry.keys()) == ['foo']

    def test_add_decorator_with_name(self):
        @registry.add('bar')
        def foo(*args, **kwargs):
            return args, kwargs

        assert registry.registry['bar'] is foo
        assert list(registry.registry.keys()) == ['bar']

    def test_add_arbitrary_object(self):
        registry.add('foo', 1)
        registry.add('bar', 2)

        assert registry.registry['foo'] == 1
        assert registry.registry['bar'] == 2
        assert sorted(registry.registry.keys()) == ['bar', 'foo']

    def test_get(self):
        registry.registry['foo'] = 1
        assert registry.get('foo') == 1

    def test_get_error(self):
        assert not list(registry.registry.keys())
        with pytest.raises(KeyError) as ex:
            registry.get('foo')
        assert 'is not registered in ramses registry' in str(ex.value)

    def test_mget(self):
        registry.registry['Foo.bar'] = 1
        registry.registry['Foo.zoo'] = 2
        assert registry.mget('FoO') == {'bar': 1, 'zoo': 2}

    def test_mget_not_existing(self):
        registry.registry['Foo.bar'] = 1
        registry.registry['Foo.zoo'] = 2
        assert registry.mget('asdasdasd') == {}
