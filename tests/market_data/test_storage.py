from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.exchanges.models import Candle
from app.market_data.storage import MarketDataStorage
from app.storage.repositories.memory_candle_repository import (
    InMemoryCandleRepository,
)
from app.storage.service import StorageService


def make_candle(
    timestamp: datetime | None = None,
    close: str = "105",
) -> Candle:
    return Candle(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
        timestamp=timestamp
        or datetime(
            2026,
            8,
            24,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal(close),
        volume=Decimal("1000"),
    )


def make_storage() -> MarketDataStorage:
    repository = InMemoryCandleRepository()
    service = StorageService(repository)

    return MarketDataStorage(service)


def test_save_candle():
    storage = make_storage()

    stored = storage.save_candle(
        make_candle()
    )

    assert stored.exchange == "binance"
    assert stored.symbol == "BTC/USDT"
    assert stored.timeframe == "15m"
    assert stored.close == Decimal("105")


def test_save_multiple_candles():
    storage = make_storage()

    candles = [
        make_candle(close="101"),
        make_candle(
            timestamp=datetime(
                2026,
                8,
                24,
                12,
                15,
                tzinfo=timezone.utc,
            ),
            close="102",
        ),
    ]

    stored = storage.save_candles(candles)

    assert len(stored) == 2
    assert storage.count() == 2


def test_get_candles():
    storage = make_storage()

    storage.save_candle(
        make_candle()
    )

    candles = storage.get_candles(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
    )

    assert len(candles) == 1
    assert candles[0].close == Decimal("105")


def test_get_candles_with_limit():
    storage = make_storage()

    storage.save_candles(
        [
            make_candle(close="101"),
            make_candle(
                timestamp=datetime(
                    2026,
                    8,
                    24,
                    12,
                    15,
                    tzinfo=timezone.utc,
                ),
                close="102",
            ),
            make_candle(
                timestamp=datetime(
                    2026,
                    8,
                    24,
                    12,
                    30,
                    tzinfo=timezone.utc,
                ),
                close="103",
            ),
        ]
    )

    candles = storage.get_candles(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
        limit=2,
    )

    assert len(candles) == 2
    assert candles[0].close == Decimal("101")
    assert candles[1].close == Decimal("102")


def test_get_latest_candle():
    storage = make_storage()

    storage.save_candle(
        make_candle(close="101")
    )

    storage.save_candle(
        make_candle(
            timestamp=datetime(
                2026,
                8,
                24,
                12,
                15,
                tzinfo=timezone.utc,
            ),
            close="102",
        )
    )

    latest = storage.get_latest_candle(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
    )

    assert latest is not None
    assert latest.close == Decimal("102")


def test_latest_candle_empty():
    storage = make_storage()

    latest = storage.get_latest_candle(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
    )

    assert latest is None


def test_count_market():
    storage = make_storage()

    storage.save_candle(
        make_candle()
    )

    storage.save_candle(
        make_candle(
            timestamp=datetime(
                2026,
                8,
                24,
                12,
                15,
                tzinfo=timezone.utc,
            )
        )
    )

    assert (
        storage.count(
            exchange="binance",
            symbol="BTC/USDT",
            timeframe="15m",
        )
        == 2
    )


def test_count_all():
    storage = make_storage()

    storage.save_candle(
        make_candle()
    )

    storage.save_candle(
        make_candle(
            timestamp=datetime(
                2026,
                8,
                24,
                12,
                15,
                tzinfo=timezone.utc,
            )
        )
    )

    assert storage.count() == 2


def test_partial_count_arguments_rejected():
    storage = make_storage()

    with pytest.raises(ValueError):
        storage.count(
            exchange="binance",
        )