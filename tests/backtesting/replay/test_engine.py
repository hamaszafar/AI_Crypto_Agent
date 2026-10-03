import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.market_data.models import MarketCandle
from app.backtesting.datasets.models import HistoricalDataset
from app.backtesting.datasets.metadata import DatasetMetadata
from app.backtesting.replay.models import (
    ReplayRequest,
    ReplayStatus,
)
from app.backtesting.replay.exceptions import (
    ReplayFinishedError,
    ReplayInitializationError,
)
from app.backtesting.replay.engine import HistoricalReplayEngine

@pytest.fixture
def valid_candles():
    base_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
    return tuple([
        MarketCandle(
            exchange="binance",
            symbol="btc/usdt",
            timeframe="1h",
            timestamp=base_time + timedelta(hours=i),
            open=Decimal("50000"),
            high=Decimal("51000"),
            low=Decimal("49000"),
            close=Decimal("50500"),
            volume=Decimal("100")
        ) for i in range(5)
    ])

@pytest.fixture
def sample_dataset(valid_candles):
    metadata = DatasetMetadata(
        exchange="binance",
        symbol="btc/usdt",
        timeframe="1h",
        start_timestamp=valid_candles[0].timestamp,
        end_timestamp=valid_candles[-1].timestamp,
        candle_count=len(valid_candles)
    )
    return HistoricalDataset(candles=valid_candles, metadata=metadata)

def test_engine_initialization_valid(sample_dataset):
    engine = HistoricalReplayEngine()
    req = ReplayRequest(dataset=sample_dataset)
    engine.initialize(req)
    
    state = engine.get_state()
    assert state.status == ReplayStatus.IN_PROGRESS
    assert state.total_candles == 5
    assert state.current_index == 0
    assert state.current_candle is None
    assert state.remaining_candles == 5

def test_engine_step_uninitialized():
    engine = HistoricalReplayEngine()
    with pytest.raises(ReplayInitializationError, match="not been initialized"):
        engine.next_step()

def test_engine_first_candle(sample_dataset):
    engine = HistoricalReplayEngine()
    engine.initialize(ReplayRequest(dataset=sample_dataset))
    
    event = engine.next_step()
    assert event.index == 0
    assert event.candle == sample_dataset.candles[0]
    
    state = engine.get_state()
    assert state.current_index == 1
    assert state.remaining_candles == 4
    assert state.current_candle == sample_dataset.candles[0]
    assert state.status == ReplayStatus.IN_PROGRESS

def test_engine_sequential_replay(sample_dataset):
    engine = HistoricalReplayEngine()
    engine.initialize(ReplayRequest(dataset=sample_dataset))
    
    for i in range(5):
        event = engine.next_step()
        assert event.index == i
        assert event.candle == sample_dataset.candles[i]
        
    state = engine.get_state()
    assert state.status == ReplayStatus.COMPLETED
    assert state.remaining_candles == 0
    assert state.current_index == 5
    
    # Repeated calls after completion
    with pytest.raises(ReplayFinishedError):
        engine.next_step()

def test_engine_custom_start_boundary(sample_dataset):
    start = sample_dataset.candles[2].timestamp
    engine = HistoricalReplayEngine()
    engine.initialize(ReplayRequest(dataset=sample_dataset, start_time=start))
    
    state = engine.get_state()
    assert state.total_candles == 3
    
    event = engine.next_step()
    assert event.candle.timestamp == start

def test_engine_custom_end_boundary(sample_dataset):
    end = sample_dataset.candles[2].timestamp
    engine = HistoricalReplayEngine()
    engine.initialize(ReplayRequest(dataset=sample_dataset, end_time=end))
    
    state = engine.get_state()
    assert state.total_candles == 3
    
    for _ in range(3):
        engine.next_step()
        
    assert engine.get_state().status == ReplayStatus.COMPLETED

def test_engine_range_excluding_all(sample_dataset):
    start = sample_dataset.candles[-1].timestamp + timedelta(hours=1)
    engine = HistoricalReplayEngine()
    engine.initialize(ReplayRequest(dataset=sample_dataset, start_time=start))
    
    state = engine.get_state()
    assert state.status == ReplayStatus.COMPLETED
    assert state.total_candles == 0
    
    with pytest.raises(ReplayFinishedError):
        engine.next_step()

def test_engine_reset(sample_dataset):
    engine = HistoricalReplayEngine()
    engine.initialize(ReplayRequest(dataset=sample_dataset))
    
    engine.next_step()
    engine.next_step()
    
    assert engine.get_state().current_index == 2
    
    engine.reset()
    state = engine.get_state()
    assert state.current_index == 0
    assert state.status == ReplayStatus.IN_PROGRESS
    assert state.current_candle is None

def test_engine_reset_uninitialized():
    engine = HistoricalReplayEngine()
    with pytest.raises(ReplayInitializationError, match="Cannot reset before initialization"):
        engine.reset()

def test_engine_single_candle_dataset(valid_candles):
    single_candle = valid_candles[0:1]
    metadata = DatasetMetadata(
        exchange="binance",
        symbol="btc/usdt",
        timeframe="1h",
        start_timestamp=single_candle[0].timestamp,
        end_timestamp=single_candle[-1].timestamp,
        candle_count=1
    )
    dataset = HistoricalDataset(candles=single_candle, metadata=metadata)
    
    engine = HistoricalReplayEngine()
    engine.initialize(ReplayRequest(dataset=dataset))
    
    event = engine.next_step()
    assert event.candle == single_candle[0]
    
    with pytest.raises(ReplayFinishedError):
        engine.next_step()
