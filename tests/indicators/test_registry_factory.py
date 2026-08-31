import pytest
from app.indicators.base import BaseIndicator
from app.indicators.registry import IndicatorRegistry
from app.indicators.factory import IndicatorFactory

class DummyIndicator(BaseIndicator):
    @property
    def metadata(self):
        pass
    def calculate(self, data):
        pass

def test_registry_register_and_get():
    IndicatorRegistry.clear()
    IndicatorRegistry.register("dummy", DummyIndicator)
    assert IndicatorRegistry.get("dummy") is DummyIndicator

def test_registry_register_duplicate():
    IndicatorRegistry.clear()
    IndicatorRegistry.register("dummy", DummyIndicator)
    with pytest.raises(ValueError, match="already registered"):
        IndicatorRegistry.register("dummy", DummyIndicator)

def test_registry_get_unknown():
    IndicatorRegistry.clear()
    with pytest.raises(ValueError, match="not found"):
        IndicatorRegistry.get("unknown")

def test_factory_create():
    IndicatorRegistry.clear()
    IndicatorRegistry.register("dummy", DummyIndicator)
    instance = IndicatorFactory.create("dummy")
    assert isinstance(instance, DummyIndicator)
