from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.market_data.historical import HistoricalMarketData
from app.storage.models import StoredCandle
from app.storage.repositories.memory_candle_repository import (
    InMemoryCandleRepository,
)


def make_candle(
    timestamp: datetime,
    exchange: str = "binance",
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
) -> StoredCandle:
    return StoredCandle(
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp,
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
        volume=Decimal("1000"),
    )


@pytest.fixture
def historical():
    repository = InMemoryCandleRepository()
    return HistoricalMarketData(repository)


def test_save_and_get_history(historical):
    base = datetime(2026, 1, 1, 0, 0)

    candles = [
        make_candle(base),
        make_candle(base + timedelta(hours=1)),
        make_candle(base + timedelta(hours=2)),
    ]

    historical.save_candles(candles)

    result = historical.get_history(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
    )

    assert len(result) == 3
    assert result[0].timestamp == base
    assert result[-1].timestamp == base + timedelta(hours=2)


def test_get_history_with_time_range(historical):
    base = datetime(2026, 1, 1, 0, 0)

    candles = [
        make_candle(base),
        make_candle(base + timedelta(hours=1)),
        make_candle(base + timedelta(hours=2)),
        make_candle(base + timedelta(hours=3)),
    ]

    historical.save_candles(candles)

    result = historical.get_history(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_time=base + timedelta(hours=1),
        end_time=base + timedelta(hours=2),
    )

    assert len(result) == 2
    assert result[0].timestamp == base + timedelta(hours=1)
    assert result[1].timestamp == base + timedelta(hours=2)


def test_get_latest(historical):
    base = datetime(2026, 1, 1, 0, 0)

    historical.save_candles(
        [
            make_candle(base),
            make_candle(base + timedelta(hours=1)),
            make_candle(base + timedelta(hours=2)),
        ]
    )

    latest = historical.get_latest(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
    )

    assert latest is not None
    assert latest.timestamp == base + timedelta(hours=2)


def test_get_latest_when_empty(historical):
    latest = historical.get_latest(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
    )

    assert latest is None


def test_count(historical):
    base = datetime(2026, 1, 1, 0, 0)

    historical.save_candles(
        [
            make_candle(base),
            make_candle(base + timedelta(hours=1)),
            make_candle(
                base + timedelta(hours=2),
                symbol="ETH/USDT",
            ),
        ]
    )

    assert historical.count() == 3
    assert historical.count(exchange="binance") == 3
    assert historical.count(symbol="BTC/USDT") == 2
    assert historical.count(symbol="ETH/USDT") == 1


def test_invalid_time_range_raises(historical):
    start = datetime(2026, 1, 2)
    end = datetime(2026, 1, 1)

    with pytest.raises(ValueError, match="start_time"):
        historical.get_history(
            exchange="binance",
            symbol="BTC/USDT",
            timeframe="1h",
            start_time=start,
            end_time=end,
        )


def test_negative_limit_raises(historical):
    with pytest.raises(ValueError, match="limit"):
        historical.get_history(
            exchange="binance",
            symbol="BTC/USDT",
            timeframe="1h",
            limit=-1,
        )


def test_duplicate_candle_is_replaced(historical):
    timestamp = datetime(2026, 1, 1)

    first = make_candle(timestamp)
    second = StoredCandle(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        timestamp=timestamp,
        open=Decimal("200"),
        high=Decimal("220"),
        low=Decimal("190"),
        close=Decimal("210"),
        volume=Decimal("2000"),
    )

    historical.save_candle(first)
    historical.save_candle(second)

    result = historical.get_history(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
    )

    assert len(result) == 1
    assert result[0].close == Decimal("210")
    assert result[0].volume == Decimal("2000")