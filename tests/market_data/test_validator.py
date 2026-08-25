from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.market_data.models import MarketCandle
from app.market_data.validator import (
    CandleValidationError,
    is_valid_ohlc,
    validate_ohlc,
)


def make_candle(
    *,
    open_price: str = "100",
    high: str = "110",
    low: str = "90",
    close: str = "105",
) -> MarketCandle:
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
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("100"),
    )


def test_valid_ohlc_passes():
    candle = make_candle()

    validate_ohlc(candle)


def test_is_valid_ohlc_returns_true_for_valid_candle():
    candle = make_candle()

    assert is_valid_ohlc(candle) is True


def test_high_cannot_be_lower_than_low():
    candle = make_candle(
        open_price="100",
        high="90",
        low="95",
        close="100",
    )

    with pytest.raises(CandleValidationError):
        validate_ohlc(candle)


def test_high_cannot_be_lower_than_open():
    candle = make_candle(
        open_price="105",
        high="100",
        low="90",
        close="95",
    )

    with pytest.raises(CandleValidationError):
        validate_ohlc(candle)


def test_high_cannot_be_lower_than_close():
    candle = make_candle(
        open_price="100",
        high="105",
        low="90",
        close="110",
    )

    with pytest.raises(CandleValidationError):
        validate_ohlc(candle)


def test_low_cannot_be_higher_than_open():
    candle = make_candle(
        open_price="90",
        high="110",
        low="95",
        close="100",
    )

    with pytest.raises(CandleValidationError):
        validate_ohlc(candle)


def test_low_cannot_be_higher_than_close():
    candle = make_candle(
        open_price="100",
        high="110",
        low="105",
        close="90",
    )

    with pytest.raises(CandleValidationError):
        validate_ohlc(candle)


def test_zero_open_is_rejected():
    candle = make_candle(open_price="0")

    with pytest.raises(CandleValidationError):
        validate_ohlc(candle)


def test_negative_close_is_rejected():
    candle = make_candle(close="-1")

    with pytest.raises(CandleValidationError):
        validate_ohlc(candle)


def test_zero_high_is_rejected():
    candle = make_candle(
        open_price="0",
        high="0",
        low="0",
        close="0",
    )

    with pytest.raises(CandleValidationError):
        validate_ohlc(candle)


def test_nan_price_is_rejected():
    candle = make_candle(high="NaN")

    with pytest.raises(CandleValidationError):
        validate_ohlc(candle)


def test_infinite_price_is_rejected():
    candle = make_candle(high="Infinity")

    with pytest.raises(CandleValidationError):
        validate_ohlc(candle)


def test_invalid_candle_returns_false():
    candle = make_candle(
        high="90",
        low="95",
    )

    assert is_valid_ohlc(candle) is False
