from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.indicators.input import IndicatorCandle, IndicatorInput
from app.indicators.pipeline import IndicatorInputPipeline
from app.market_data.historical import HistoricalMarketData
from app.storage.models import StoredCandle
from app.storage.repositories.memory_candle_repository import (
    InMemoryCandleRepository,
)


def make_candle(
    timestamp: datetime,
    close: str = "105",
) -> StoredCandle:
    return StoredCandle(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        timestamp=timestamp,
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal(close),
        volume=Decimal("1000"),
    )


@pytest.fixture
def pipeline() -> IndicatorInputPipeline:
    repository = InMemoryCandleRepository()
    historical = HistoricalMarketData(repository)

    base = datetime(2026, 1, 1)

    historical.save_candles(
        [
            make_candle(base, "105"),
            make_candle(base + timedelta(hours=1), "106"),
            make_candle(base + timedelta(hours=2), "107"),
        ]
    )

    return IndicatorInputPipeline(historical)


def test_build_indicator_input(pipeline):
    result = pipeline.build(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
    )

    assert isinstance(result, IndicatorInput)
    assert result.exchange == "binance"
    assert result.symbol == "BTC/USDT"
    assert result.timeframe == "1h"
    assert result.size == 3


def test_indicator_candles_are_converted(pipeline):
    result = pipeline.build(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
    )

    candle = result.candles[0]

    assert isinstance(candle, IndicatorCandle)
    assert candle.open == Decimal("100")
    assert candle.high == Decimal("110")
    assert candle.low == Decimal("90")
    assert candle.close == Decimal("105")
    assert candle.volume == Decimal("1000")


def test_candles_are_chronological(pipeline):
    result = pipeline.build(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
    )

    timestamps = [
        candle.timestamp
        for candle in result.candles
    ]

    assert timestamps == sorted(timestamps)


def test_latest_candle(pipeline):
    result = pipeline.build(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
    )

    assert result.latest is not None
    assert result.latest.close == Decimal("107")


def test_empty_indicator_input():
    result = IndicatorInput(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        candles=(),
    )

    assert result.size == 0
    assert result.latest is None


def test_has_enough_data(pipeline):
    result = pipeline.build(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
    )

    assert pipeline.has_enough_data(result, 3)
    assert not pipeline.has_enough_data(result, 4)


def test_invalid_minimum_candles(pipeline):
    result = pipeline.build(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
    )

    with pytest.raises(
        ValueError,
        match="minimum_candles",
    ):
        pipeline.has_enough_data(result, 0)


def test_limit_is_forwarded(pipeline):
    result = pipeline.build(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        limit=2,
    )

    assert result.size == 2


def test_time_range_is_forwarded(pipeline):
    base = datetime(2026, 1, 1)

    result = pipeline.build(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_time=base + timedelta(hours=1),
    )

    assert result.size == 2
    assert result.candles[0].timestamp == (
        base + timedelta(hours=1)
    )