from datetime import datetime, timezone
from decimal import Decimal

from app.storage.database import SQLiteDatabase
from app.storage.models import StoredCandle
from app.storage.repositories.sqlite_candle_repository import (
    SQLiteCandleRepository,
)


def make_candle(minute: int, close: str = "105") -> StoredCandle:
    return StoredCandle(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
        timestamp=datetime(
            2026,
            8,
            22,
            12,
            minute,
            tzinfo=timezone.utc,
        ),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal(close),
        volume=Decimal("1000"),
    )


def make_repository(tmp_path):
    database = SQLiteDatabase(
        tmp_path / "market_data.db"
    )

    return (
        database,
        SQLiteCandleRepository(database),
    )


def test_save_and_get_candle(tmp_path):
    database, repository = make_repository(tmp_path)

    candle = make_candle(0)

    repository.save_candle(candle)

    result = repository.get_candles(
        "binance",
        "BTC/USDT",
        "15m",
    )

    assert result == [candle]

    database.close()


def test_save_multiple_candles(tmp_path):
    database, repository = make_repository(tmp_path)

    candles = [
        make_candle(0),
        make_candle(15),
        make_candle(30),
    ]

    repository.save_candles(candles)

    assert repository.count_candles(
        "binance",
        "BTC/USDT",
        "15m",
    ) == 3

    database.close()


def test_results_are_chronological(tmp_path):
    database, repository = make_repository(tmp_path)

    latest = make_candle(30)
    first = make_candle(0)
    middle = make_candle(15)

    repository.save_candles(
        [latest, first, middle]
    )

    result = repository.get_candles(
        "binance",
        "BTC/USDT",
        "15m",
    )

    assert result == [
        first,
        middle,
        latest,
    ]

    database.close()


def test_duplicate_updates_existing_candle(tmp_path):
    database, repository = make_repository(tmp_path)

    original = make_candle(0, close="105")
    updated = make_candle(0, close="110")

    repository.save_candle(original)
    repository.save_candle(updated)

    result = repository.get_candles(
        "binance",
        "BTC/USDT",
        "15m",
    )

    assert len(result) == 1
    assert result[0].close == Decimal("110")

    database.close()


def test_get_latest_candle(tmp_path):
    database, repository = make_repository(tmp_path)

    first = make_candle(0)
    latest = make_candle(30)

    repository.save_candles(
        [first, latest]
    )

    result = repository.get_latest_candle(
        "binance",
        "BTC/USDT",
        "15m",
    )

    assert result == latest

    database.close()


def test_empty_latest_returns_none(tmp_path):
    database, repository = make_repository(tmp_path)

    assert repository.get_latest_candle(
        "binance",
        "BTC/USDT",
        "15m",
    ) is None

    database.close()


def test_time_range_filter(tmp_path):
    database, repository = make_repository(tmp_path)

    first = make_candle(0)
    middle = make_candle(15)
    latest = make_candle(30)

    repository.save_candles(
        [first, middle, latest]
    )

    result = repository.get_candles(
        "binance",
        "BTC/USDT",
        "15m",
        start_time=middle.timestamp,
        end_time=latest.timestamp,
    )

    assert result == [
        middle,
        latest,
    ]

    database.close()


def test_limit(tmp_path):
    database, repository = make_repository(tmp_path)

    repository.save_candles(
        [
            make_candle(0),
            make_candle(15),
            make_candle(30),
        ]
    )

    result = repository.get_candles(
        "binance",
        "BTC/USDT",
        "15m",
        limit=2,
    )

    assert len(result) == 2

    database.close()