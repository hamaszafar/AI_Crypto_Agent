from datetime import datetime, timezone
from decimal import Decimal

from app.exchanges.models import Candle
from app.storage.repositories.candle_repository import CandleRepository
from app.storage.repositories.memory_candle_repository import (
    MemoryCandleRepository,
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
        timestamp=timestamp or datetime(
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


def make_service() -> StorageService:
    repository = MemoryCandleRepository()
    return StorageService(repository)


def test_storage_repository_is_abstract():
    assert CandleRepository.__abstractmethods__


def test_save_candle():
    service = make_service()

    stored = service.save_candle(make_candle())

    assert stored.exchange == "binance"
    assert stored.symbol == "BTC/USDT"
    assert stored.timeframe == "15m"
    assert stored.close == Decimal("105")


def test_save_multiple_candles():
    service = make_service()

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

    stored = service.save_candles(candles)

    assert len(stored) == 2
    assert service.count() == 2


def test_get_candles():
    service = make_service()

    service.save_candle(make_candle())

    candles = service.get_candles(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
    )

    assert len(candles) == 1
    assert candles[0].close == Decimal("105")


def test_get_latest_candle():
    service = make_service()

    service.save_candle(make_candle(close="101"))

    service.save_candle(
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

    latest = service.get_latest_candle(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
    )

    assert latest is not None
    assert latest.close == Decimal("102")


def test_count():
    service = make_service()

    service.save_candle(make_candle())

    service.save_candle(
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

    assert service.count() == 2
    assert service.count(exchange="binance") == 2
    assert service.count(symbol="BTC/USDT") == 2
    assert service.count(timeframe="15m") == 2