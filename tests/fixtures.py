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

    nefertari.engine = Mock()
    nefertari.engine.BaseDocument = BaseDocument
    nefertari.engine.ESBaseDocument = ESBaseDocument
    return nefertari.engine
