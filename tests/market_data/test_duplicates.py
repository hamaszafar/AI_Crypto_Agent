from datetime import datetime, timezone
from decimal import Decimal

from app.market_data.models import MarketCandle
from app.market_data.validator import (
    candle_identity,
    find_duplicate_candles,
    has_duplicates,
    remove_duplicate_candles,
)


def make_candle(
    *,
    exchange: str = "binance",
    symbol: str = "BTC/USDT",
    timeframe: str = "15m",
    minute: int = 0,
    close: str = "105",
) -> MarketCandle:
    return MarketCandle(
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
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
        volume=Decimal("100"),
    )


def test_candle_identity_uses_exchange_symbol_timeframe_timestamp():
    candle = make_candle()

    assert candle_identity(candle) == (
        "binance",
        "BTC/USDT",
        "15m",
        datetime(
            2026,
            8,
            22,
            12,
            0,
            tzinfo=timezone.utc,
        ),
    )


def test_identical_candles_are_duplicates():
    candle = make_candle()

    candles = [candle, candle]

    assert has_duplicates(candles) is True


def test_different_timestamps_are_not_duplicates():
    first = make_candle(minute=0)
    second = make_candle(minute=15)

    assert has_duplicates([first, second]) is False


def test_different_symbols_are_not_duplicates():
    first = make_candle(symbol="BTC/USDT")
    second = make_candle(symbol="ETH/USDT")

    assert has_duplicates([first, second]) is False


def test_different_timeframes_are_not_duplicates():
    first = make_candle(timeframe="15m")
    second = make_candle(timeframe="1h")

    assert has_duplicates([first, second]) is False


def test_different_exchanges_are_not_duplicates():
    first = make_candle(exchange="binance")
    second = make_candle(exchange="bybit")

    assert has_duplicates([first, second]) is False


def test_same_identity_with_different_prices_is_still_duplicate():
    first = make_candle(close="105")
    second = make_candle(close="106")

    assert has_duplicates([first, second]) is True


def test_find_duplicate_candles_returns_only_later_occurrences():
    first = make_candle(minute=0)
    duplicate = make_candle(minute=0, close="106")
    second = make_candle(minute=15)

    duplicates = find_duplicate_candles(
        [first, duplicate, second]
    )

    assert duplicates == [duplicate]


def test_find_duplicate_candles_preserves_duplicate_order():
    first = make_candle(minute=0)
    duplicate_one = make_candle(minute=0, close="106")
    duplicate_two = make_candle(minute=0, close="107")

    duplicates = find_duplicate_candles(
        [first, duplicate_one, duplicate_two]
    )

    assert duplicates == [duplicate_one, duplicate_two]


def test_remove_duplicate_candles_keeps_first_occurrence():
    first = make_candle(minute=0, close="105")
    duplicate = make_candle(minute=0, close="106")
    second = make_candle(minute=15)

    result = remove_duplicate_candles(
        [first, duplicate, second]
    )

    assert result == [first, second]


def test_remove_duplicate_candles_preserves_original_order():
    first = make_candle(minute=15)
    second = make_candle(minute=0)
    duplicate = make_candle(minute=0, close="106")

    result = remove_duplicate_candles(
        [first, second, duplicate]
    )

    assert result == [first, second]


def test_empty_collection_has_no_duplicates():
    assert has_duplicates([]) is False


def test_empty_collection_returns_no_duplicates():
    assert find_duplicate_candles([]) == []


def test_empty_collection_remains_empty_after_removal():
    assert remove_duplicate_candles([]) == []
