from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from app.market_data.models import MarketCandle
from app.backtesting.datasets.models import HistoricalDataset
from app.backtesting.replay.exceptions import InvalidReplayRequestError

class ReplayStatus(Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

@dataclass(frozen=True, slots=True)
class ReplayRequest:
    """Configuration for a historical replay session."""
    dataset: HistoricalDataset
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    def __post_init__(self):
        if self.start_time and self.end_time and self.start_time > self.end_time:
            raise InvalidReplayRequestError("start_time cannot be after end_time")
        if self.start_time and self.start_time.tzinfo is None:
            raise InvalidReplayRequestError("start_time must be timezone-aware")
        if self.end_time and self.end_time.tzinfo is None:
            raise InvalidReplayRequestError("end_time must be timezone-aware")

@dataclass(frozen=True, slots=True)
class ReplayEvent:
    """Represents a single step in the historical replay."""
    candle: MarketCandle
    index: int  # 0-based index of the processed candle in the current replay session
    total_expected: int # Total candles expected to be processed in this session
    
    @property
    def timestamp(self) -> datetime:
        return self.candle.timestamp

@dataclass(frozen=True, slots=True)
class ReplayState:
    """Represents the current state of the replay engine."""
    status: ReplayStatus
    current_index: int  # How many candles have been processed
    total_candles: int
    current_candle: Optional[MarketCandle] = None

    @property
    def remaining_candles(self) -> int:
        return self.total_candles - self.current_index

    @property
    def current_timestamp(self) -> Optional[datetime]:
        return self.current_candle.timestamp if self.current_candle else None
