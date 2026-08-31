from decimal import Decimal
from datetime import datetime, timezone
import pytest
from app.indicators.models import IndicatorMetadata, IndicatorResult

def test_indicator_metadata():
    meta = IndicatorMetadata(name="SMA", description="Simple Moving Average", minimum_period=14)
    assert meta.name == "SMA"
    assert meta.description == "Simple Moving Average"
    assert meta.minimum_period == 14

def test_indicator_result():
    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    result = IndicatorResult(
        indicator_name="SMA",
        timestamp=timestamp,
        values={"sma": Decimal("100.5")}
    )
    
    assert result.indicator_name == "SMA"
    assert result.timestamp == timestamp
    assert result.get("sma") == Decimal("100.5")

def test_indicator_result_missing_key():
    timestamp = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    result = IndicatorResult(
        indicator_name="SMA",
        timestamp=timestamp,
        values={"sma": Decimal("100.5")}
    )
    
    with pytest.raises(KeyError):
        result.get("unknown")
