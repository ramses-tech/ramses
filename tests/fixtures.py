import pytest


@pytest.fixture
def clear_registry(request):
    from ramses import registry
    registry.registry.clear()


@pytest.fixture(scope='module')
def engine_mock(request):
    import nefertari
    from mock import Mock

    nefertari.engine = Mock()
    nefertari.engine.BaseDocument = object
    return nefertari.engine
