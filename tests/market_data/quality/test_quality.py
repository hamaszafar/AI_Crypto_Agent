from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest

from app.market_data.exceptions import DuplicateCandleError, CandleGapError
from app.market_data.models import MarketCandle
from app.market_data.quality.models import (
    DataQualityStatus,
    NormalizationConfig,
)
from app.market_data.quality.pipeline import DataQualityPipeline


def make_candle(exchange: str, ts: datetime, close: str = "50000") -> MarketCandle:
    return MarketCandle(
        exchange=exchange,
        symbol="BTC/USDT",
        timeframe="15m",
        timestamp=ts,
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal(close),
        volume=Decimal("10"),
    )


def test_quality_pipeline_clean():
    now = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)
    pipeline = DataQualityPipeline(clock=lambda: now)

    c1 = make_candle("binance", now - timedelta(minutes=30))
    c2 = make_candle("binance", now - timedelta(minutes=15))

    clean, result = pipeline.process([c2, c1])  # unsorted input
    assert len(clean) == 2
    assert clean[0].timestamp < clean[1].timestamp  # sorted
    assert result.status == DataQualityStatus.VALID
    assert result.is_valid is True


def test_quality_pipeline_duplicates():
    now = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)
    c1 = make_candle("binance", now - timedelta(minutes=15))

    pipeline_retain = DataQualityPipeline(clock=lambda: now)
    clean, result = pipeline_retain.process([c1, c1])
    assert len(clean) == 1
    assert result.duplicate_count == 1
    assert result.status == DataQualityStatus.WARNING

    strict_config = NormalizationConfig(duplicate_policy="strict")
    pipeline_strict = DataQualityPipeline(config=strict_config, clock=lambda: now)
    with pytest.raises(DuplicateCandleError):
        pipeline_strict.process([c1, c1])


def test_quality_pipeline_future_timestamp():
    now = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)
    c_future = make_candle("binance", now + timedelta(minutes=10))

    pipeline = DataQualityPipeline(clock=lambda: now)
    clean, result = pipeline.process([c_future])
    assert result.future_timestamp_detected is True
    assert result.is_valid is False
    assert result.status == DataQualityStatus.INVALID


def test_quality_pipeline_stale_data():
    now = datetime(2026, 8, 26, 12, 0, tzinfo=timezone.utc)
    c_old = make_candle("binance", now - timedelta(days=5))

    pipeline = DataQualityPipeline(clock=lambda: now)
    clean, result = pipeline.process([c_old])
    assert result.stale is True
    assert result.status == DataQualityStatus.WARNING
