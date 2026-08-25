from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.market_data.models import MarketCandle
from app.market_data.validator import (
    CandleValidationError,
    is_consistent,
    validate_consistency,
)


BASE_TIME = datetime(
    2026,
    8,
    22,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_candle(
    *,
    exchange: str = "binance",
    symbol: str = "BTC/USDT",
    timeframe: str = "15m",
    minute: int = 0,
) -> MarketCandle:
    return MarketCandle(
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        timestamp=BASE_TIME.replace(
            minute=minute,
        ),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
        volume=Decimal("100"),
    )


def test_consistent_candles_are_valid():
    candles = [
        make_candle(minute=0),
        make_candle(minute=15),
        make_candle(minute=30),
    ]

    validate_consistency(candles)


def test_consistent_returns_true():
    candles = [
        make_candle(minute=0),
        make_candle(minute=15),
    ]

    assert is_consistent(candles) is True


def test_different_exchange_is_invalid():
    candles = [
        make_candle(
            exchange="binance",
            minute=0,
        ),
        make_candle(
            exchange="bybit",
            minute=15,
        ),
    ]

    with pytest.raises(CandleValidationError):
        validate_consistency(candles)


def test_different_exchange_returns_false():
    candles = [
        make_candle(
            exchange="binance",
            minute=0,
        ),
        make_candle(
            exchange="bybit",
            minute=15,
        ),
    ]

    assert is_consistent(candles) is False


def test_different_symbol_is_invalid():
    candles = [
        make_candle(
            symbol="BTC/USDT",
            minute=0,
        ),
        make_candle(
            symbol="ETH/USDT",
            minute=15,
        ),
    ]

    with pytest.raises(CandleValidationError):
        validate_consistency(candles)


def test_different_symbol_returns_false():
    candles = [
        make_candle(
            symbol="BTC/USDT",
            minute=0,
        ),
        make_candle(
            symbol="ETH/USDT",
            minute=15,
        ),
    ]

    assert is_consistent(candles) is False


def test_different_timeframe_is_invalid():
    candles = [
        make_candle(
            timeframe="15m",
            minute=0,
        ),
        make_candle(
            timeframe="1h",
            minute=15,
        ),
    ]

    with pytest.raises(CandleValidationError):
        validate_consistency(candles)


def test_different_timeframe_returns_false():
    candles = [
        make_candle(
            timeframe="15m",
            minute=0,
        ),
        make_candle(
            timeframe="1h",
            minute=15,
        ),
    ]

    assert is_consistent(candles) is False


def test_empty_collection_is_consistent():
    assert is_consistent([]) is True


def test_single_candle_is_consistent():
    candle = make_candle()

    assert is_consistent([candle]) is True


def test_generator_is_supported():
    candles = (
        make_candle(minute=minute)
        for minute in (0, 15, 30)
    )

    assert is_consistent(candles) is True


def test_exchange_error_contains_expected_and_actual_values():
    candles = [
        make_candle(
            exchange="binance",
            minute=0,
        ),
        make_candle(
            exchange="okx",
            minute=15,
        ),
    ]

    with pytest.raises(
        CandleValidationError,
        match="binance.*okx",
    ):
        validate_consistency(candles)


def test_symbol_error_contains_expected_and_actual_values():
    candles = [
        make_candle(
            symbol="BTC/USDT",
            minute=0,
        ),
        make_candle(
            symbol="SOL/USDT",
            minute=15,
        ),
    ]

    with pytest.raises(
        CandleValidationError,
        match="BTC/USDT.*SOL/USDT",
    ):
        validate_consistency(candles)


def test_timeframe_error_contains_expected_and_actual_values():
    candles = [
        make_candle(
            timeframe="15m",
            minute=0,
        ),
        make_candle(
            timeframe="4h",
            minute=15,
        ),
    ]

    with pytest.raises(
        CandleValidationError,
        match="15m.*4h",
    ):
        validate_consistency(candles)
