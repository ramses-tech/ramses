"""
Naive registry that is just a subclass of a python dictionary.
It is meant to be used to store objects and retrieve them when needed.
The registry is recreated on each app launch and is best suited to store some
dynamic or short-term data.

Storing an object should be performed by using the `add` function, and
retrieving it by using the `get` function.


Examples:

Register a function under a function name::

    from ramses import registry

    @registry.add
    def foo():
        print 'In foo'

    assert registry.get('foo') is foo


Register a function under a different name::

    from ramses import registry

    @registry.add('bar')
    def foo():
        print 'In foo'

    assert registry.get('bar') is foo


Register an arbitrary object::

    from ramses import registry

    myvar = 'my awesome var'
    registry.add('my_stored_var', myvar)
    assert registry.get('my_stored_var') == myvar


Register and get an object by namespace::

    from ramses import registry

    myvar = 'my awesome var'
    registry.add('Foo.my_stored_var', myvar)
    assert registry.mget('Foo') == {'my_stored_var': myvar}

"""
import six


class Registry(dict):
    pass


registry = Registry()


def add(*args):
    def decorator(function):
        registry[name] = function
        return function

    if len(args) == 1 and six.callable(args[0]):
        function = args[0]
        name = function.__name__
        return decorator(function)
    elif len(args) == 2:
        registry[args[0]] = args[1]
    else:
        name = args[0]
        return decorator


def get(name):
    try:
        return registry[name]
    except KeyError:
        raise KeyError(
            "Object named '{}' is not registered in ramses "
            "registry".format(name))


def mget(namespace):
    namespace = namespace.lower() + '.'
    data = {}
    for key, val in registry.items():
        key = key.lower()
        if not key.startswith(namespace):
            continue
        clean_key = key.split(namespace)[-1]
        data[clean_key] = val
    return data
