import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.market_data.models import MarketCandle
from app.backtesting.datasets.models import HistoricalDataset
from app.backtesting.datasets.metadata import DatasetMetadata
from app.backtesting.replay.context.provider import HistoricalContextProvider
from app.backtesting.replay.context.exceptions import InvalidLookbackError, FutureDataLeakError

def create_candle(dt: datetime) -> MarketCandle:
    return MarketCandle(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
        timestamp=dt,
        open=Decimal("100"),
        high=Decimal("105"),
        low=Decimal("95"),
        close=Decimal("102"),
        volume=Decimal("1000")
    )

def create_dataset(start_time: datetime, count: int, interval_minutes: int = 15) -> HistoricalDataset:
    candles = []
    for i in range(count):
        dt = start_time + timedelta(minutes=i * interval_minutes)
        candles.append(create_candle(dt))
        
    metadata = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
        start_timestamp=candles[0].timestamp,
        end_timestamp=candles[-1].timestamp,
        candle_count=len(candles)
    )
    return HistoricalDataset(candles=tuple(candles), metadata=metadata)

def test_provider_initialization_invalid_lookback():
    dataset = create_dataset(datetime(2024, 1, 1, tzinfo=timezone.utc), 10)
    with pytest.raises(InvalidLookbackError):
        HistoricalContextProvider(dataset, 0)
    with pytest.raises(InvalidLookbackError):
        HistoricalContextProvider(dataset, -5)

def test_provider_get_context_basic():
    start = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    dataset = create_dataset(start, 20)
    provider = HistoricalContextProvider(dataset, lookback=5)
    
    # Ask for context at the 5th candle (index 4)
    target_time = start + timedelta(minutes=15 * 4)
    window = provider.get_context(target_time)
    
    assert len(window.candles) == 5
    assert window.candles[-1].timestamp == target_time
    assert window.candles[0].timestamp == start
    assert window.is_warmed_up is True
    
def test_provider_get_context_partial_warmup():
    start = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    dataset = create_dataset(start, 20)
    provider = HistoricalContextProvider(dataset, lookback=10)
    
    # Ask for context at the 3rd candle (index 2)
    target_time = start + timedelta(minutes=15 * 2)
    window = provider.get_context(target_time)
    
    assert len(window.candles) == 3
    assert window.candles[-1].timestamp == target_time
    assert window.candles[0].timestamp == start
    assert window.is_warmed_up is False

def test_provider_future_exclusion():
    start = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    dataset = create_dataset(start, 20)
    provider = HistoricalContextProvider(dataset, lookback=5)
    
    # Request a time before the dataset starts
    before_start = start - timedelta(minutes=15)
    window = provider.get_context(before_start)
    assert len(window.candles) == 0
    
    # Request a time exactly between two candles
    between_time = start + timedelta(minutes=20) # after 1st (0m), 2nd (15m), before 3rd (30m)
    window = provider.get_context(between_time)
    assert len(window.candles) == 2
    assert window.candles[-1].timestamp == start + timedelta(minutes=15)
    
def test_provider_deterministic_repeated_calls():
    start = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    dataset = create_dataset(start, 20)
    provider = HistoricalContextProvider(dataset, lookback=5)
    
    target_time = start + timedelta(minutes=60)
    window1 = provider.get_context(target_time)
    window2 = provider.get_context(target_time)
    
    assert window1 == window2
    
def test_provider_insufficient_history_returns_partial():
    start = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    # only 2 candles total
    dataset = create_dataset(start, 2)
    provider = HistoricalContextProvider(dataset, lookback=5)
    
    target_time = start + timedelta(minutes=60)
    window = provider.get_context(target_time)
    
    assert len(window.candles) == 2
    assert window.is_warmed_up is False
    assert window.candles[0].timestamp == start
    assert window.candles[-1].timestamp == start + timedelta(minutes=15)
    
def test_provider_lookback_exactly_honored():
    start = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    dataset = create_dataset(start, 50)
    provider = HistoricalContextProvider(dataset, lookback=15)
    
    target_time = start + timedelta(minutes=15 * 30) # index 30
    window = provider.get_context(target_time)
    
    assert len(window.candles) == 15
    assert window.is_warmed_up is True
    assert window.candles[-1].timestamp == target_time
    assert window.candles[0].timestamp == target_time - timedelta(minutes=15 * 14)
