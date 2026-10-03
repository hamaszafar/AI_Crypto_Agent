import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.market_data.models import MarketCandle
from app.backtesting.datasets.models import HistoricalDataset
from app.backtesting.datasets.metadata import DatasetMetadata
from app.backtesting.replay.models import (
    ReplayRequest,
    ReplayEvent,
    ReplayState,
    ReplayStatus,
)
from app.backtesting.replay.exceptions import InvalidReplayRequestError

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
        candle_count=5
    )
    return HistoricalDataset(candles=valid_candles, metadata=metadata)

def test_replay_request_valid(sample_dataset):
    req = ReplayRequest(dataset=sample_dataset)
    assert req.dataset == sample_dataset
    assert req.start_time is None
    assert req.end_time is None

def test_replay_request_with_valid_range(sample_dataset):
    start = sample_dataset.candles[1].timestamp
    end = sample_dataset.candles[3].timestamp
    req = ReplayRequest(dataset=sample_dataset, start_time=start, end_time=end)
    assert req.start_time == start
    assert req.end_time == end

def test_replay_request_invalid_range(sample_dataset):
    start = sample_dataset.candles[3].timestamp
    end = sample_dataset.candles[1].timestamp
    with pytest.raises(InvalidReplayRequestError, match="start_time cannot be after end_time"):
        ReplayRequest(dataset=sample_dataset, start_time=start, end_time=end)

def test_replay_request_naive_start_time(sample_dataset):
    with pytest.raises(InvalidReplayRequestError, match="start_time must be timezone-aware"):
        ReplayRequest(dataset=sample_dataset, start_time=datetime(2023, 1, 1))

def test_replay_request_naive_end_time(sample_dataset):
    with pytest.raises(InvalidReplayRequestError, match="end_time must be timezone-aware"):
        ReplayRequest(dataset=sample_dataset, end_time=datetime(2023, 1, 1))

def test_replay_event(valid_candles):
    candle = valid_candles[0]
    event = ReplayEvent(candle=candle, index=0, total_expected=5)
    assert event.candle == candle
    assert event.index == 0
    assert event.total_expected == 5
    assert event.timestamp == candle.timestamp

def test_replay_state(valid_candles):
    candle = valid_candles[0]
    state = ReplayState(
        status=ReplayStatus.IN_PROGRESS,
        current_index=1,
        total_candles=5,
        current_candle=candle
    )
    assert state.status == ReplayStatus.IN_PROGRESS
    assert state.current_index == 1
    assert state.total_candles == 5
    assert state.current_candle == candle
    assert state.remaining_candles == 4
    assert state.current_timestamp == candle.timestamp

def test_replay_state_empty():
    state = ReplayState(
        status=ReplayStatus.NOT_STARTED,
        current_index=0,
        total_candles=5,
        current_candle=None
    )
    assert state.current_timestamp is None
    assert state.remaining_candles == 5
