from datetime import datetime, timezone
from decimal import Decimal
import pytest

from app.market_data.exceptions import (
    InvalidExchangeError,
    InvalidOHLCError,
    InvalidSymbolError,
    InvalidTimeframeError,
    InvalidTimestampError,
    InvalidVolumeError,
)
from app.market_data.models import MarketCandle
from app.market_data.normalization.service import MarketDataNormalizer


def test_market_candle_valid():
    candle = MarketCandle(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
        timestamp=datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc),
        open=Decimal("50000.0"),
        high=Decimal("51000.0"),
        low=Decimal("49500.0"),
        close=Decimal("50500.0"),
        volume=Decimal("10.5"),
    )
    assert candle.exchange == "binance"
    assert candle.symbol == "BTC/USDT"
    assert candle.timeframe == "15m"


def test_market_candle_invalid_metadata():
    ts = datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc)

    # Invalid uppercase exchange name in MarketCandle direct init
    with pytest.raises(InvalidExchangeError):
        MarketCandle("BINANCE", "BTC/USDT", "15m", ts, Decimal("50000"), Decimal("51000"), Decimal("49500"), Decimal("50500"), Decimal("1"))

    # Invalid symbol format without slash
    with pytest.raises(InvalidSymbolError):
        MarketCandle("binance", "BTCUSDT", "15m", ts, Decimal("50000"), Decimal("51000"), Decimal("49500"), Decimal("50500"), Decimal("1"))

    # Unsupported timeframe
    with pytest.raises(InvalidTimeframeError):
        MarketCandle("binance", "BTC/USDT", "5m", ts, Decimal("50000"), Decimal("51000"), Decimal("49500"), Decimal("50500"), Decimal("1"))

    # Naive timestamp
    with pytest.raises(InvalidTimestampError):
        MarketCandle("binance", "BTC/USDT", "15m", datetime(2026, 8, 26, 10, 0), Decimal("50000"), Decimal("51000"), Decimal("49500"), Decimal("50500"), Decimal("1"))


def test_normalizer_invalid_ohlc_and_volume():
    # High lower than low via normalizer
    with pytest.raises(InvalidOHLCError):
        MarketDataNormalizer.normalize_candle(
            "binance", "BTC/USDT", "15m", "2026-08-26T10:00:00Z",
            50000, 49000, 49500, 50000, 10
        )

    # Negative volume via normalizer
    with pytest.raises(InvalidVolumeError):
        MarketDataNormalizer.normalize_candle(
            "binance", "BTC/USDT", "15m", "2026-08-26T10:00:00Z",
            50000, 51000, 49500, 50000, -10
        )
