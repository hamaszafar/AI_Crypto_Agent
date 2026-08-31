from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.market_data.models import MarketCandle
from app.market_data.quality.gap import find_candle_gaps


def make_candle(ts: datetime) -> MarketCandle:
    return MarketCandle(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
        timestamp=ts,
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50500"),
        volume=Decimal("10"),
    )


def test_find_candle_gaps_none():
    base_ts = datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc)
    candles = [
        make_candle(base_ts),
        make_candle(base_ts + timedelta(minutes=15)),
        make_candle(base_ts + timedelta(minutes=30)),
    ]
    gaps = find_candle_gaps(candles)
    assert len(gaps) == 0


def test_find_candle_gaps_detected():
    base_ts = datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc)
    candles = [
        make_candle(base_ts),
        make_candle(base_ts + timedelta(minutes=15)),
        # Missing 10:30
        make_candle(base_ts + timedelta(minutes=45)),
    ]
    gaps = find_candle_gaps(candles)
    assert len(gaps) == 1
    assert gaps[0].missing_count == 1
    assert gaps[0].expected_timestamp == base_ts + timedelta(minutes=30)
