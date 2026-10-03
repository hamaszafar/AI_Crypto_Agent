import pytest
from datetime import datetime, timezone
from decimal import Decimal

from app.market_data.models import MarketCandle
from app.backtesting.replay.context.models import ContextWindow

def create_candle(timestamp_str: str) -> MarketCandle:
    return MarketCandle(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
        timestamp=datetime.fromisoformat(timestamp_str).replace(tzinfo=timezone.utc),
        open=Decimal("100"),
        high=Decimal("105"),
        low=Decimal("95"),
        close=Decimal("102"),
        volume=Decimal("1000")
    )

def test_context_window_immutability():
    candles = [
        create_candle("2024-01-01T00:00:00"),
        create_candle("2024-01-01T00:15:00")
    ]
    window = ContextWindow(
        candles=candles, # list
        lookback_size=5,
        replay_timestamp=datetime.now(timezone.utc)
    )
    
    assert isinstance(window.candles, tuple)
    
    # Attempting to mutate should fail if dataclass frozen is respected
    with pytest.raises(Exception):
        window.candles = tuple()
        
def test_context_window_warmed_up():
    candles = [
        create_candle("2024-01-01T00:00:00"),
        create_candle("2024-01-01T00:15:00"),
        create_candle("2024-01-01T00:30:00")
    ]
    
    # Exact lookback
    w1 = ContextWindow(candles=tuple(candles), lookback_size=3, replay_timestamp=datetime.now(timezone.utc))
    assert w1.is_warmed_up is True
    
    # Over lookback
    w2 = ContextWindow(candles=tuple(candles), lookback_size=2, replay_timestamp=datetime.now(timezone.utc))
    assert w2.is_warmed_up is True
    
    # Under lookback
    w3 = ContextWindow(candles=tuple(candles), lookback_size=4, replay_timestamp=datetime.now(timezone.utc))
    assert w3.is_warmed_up is False

def test_context_window_current_candle():
    candles = [
        create_candle("2024-01-01T00:00:00"),
        create_candle("2024-01-01T00:15:00")
    ]
    
    window = ContextWindow(candles=tuple(candles), lookback_size=5, replay_timestamp=datetime.now(timezone.utc))
    assert window.current_candle == candles[-1]
    
    empty_window = ContextWindow(candles=tuple(), lookback_size=5, replay_timestamp=datetime.now(timezone.utc))
    assert empty_window.current_candle is None
