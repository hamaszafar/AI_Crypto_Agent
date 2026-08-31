from datetime import datetime, timezone
from decimal import Decimal
import pytest

from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe
from app.market_data.exceptions import CandleValidationError
from app.market_data.normalization.service import MarketDataNormalizer


def test_normalizer_normalize_candle():
    candle = MarketDataNormalizer.normalize_candle(
        exchange="BINANCE",
        symbol="BTCUSDT",
        timeframe="15",
        timestamp="2026-08-26T10:00:00Z",
        open_val=50000,
        high_val=51000,
        low_val=49000,
        close_val=50500,
        volume_val=100.5,
    )
    assert candle.exchange == "binance"
    assert candle.symbol == "BTC/USDT"
    assert candle.timeframe == "15m"
    assert candle.open == Decimal("50000")


def test_normalizer_from_exchange_candle():
    ex_candle = Candle(
        exchange="bybit",
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.ONE_HOUR,
        timestamp=datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc),
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("10"),
    )
    mc = MarketDataNormalizer.from_exchange_candle(ex_candle)
    assert mc.exchange == "bybit"
    assert mc.symbol == "BTC/USDT"
    assert mc.timeframe == "1h"


def test_normalizer_raw_tuple():
    raw_array = ["2026-08-26T10:00:00Z", 50000, 51000, 49000, 50500, 10]
    mc = MarketDataNormalizer.normalize_raw_tuple("okx", "BTC-USDT", "60", raw_array)
    assert mc.exchange == "okx"
    assert mc.symbol == "BTC/USDT"
    assert mc.timeframe == "1h"


def test_normalizer_raw_dict():
    raw_d = {
        "timestamp": "2026-08-26T10:00:00Z",
        "open": "50000",
        "high": "51000",
        "low": "49000",
        "close": "50500",
        "volume": "10",
    }
    mc = MarketDataNormalizer.normalize_raw_dict("kraken", "XBT/USD", "240", raw_d)
    assert mc.exchange == "kraken"
    assert mc.symbol == "BTC/USD"
    assert mc.timeframe == "4h"

    with pytest.raises(CandleValidationError):
        MarketDataNormalizer.normalize_raw_dict("kraken", "BTC/USD", "4h", {"invalid": "data"})
