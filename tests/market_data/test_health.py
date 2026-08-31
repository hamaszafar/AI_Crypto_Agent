from datetime import datetime, timezone
import pytest

from app.market_data.health import CollectionHealthTracker, HealthStatus


def test_health_tracker_initial():
    tracker = CollectionHealthTracker()
    health = tracker.get_health("binance")

    assert health.exchange == "binance"
    assert health.status == HealthStatus.HEALTHY
    assert health.failure_count == 0
    assert health.total_collected == 0


def test_health_tracker_success():
    tracker = CollectionHealthTracker()
    t_now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    t_candle = datetime(2025, 1, 1, 11, 45, tzinfo=timezone.utc)

    tracker.record_success("binance", candles_collected=50, latest_candle_time=t_candle, now=t_now)
    health = tracker.get_health("binance")

    assert health.status == HealthStatus.HEALTHY
    assert health.last_success == t_now
    assert health.total_collected == 50
    assert health.latest_candle_time == t_candle


def test_health_tracker_failures_degraded_unhealthy():
    tracker = CollectionHealthTracker(degraded_threshold=2, unhealthy_threshold=4)

    # 1 failure -> HEALTHY
    tracker.record_failure("bybit")
    assert tracker.get_health("bybit").status == HealthStatus.HEALTHY

    # 2 failures -> DEGRADED
    tracker.record_failure("bybit")
    assert tracker.get_health("bybit").status == HealthStatus.DEGRADED

    # 3 failures -> DEGRADED
    tracker.record_failure("bybit")
    assert tracker.get_health("bybit").status == HealthStatus.DEGRADED

    # 4 failures -> UNHEALTHY
    tracker.record_failure("bybit")
    assert tracker.get_health("bybit").status == HealthStatus.UNHEALTHY

    # Success resets failure count and status back to HEALTHY
    tracker.record_success("bybit", candles_collected=10)
    assert tracker.get_health("bybit").status == HealthStatus.HEALTHY
    assert tracker.get_health("bybit").failure_count == 0
