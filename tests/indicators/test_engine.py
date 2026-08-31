from datetime import datetime, timezone
from decimal import Decimal
import pytest

from app.indicators.base import BaseIndicator
from app.indicators.engine import IndicatorEngine
from app.indicators.input import IndicatorInput, IndicatorCandle
from app.indicators.models import IndicatorMetadata, IndicatorResult

class MockIndicator(BaseIndicator):
    def __init__(self, period: int = 2):
        self._period = period

    @property
    def metadata(self) -> IndicatorMetadata:
        return IndicatorMetadata(
            name=f"MOCK{self._period}",
            description="Mock indicator",
            minimum_period=self._period
        )

    def calculate(self, data: IndicatorInput) -> IndicatorResult:
        return IndicatorResult(
            indicator_name=self.metadata.name,
            timestamp=data.latest.timestamp,
            values={"value": Decimal("42")}
        )

def make_input(size: int) -> IndicatorInput:
    candles = []
    for i in range(size):
        candles.append(IndicatorCandle(
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            open=Decimal("10"),
            high=Decimal("15"),
            low=Decimal("9"),
            close=Decimal("11"),
            volume=Decimal("100")
        ))
    return IndicatorInput(exchange="test", symbol="BTC/USDT", timeframe="1h", candles=tuple(candles))

def test_engine_initialization():
    engine = IndicatorEngine([MockIndicator()])
    assert len(engine.indicators) == 1

def test_engine_requires_indicators():
    with pytest.raises(ValueError):
        IndicatorEngine([])

def test_engine_calculate_all():
    engine = IndicatorEngine([MockIndicator(period=1)])
    data = make_input(1)
    
    results = engine.calculate_all(data)
    assert "MOCK1" in results
    assert results["MOCK1"].get("value") == Decimal("42")

def test_engine_insufficient_data():
    engine = IndicatorEngine([MockIndicator(period=10)])
    data = make_input(5)
    
    with pytest.raises(ValueError, match="Insufficient data"):
        engine.calculate_all(data)

def test_engine_empty_data():
    engine = IndicatorEngine([MockIndicator(period=1)])
    data = make_input(0)
    
    with pytest.raises(ValueError, match="cannot be empty"):
        engine.calculate_all(data)
