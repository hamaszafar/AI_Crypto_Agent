from datetime import datetime, timezone
from decimal import Decimal

from app.market_data.models import MarketCandle


def make_candle() -> MarketCandle:
    return MarketCandle(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
        timestamp=datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc),
        open=Decimal("117500"),
        high=Decimal("117800"),
        low=Decimal("117400"),
        close=Decimal("117700"),
        volume=Decimal("123.456"),
    )


def test_market_candle_can_be_created():
    candle = make_candle()

    assert candle.exchange == "binance"
    assert candle.symbol == "BTC/USDT"
    assert candle.timeframe == "15m"


def test_market_candle_contains_ohlcv_data():
    candle = make_candle()

    assert candle.open == Decimal("117500")
    assert candle.high == Decimal("117800")
    assert candle.low == Decimal("117400")
    assert candle.close == Decimal("117700")
    assert candle.volume == Decimal("123.456")


def test_market_candle_timestamp_is_preserved():
    candle = make_candle()

    assert candle.timestamp == datetime(
        2026,
        8,
        22,
        12,
        0,
        tzinfo=timezone.utc,
    )


def test_market_candle_is_immutable():
    candle = make_candle()

    try:
        candle.close = Decimal("118000")
        assert False, "MarketCandle should be immutable"
    except AttributeError:
        pass
