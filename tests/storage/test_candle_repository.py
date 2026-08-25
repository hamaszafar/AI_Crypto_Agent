from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.storage.models import StoredCandle
from app.storage.repositories.memory_candle_repository import (
    InMemoryCandleRepository,
)


def candle(
    hour: int,
    minute: int = 0,
    exchange: str = "binance",
    symbol: str = "BTC/USDT",
    timeframe: str = "15m",
    close: str = "105",
) -> StoredCandle:

    return StoredCandle(
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        timestamp=datetime(
            2026,
            8,
            22,
            hour,
            minute,
            tzinfo=timezone.utc,
        ),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal(close),
        volume=Decimal("1000"),
    )


def test_repository_starts_empty():
    repo = InMemoryCandleRepository()

    assert repo.count_candles(
        "binance",
        "BTC/USDT",
        "15m",
    ) == 0


def test_save_candle():
    repo = InMemoryCandleRepository()
    item = candle(12)

    repo.save_candle(item)

    assert repo.get_candles(
        "binance",
        "BTC/USDT",
        "15m",
    ) == [item]


def test_save_multiple_candles():
    repo = InMemoryCandleRepository()

    items = [
        candle(12, 0),
        candle(12, 15),
        candle(12, 30),
    ]

    repo.save_candles(items)

    assert repo.count_candles(
        "binance",
        "BTC/USDT",
        "15m",
    ) == 3


def test_results_are_chronological():
    repo = InMemoryCandleRepository()

    latest = candle(12, 30)
    first = candle(12, 0)
    middle = candle(12, 15)

    repo.save_candles([latest, first, middle])

    result = repo.get_candles(
        "binance",
        "BTC/USDT",
        "15m",
    )

    assert result == [first, middle, latest]


def test_filters_exchange():
    repo = InMemoryCandleRepository()

    binance = candle(12, exchange="binance")
    bybit = candle(12, exchange="bybit")

    repo.save_candles([binance, bybit])

    result = repo.get_candles(
        "binance",
        "BTC/USDT",
        "15m",
    )

    assert result == [binance]


def test_filters_symbol():
    repo = InMemoryCandleRepository()

    btc = candle(12, symbol="BTC/USDT")
    eth = candle(12, symbol="ETH/USDT")

    repo.save_candles([btc, eth])

    result = repo.get_candles(
        "binance",
        "BTC/USDT",
        "15m",
    )

    assert result == [btc]


def test_filters_time_range():
    repo = InMemoryCandleRepository()

    first = candle(12, 0)
    middle = candle(12, 15)
    latest = candle(12, 30)

    repo.save_candles([first, middle, latest])

    result = repo.get_candles(
        "binance",
        "BTC/USDT",
        "15m",
        start_time=middle.timestamp,
        end_time=latest.timestamp,
    )

    assert result == [middle, latest]


def test_limit():
    repo = InMemoryCandleRepository()

    items = [
        candle(12, 0),
        candle(12, 15),
        candle(12, 30),
    ]

    repo.save_candles(items)

    result = repo.get_candles(
        "binance",
        "BTC/USDT",
        "15m",
        limit=2,
    )

    assert result == items[:2]


def test_negative_limit_rejected():
    repo = InMemoryCandleRepository()

    with pytest.raises(ValueError):
        repo.get_candles(
            "binance",
            "BTC/USDT",
            "15m",
            limit=-1,
        )


def test_latest_candle():
    repo = InMemoryCandleRepository()

    first = candle(12, 0)
    latest = candle(12, 30)

    repo.save_candles([latest, first])

    assert repo.get_latest_candle(
        "binance",
        "BTC/USDT",
        "15m",
    ) == latest


def test_latest_candle_empty():
    repo = InMemoryCandleRepository()

    assert repo.get_latest_candle(
        "binance",
        "BTC/USDT",
        "15m",
    ) is None


def test_duplicate_replaces_existing():
    repo = InMemoryCandleRepository()

    original = candle(12, close="105")
    updated = candle(12, close="110")

    repo.save_candle(original)
    repo.save_candle(updated)

    result = repo.get_candles(
        "binance",
        "BTC/USDT",
        "15m",
    )

    assert len(result) == 1
    assert result[0].close == Decimal("110")


def test_timeframes_are_separate():
    repo = InMemoryCandleRepository()

    fifteen = candle(12, timeframe="15m")
    hourly = candle(12, timeframe="1h")

    repo.save_candles([fifteen, hourly])

    assert repo.count_candles(
        "binance",
        "BTC/USDT",
        "15m",
    ) == 1

    assert repo.count_candles(
        "binance",
        "BTC/USDT",
        "1h",
    ) == 1