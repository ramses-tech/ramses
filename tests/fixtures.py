import pytest


@pytest.fixture
def clear_registry(request):
    from ramses import registry
    registry.registry.clear()


@pytest.fixture
def engine_mock(request):
    import nefertari
    from mock import Mock

    class BaseDocument(object):
        pass

    class ESBaseDocument(object):
        pass

    original_engine = nefertari.engine
    nefertari.engine = Mock()
    nefertari.engine.BaseDocument = BaseDocument
    nefertari.engine.ESBaseDocument = ESBaseDocument

    def clear():
        nefertari.engine = original_engine
    request.addfinalizer(clear)

    return nefertari.engine


@pytest.fixture
def guards_engine_mock(request):
    import nefertari_guards
    from nefertari_guards import engine
    from mock import Mock

    class DocumentACLMixin(object):
        pass

    original_engine = engine
    nefertari_guards.engine = Mock()
    nefertari_guards.engine.DocumentACLMixin = DocumentACLMixin

    def clear():
        nefertari_guards.engine = original_engine
    request.addfinalizer(clear)

    return nefertari_guards.engine


def config_mock():
    from mock import Mock
    config = Mock()
    config.registry.database_acls = False
    return config
