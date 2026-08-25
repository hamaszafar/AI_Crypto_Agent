from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.storage.models import StoredCandle
from app.storage.repositories.memory_candle_repository import (
    InMemoryCandleRepository,
)


def make_candle(
    timestamp: datetime,
    exchange: str = "binance",
    symbol: str = "BTC/USDT",
    timeframe: str = "15m",
    close: str = "105",
) -> StoredCandle:
    return StoredCandle(
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp,
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal(close),
        volume=Decimal("1000"),
    )


def test_repository_starts_empty():
    repository = InMemoryCandleRepository()

    assert repository.count_candles(
        "binance",
        "BTC/USDT",
        "15m",
    ) == 0


def test_save_single_candle():
    repository = InMemoryCandleRepository()

    candle = make_candle(
        datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
    )

    repository.save_candle(candle)

    candles = repository.get_candles(
        "binance",
        "BTC/USDT",
        "15m",
    )

    assert candles == [candle]


def test_save_multiple_candles():
    repository = InMemoryCandleRepository()

    candles = [
        make_candle(
            datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
        ),
        make_candle(
            datetime(2026, 8, 22, 12, 15, tzinfo=timezone.utc)
        ),
        make_candle(
            datetime(2026, 8, 22, 12, 30, tzinfo=timezone.utc)
        ),
    ]

    repository.save_candles(candles)

    assert repository.count_candles(
        "binance",
        "BTC/USDT",
        "15m",
    ) == 3


def test_candles_are_returned_chronologically():
    repository = InMemoryCandleRepository()

    latest = make_candle(
        datetime(2026, 8, 22, 12, 30, tzinfo=timezone.utc)
    )

    earliest = make_candle(
        datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
    )

    middle = make_candle(
        datetime(2026, 8, 22, 12, 15, tzinfo=timezone.utc)
    )

    repository.save_candles(
        [latest, earliest, middle]
    )

    candles = repository.get_candles(
        "binance",
        "BTC/USDT",
        "15m",
    )

    assert candles == [
        earliest,
        middle,
        latest,
    ]


def test_get_candles_filters_by_exchange():
    repository = InMemoryCandleRepository()

    binance = make_candle(
        datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
        exchange="binance",
    )

    bybit = make_candle(
        datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
        exchange="bybit",
    )

    repository.save_candles([binance, bybit])

    candles = repository.get_candles(
        "binance",
        "BTC/USDT",
        "15m",
    )

    assert candles == [binance]


def test_get_candles_filters_by_symbol():
    repository = InMemoryCandleRepository()

    btc = make_candle(
        datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
        symbol="BTC/USDT",
    )

    eth = make_candle(
        datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
        symbol="ETH/USDT",
    )

    repository.save_candles([btc, eth])

    candles = repository.get_candles(
        "binance",
        "BTC/USDT",
        "15m",
    )

    assert candles == [btc]


def test_get_candles_filters_by_time_range():
    repository = InMemoryCandleRepository()

    candles = [
        make_candle(
            datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
        ),
        make_candle(
            datetime(2026, 8, 22, 12, 15, tzinfo=timezone.utc)
        ),
        make_candle(
            datetime(2026, 8, 22, 12, 30, tzinfo=timezone.utc)
        ),
    ]

    repository.save_candles(candles)

    result = repository.get_candles(
        "binance",
        "BTC/USDT",
        "15m",
        start_time=datetime(
            2026,
            8,
            22,
            12,
            15,
            tzinfo=timezone.utc,
        ),
        end_time=datetime(
            2026,
            8,
            22,
            12,
            30,
            tzinfo=timezone.utc,
        ),
    )

    assert result == candles[1:]


def test_limit_restricts_results():
    repository = InMemoryCandleRepository()

    candles = [
        make_candle(
            datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
        ),
        make_candle(
            datetime(2026, 8, 22, 12, 15, tzinfo=timezone.utc)
        ),
        make_candle(
            datetime(2026, 8, 22, 12, 30, tzinfo=timezone.utc)
        ),
    ]

    repository.save_candles(candles)

    result = repository.get_candles(
        "binance",
        "BTC/USDT",
        "15m",
        limit=2,
    )

    assert result == candles[:2]


def test_negative_limit_is_rejected():
    repository = InMemoryCandleRepository()

    with pytest.raises(ValueError):
        repository.get_candles(
            "binance",
            "BTC/USDT",
            "15m",
            limit=-1,
        )


def test_get_latest_candle():
    repository = InMemoryCandleRepository()

    first = make_candle(
        datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
    )

    latest = make_candle(
        datetime(2026, 8, 22, 12, 30, tzinfo=timezone.utc)
    )

    repository.save_candles([latest, first])

    result = repository.get_latest_candle(
        "binance",
        "BTC/USDT",
        "15m",
    )

    assert result == latest


def test_latest_candle_returns_none_when_empty():
    repository = InMemoryCandleRepository()

    result = repository.get_latest_candle(
        "binance",
        "BTC/USDT",
        "15m",
    )

    assert result is None


def test_duplicate_candle_is_replaced():
    repository = InMemoryCandleRepository()

    timestamp = datetime(
        2026,
        8,
        22,
        12,
        0,
        tzinfo=timezone.utc,
    )

    original = make_candle(
        timestamp,
        close="105",
    )

    updated = make_candle(
        timestamp,
        close="110",
    )

    repository.save_candle(original)
    repository.save_candle(updated)

    candles = repository.get_candles(
        "binance",
        "BTC/USDT",
        "15m",
    )

    assert len(candles) == 1
    assert candles[0].close == Decimal("110")


def test_different_timeframes_are_stored_separately():
    repository = InMemoryCandleRepository()

    candle_15m = make_candle(
        datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
        timeframe="15m",
    )

    candle_1h = make_candle(
        datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
        timeframe="1h",
    )

    repository.save_candles(
        [candle_15m, candle_1h]
    )

    assert repository.count_candles(
        "binance",
        "BTC/USDT",
        "15m",
    ) == 1

    assert repository.count_candles(
        "binance",
        "BTC/USDT",
        "1h",
    ) == 1