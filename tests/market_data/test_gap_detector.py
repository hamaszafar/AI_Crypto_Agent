from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest

from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe
from app.market_data.gap_detector import GapDetector, Gap


def make_candle(ts: datetime) -> Candle:
    return Candle(
        exchange="binance",
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        timestamp=ts,
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("95"),
        close=Decimal("105"),
        volume=Decimal("10"),
    )


def test_gap_detector_continuous_data():
    t1 = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2025, 1, 1, 10, 15, tzinfo=timezone.utc)
    t3 = datetime(2025, 1, 1, 10, 30, tzinfo=timezone.utc)

    candles = [make_candle(t1), make_candle(t2), make_candle(t3)]
    gaps = GapDetector.detect_gaps(candles, "15m")

    assert gaps == []


def test_gap_detector_single_gap():
    t1 = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2025, 1, 1, 10, 15, tzinfo=timezone.utc)
    t3 = datetime(2025, 1, 1, 11, 0, tzinfo=timezone.utc)  # Missing 10:30 and 10:45

    candles = [make_candle(t1), make_candle(t2), make_candle(t3)]
    gaps = GapDetector.detect_gaps(candles, "15m")

    assert len(gaps) == 1
    assert gaps[0].start_time == datetime(2025, 1, 1, 10, 30, tzinfo=timezone.utc)
    assert gaps[0].end_time == datetime(2025, 1, 1, 10, 45, tzinfo=timezone.utc)
    assert gaps[0].missing_count == 2


def test_gap_detector_multiple_gaps():
    t1 = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2025, 1, 1, 10, 30, tzinfo=timezone.utc)  # Missing 10:15
    t3 = datetime(2025, 1, 1, 11, 0, tzinfo=timezone.utc)   # Missing 10:45

    candles = [make_candle(t1), make_candle(t2), make_candle(t3)]
    gaps = GapDetector.detect_gaps(candles, "15m")

    assert len(gaps) == 2
    assert gaps[0].missing_count == 1
    assert gaps[1].missing_count == 1


def test_gap_detector_empty_or_single_candle():
    assert GapDetector.detect_gaps([], "15m") == []
    t1 = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    assert GapDetector.detect_gaps([make_candle(t1)], "15m") == []


def test_gap_detector_invalid_timeframe():
    t1 = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2025, 1, 1, 10, 15, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="Unsupported timeframe"):
        GapDetector.detect_gaps([make_candle(t1), make_candle(t2)], "3m")
