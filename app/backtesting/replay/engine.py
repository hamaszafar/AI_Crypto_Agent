from typing import List

from app.market_data.models import MarketCandle
from app.backtesting.replay.models import (
    ReplayRequest,
    ReplayEvent,
    ReplayState,
    ReplayStatus,
)
from app.backtesting.replay.exceptions import (
    ReplayFinishedError,
    ReplayInitializationError,
)

class HistoricalReplayEngine:
    """
    Engine responsible for sequentially progressing through a HistoricalDataset.
    Ensures strict chronological progression without exposing future data.
    """
    def __init__(self):
        self._request = None
        self._candles: List[MarketCandle] = []
        self._current_index = 0
        self._status = ReplayStatus.NOT_STARTED

    def initialize(self, request: ReplayRequest) -> None:
        """
        Initializes the replay engine with a specific request.
        Filters candles based on start_time and end_time boundaries.
        """
        try:
            self._request = request
            dataset = request.dataset
            
            # Filter candles by requested time range
            filtered_candles = []
            for candle in dataset:
                if request.start_time and candle.timestamp < request.start_time:
                    continue
                if request.end_time and candle.timestamp > request.end_time:
                    continue
                filtered_candles.append(candle)
                
            self._candles = filtered_candles
            self._current_index = 0
            
            if not self._candles:
                self._status = ReplayStatus.COMPLETED
            else:
                self._status = ReplayStatus.IN_PROGRESS
                
        except Exception as e:
            self._status = ReplayStatus.FAILED
            raise ReplayInitializationError(f"Failed to initialize replay: {str(e)}") from e

    def next_step(self) -> ReplayEvent:
        """
        Advances the replay by one candle and returns the corresponding event.
        Raises ReplayFinishedError if no more candles are available.
        """
        if self._status == ReplayStatus.NOT_STARTED:
            raise ReplayInitializationError("Replay engine has not been initialized.")
            
        if self._status == ReplayStatus.COMPLETED or self._current_index >= len(self._candles):
            self._status = ReplayStatus.COMPLETED
            raise ReplayFinishedError("No more candles available in this replay session.")
            
        candle = self._candles[self._current_index]
        event = ReplayEvent(
            candle=candle,
            index=self._current_index,
            total_expected=len(self._candles)
        )
        
        self._current_index += 1
        
        if self._current_index >= len(self._candles):
            self._status = ReplayStatus.COMPLETED
            
        return event

    def reset(self) -> None:
        """
        Resets the replay to the beginning using the previously initialized request.
        """
        if self._request is None:
            raise ReplayInitializationError("Cannot reset before initialization.")
        
        self._current_index = 0
        if not self._candles:
            self._status = ReplayStatus.COMPLETED
        else:
            self._status = ReplayStatus.IN_PROGRESS

    def get_state(self) -> ReplayState:
        """
        Returns the current state of the replay engine.
        """
        current_candle = None
        if self._current_index > 0 and self._current_index <= len(self._candles):
            current_candle = self._candles[self._current_index - 1]
            
        return ReplayState(
            status=self._status,
            current_index=self._current_index,
            total_candles=len(self._candles),
            current_candle=current_candle
        )
