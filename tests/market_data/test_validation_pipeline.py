from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.market_data.models import MarketCandle
from app.market_data.validator import (
    CandleValidationError,
    validate_market_data,
)


def make_candle(
    timestamp: datetime,
    *,
    exchange: str = "binance",
    symbol: str = "BTC/USDT",
    timeframe: str = "15m",
    open_price: str = "100",
    high: str = "110",
    low: str = "90",
    close: str = "105",
    volume: str = "10",
) -> MarketCandle:
    return MarketCandle(
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp,
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal(volume),
    )


def test_valid_market_data_passes():
    candles = [
        make_candle(
            datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
        ),
        make_candle(
            datetime(2026, 8, 22, 12, 15, tzinfo=timezone.utc)
        ),
    ]

    result = validate_market_data(candles)

    assert result == candles


def test_invalid_ohlc_fails_pipeline():
    candles = [
        make_candle(
            datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
            high="80",
        )
    ]

    with pytest.raises(CandleValidationError):
        validate_market_data(candles)


def test_negative_volume_fails_pipeline():
    candles = [
        make_candle(
            datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
            volume="-1",
        )
    ]

    with pytest.raises(CandleValidationError):
        validate_market_data(candles)


def test_duplicate_candles_fail_pipeline():
    timestamp = datetime(
        2026,
        8,
        22,
        12,
        0,
        tzinfo=timezone.utc,
    )

    candles = [
        make_candle(timestamp),
        make_candle(timestamp),
    ]

    with pytest.raises(CandleValidationError):
        validate_market_data(candles)


def test_out_of_order_candles_fail_pipeline():
    candles = [
        make_candle(
            datetime(2026, 8, 22, 12, 15, tzinfo=timezone.utc)
        ),
        make_candle(
            datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)
        ),
    ]

    with pytest.raises(CandleValidationError):
        validate_market_data(candles)


def test_inconsistent_exchange_fails_pipeline():
    timestamp = datetime(
        2026,
        8,
        22,
        12,
        0,
        tzinfo=timezone.utc,
    )

    candles = [
        make_candle(timestamp, exchange="binance"),
        make_candle(
            timestamp.replace(minute=15),
            exchange="bybit",
        ),
    ]

    with pytest.raises(CandleValidationError):
        validate_market_data(candles)


def test_inconsistent_symbol_fails_pipeline():
    timestamp = datetime(
        2026,
        8,
        22,
        12,
        0,
        tzinfo=timezone.utc,
    )

    candles = [
        make_candle(timestamp, symbol="BTC/USDT"),
        make_candle(
            timestamp.replace(minute=15),
            symbol="ETH/USDT",
        ),
    ]

    with pytest.raises(CandleValidationError):
        validate_market_data(candles)


def test_inconsistent_timeframe_fails_pipeline():
    timestamp = datetime(
        2026,
        8,
        22,
        12,
        0,
        tzinfo=timezone.utc,
    )

    candles = [
        make_candle(timestamp, timeframe="15m"),
        make_candle(
            timestamp.replace(minute=15),
            timeframe="1h",
        ),
    ]

    with pytest.raises(CandleValidationError):
        validate_market_data(candles)