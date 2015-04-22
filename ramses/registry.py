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
