import pytest


@pytest.fixture
def clear_registry(request):
    from ramses import registry
    registry.registry.clear()
