from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.market_data.models import MarketCandle
from app.market_data.validator import (
    CandleValidationError,
    is_valid_volume,
    validate_volume,
)


def make_candle(volume: str = "100") -> MarketCandle:
    return MarketCandle(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
        timestamp=datetime(
            2026,
            8,
            22,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
        volume=Decimal(volume),
    )


def test_positive_volume_is_valid():
    candle = make_candle("123.456")

    validate_volume(candle)


def test_zero_volume_is_valid():
    candle = make_candle("0")

    validate_volume(candle)


def test_negative_volume_is_rejected():
    candle = make_candle("-1")

    with pytest.raises(CandleValidationError):
        validate_volume(candle)


def test_nan_volume_is_rejected():
    candle = make_candle("NaN")

    with pytest.raises(CandleValidationError):
        validate_volume(candle)


def test_positive_infinity_volume_is_rejected():
    candle = make_candle("Infinity")

    with pytest.raises(CandleValidationError):
        validate_volume(candle)


def test_negative_infinity_volume_is_rejected():
    candle = make_candle("-Infinity")

    with pytest.raises(CandleValidationError):
        validate_volume(candle)


def test_non_decimal_volume_is_rejected():
    candle = make_candle()
    object.__setattr__(candle, "volume", 100)

    with pytest.raises(CandleValidationError):
        validate_volume(candle)


def test_is_valid_volume_returns_true_for_valid_volume():
    candle = make_candle("50.25")

    assert is_valid_volume(candle) is True


def test_is_valid_volume_returns_false_for_negative_volume():
    candle = make_candle("-10")

    assert is_valid_volume(candle) is False
