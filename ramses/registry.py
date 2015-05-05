"""
Naive registry that is just a subclass of python dict.
Is meant to be used to store object and retrieve when needed.
Registry is recreated on each app launch and best fits to store some
dynamic or short-term data.

Storing should be performed using `add` function and retrieving using
`get` function.


Examples:

Register a function under function name::

    from ramses import registry

    @registry.add
    def foo():
        print 'In foo'

    assert registry.get('foo') is foo


Register a function under different name::

    from ramses import registry

    @registry.add('bar')
    def foo():
        print 'In foo'

    assert registry.get('bar') is foo


Register arbitrary object::

    from ramses import registry

    myvar = 'my awesome var'
    registry.add('my_stored_var', myvar)
    assert registry.get('my_stored_var') == myvar


Register and get object by namespace::

    from ramses import registry

    myvar = 'my awesome var'
    registry.add('Foo.my_stored_var', myvar)
    assert registry.mget('Foo') == {'my_stored_var': myvar}

"""


class Registry(dict):
    pass


registry = Registry()


def add(*args):
    def decorator(function):
        registry[name] = function
        return function

    if len(args) == 1 and callable(args[0]):
        function = args[0]
        name = function.func_name
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
