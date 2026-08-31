from datetime import datetime, timezone, timedelta
import pytest

from app.market_data.freshness import FreshnessMonitor, FreshnessState


def test_freshness_monitor_invalid_thresholds():
    with pytest.raises(ValueError, match="fresh_multiplier"):
        FreshnessMonitor(fresh_multiplier=0)

    with pytest.raises(ValueError, match="delayed_multiplier"):
        FreshnessMonitor(fresh_multiplier=2.0, delayed_multiplier=1.5)


def test_freshness_monitor_none_latest():
    monitor = FreshnessMonitor()
    result = monitor.evaluate("binance", "BTC/USDT", "15m", latest_timestamp=None)

    assert result.state == FreshnessState.STALE
    assert result.delay_seconds is None


def test_freshness_monitor_evaluations():
    monitor = FreshnessMonitor()
    now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)

    # 15 minutes step.
    # Fresh <= 30m delay.
    # Delayed <= 75m delay.
    # Stale > 75m delay.

    # 1. Fresh (10 min ago)
    t1 = now - timedelta(minutes=10)
    res1 = monitor.evaluate("binance", "BTC/USDT", "15m", t1, now=now)
    assert res1.state == FreshnessState.FRESH
    assert res1.delay_seconds == 600.0

    # 2. Delayed (40 min ago)
    t2 = now - timedelta(minutes=40)
    res2 = monitor.evaluate("binance", "BTC/USDT", "15m", t2, now=now)
    assert res2.state == FreshnessState.DELAYED

    # 3. Stale (120 min ago)
    t3 = now - timedelta(minutes=120)
    res3 = monitor.evaluate("binance", "BTC/USDT", "15m", t3, now=now)
    assert res3.state == FreshnessState.STALE
