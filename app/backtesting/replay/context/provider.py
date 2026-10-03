import bisect
from datetime import datetime
from typing import List

from app.backtesting.datasets.models import HistoricalDataset
from app.backtesting.replay.context.exceptions import InvalidLookbackError, FutureDataLeakError
from app.backtesting.replay.context.models import ContextWindow

class HistoricalContextProvider:
    """
    Provides a sliding context window of historical candles up to a specific replay timestamp.
    Strictly guarantees that no future data (candles with timestamp > replay_timestamp) is exposed.
    """
    def __init__(self, dataset: HistoricalDataset, lookback: int):
        if lookback <= 0:
            raise InvalidLookbackError(f"Lookback must be positive, got {lookback}")
            
        self._dataset = dataset
        self._lookback = lookback
        
        # Pre-extract timestamps for O(log N) binary search
        self._timestamps = [candle.timestamp for candle in dataset.candles]
        
    def get_context(self, timestamp: datetime) -> ContextWindow:
        """
        Retrieves a context window of up to `lookback` candles available at `timestamp`.
        The context will never contain a candle where candle.timestamp > timestamp.
        """
        # Find the insertion point where all elements before it are <= timestamp.
        # bisect_right returns the index of the first element that is strictly > timestamp.
        idx = bisect.bisect_right(self._timestamps, timestamp)
        
        start_idx = max(0, idx - self._lookback)
        context_candles = self._dataset.candles[start_idx:idx]
        
        # Safety check: Assert no future data leaked. 
        # (This is technically redundant given bisect_right, but serves as a strict invariant check).
        if context_candles and context_candles[-1].timestamp > timestamp:
            raise FutureDataLeakError(
                f"CRITICAL: Future data leaked. "
                f"Candle timestamp {context_candles[-1].timestamp} > Replay timestamp {timestamp}"
            )
            
        return ContextWindow(
            candles=context_candles,
            lookback_size=self._lookback,
            replay_timestamp=timestamp
        )
