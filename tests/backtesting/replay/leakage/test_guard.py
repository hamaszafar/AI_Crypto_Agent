import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.market_data.models import MarketCandle
from app.backtesting.replay.context.models import ContextWindow
from app.backtesting.replay.leakage.guard import LeakageGuard
from app.backtesting.replay.leakage.exceptions import (
    FutureDataDetectedError,
    InvalidReplayTimestampError,
)

def create_candle(dt: datetime, timeframe: str = "15m") -> MarketCandle:
    return MarketCandle(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe=timeframe,
        timestamp=dt,
        open=Decimal("100"),
        high=Decimal("105"),
        low=Decimal("95"),
        close=Decimal("102"),
        volume=Decimal("1000")
    )

def test_guard_empty_context():
    replay_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
    context = ContextWindow(candles=tuple(), lookback_size=5, replay_timestamp=replay_time)
    
    validated = LeakageGuard.validate_context(context, replay_time)
    assert validated is context

def test_guard_valid_context_strictly_past():
    replay_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    
    candles = tuple([
        create_candle(datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)),
        create_candle(datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc))
    ])
    
    context = ContextWindow(candles=candles, lookback_size=5, replay_timestamp=replay_time)
    
    validated = LeakageGuard.validate_context(context, replay_time)
    assert validated is context

def test_guard_valid_context_exact_cutoff():
    replay_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    
    candles = tuple([
        create_candle(datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc)),
        create_candle(datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)) # Exact match
    ])
    
    context = ContextWindow(candles=candles, lookback_size=5, replay_timestamp=replay_time)
    
    validated = LeakageGuard.validate_context(context, replay_time)
    assert validated is context

def test_guard_future_data_rejection():
    replay_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    
    candles = tuple([
        create_candle(datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc)),
        create_candle(datetime(2024, 1, 1, 12, 1, tzinfo=timezone.utc)) # 1 minute into the future
    ])
    
    context = ContextWindow(candles=candles, lookback_size=5, replay_timestamp=replay_time)
    
    with pytest.raises(FutureDataDetectedError):
        LeakageGuard.validate_context(context, replay_time)

def test_guard_multi_timeframe_leakage():
    replay_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    
    # Simulate a scenario where a 1D candle is accidentally included before the day closes
    # E.g. A 1D candle timestamped at the end of the day (12 hours in the future)
    candles = tuple([
        create_candle(datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc), "1h"),
        create_candle(datetime(2024, 1, 2, 0, 0, tzinfo=timezone.utc), "1d") # 12 hours in future
    ])
    
    context = ContextWindow(candles=candles, lookback_size=5, replay_timestamp=replay_time)
    
    with pytest.raises(FutureDataDetectedError):
        LeakageGuard.validate_context(context, replay_time)

def test_guard_invalid_naive_timestamp():
    replay_time = datetime(2024, 1, 1, 12, 0) # Missing tzinfo
    
    candles = tuple([
        create_candle(datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc))
    ])
    
    context = ContextWindow(candles=candles, lookback_size=5, replay_timestamp=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc))
    
    with pytest.raises(InvalidReplayTimestampError):
        LeakageGuard.validate_context(context, replay_time)

def test_guard_determinism_and_no_silent_failure():
    replay_time = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    
    future_time = datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc)
    candles = tuple([create_candle(future_time)])
    
    context = ContextWindow(candles=candles, lookback_size=5, replay_timestamp=replay_time)
    
    # Must consistently fail, never silently pass
    for _ in range(10):
        with pytest.raises(FutureDataDetectedError):
            LeakageGuard.validate_context(context, replay_time)
