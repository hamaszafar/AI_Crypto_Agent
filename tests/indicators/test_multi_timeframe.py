from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.indicators.multi_timeframe import (
    MultiTimeframeInput,
    MultiTimeframePipeline,
)
from app.indicators.pipeline import IndicatorInputPipeline
from app.market_data.historical import HistoricalMarketData
from app.storage.models import StoredCandle
from app.storage.repositories.memory_candle_repository import (
    InMemoryCandleRepository,
)


def make_candle(
    timeframe: str,
    timestamp: datetime,
) -> StoredCandle:
    return StoredCandle(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe=timeframe,
        timestamp=timestamp,
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
        volume=Decimal("1000"),
    )


@pytest.fixture
def pipeline() -> MultiTimeframePipeline:
    repository = InMemoryCandleRepository()
    historical = HistoricalMarketData(repository)
    indicator_pipeline = IndicatorInputPipeline(historical)

    base = datetime(2026, 1, 1)

    for timeframe in ("15m", "1h", "4h", "1d"):
        historical.save_candles(
            [
                make_candle(timeframe, base),
                make_candle(
                    timeframe,
                    base + timedelta(hours=1),
                ),
                make_candle(
                    timeframe,
                    base + timedelta(hours=2),
                ),
            ]
        )

    return MultiTimeframePipeline(indicator_pipeline)


def test_build_all_timeframes(pipeline):
    result = pipeline.build(
        exchange="binance",
        symbol="BTC/USDT",
    )

    assert isinstance(result, MultiTimeframeInput)

    assert result.exchange == "binance"
    assert result.symbol == "BTC/USDT"

    assert result.timeframe_15m is not None
    assert result.timeframe_1h is not None
    assert result.timeframe_4h is not None
    assert result.timeframe_1d is not None


def test_available_timeframes(pipeline):
    result = pipeline.build(
        exchange="binance",
        symbol="BTC/USDT",
    )

    assert result.available_timeframes == (
        "15m",
        "1h",
        "4h",
        "1d",
    )


def test_complete_input(pipeline):
    result = pipeline.build(
        exchange="binance",
        symbol="BTC/USDT",
    )

    assert result.is_complete


def test_build_selected_timeframes(pipeline):
    result = pipeline.build(
        exchange="binance",
        symbol="BTC/USDT",
        timeframes=("15m", "1h"),
    )

    assert result.timeframe_15m is not None
    assert result.timeframe_1h is not None

    assert result.timeframe_4h is None
    assert result.timeframe_1d is None

    assert result.available_timeframes == (
        "15m",
        "1h",
    )

    assert not result.is_complete


def test_timeframe_data_is_correct(pipeline):
    result = pipeline.build(
        exchange="binance",
        symbol="BTC/USDT",
        timeframes=("1h",),
    )

    assert result.timeframe_1h is not None

    assert result.timeframe_1h.timeframe == "1h"
    assert result.timeframe_1h.size == 3


def test_invalid_timeframe(pipeline):
    with pytest.raises(
        ValueError,
        match="Unsupported timeframe",
    ):
        pipeline.build(
            exchange="binance",
            symbol="BTC/USDT",
            timeframes=("5m",),
        )


def test_multiple_invalid_timeframes(pipeline):
    with pytest.raises(
        ValueError,
        match="Unsupported timeframe",
    ):
        pipeline.build(
            exchange="binance",
            symbol="BTC/USDT",
            timeframes=("5m", "30m"),
        )


def test_time_range_is_forwarded(pipeline):
    base = datetime(2026, 1, 1)

    result = pipeline.build(
        exchange="binance",
        symbol="BTC/USDT",
        start_time=base + timedelta(hours=1),
        timeframes=("1h",),
    )

    assert result.timeframe_1h is not None
    assert result.timeframe_1h.size == 2


def test_limit_is_forwarded(pipeline):
    result = pipeline.build(
        exchange="binance",
        symbol="BTC/USDT",
        limit=2,
        timeframes=("15m", "1h"),
    )

    assert result.timeframe_15m is not None
    assert result.timeframe_1h is not None

    assert result.timeframe_15m.size == 2
    assert result.timeframe_1h.size == 2


def test_empty_multitimeframe_input():
    result = MultiTimeframeInput(
        exchange="binance",
        symbol="BTC/USDT",
    )

    assert result.available_timeframes == ()
    assert not result.is_complete