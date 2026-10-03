from dataclasses import dataclass
from datetime import datetime
from typing import Tuple, Optional

from app.market_data.models import MarketCandle

@dataclass(frozen=True, slots=True)
class ContextWindow:
    """
    Immutable snapshot of historical candles representing the context window at a specific replay timestamp.
    """
    candles: Tuple[MarketCandle, ...]
    lookback_size: int
    replay_timestamp: datetime

    def __post_init__(self):
        # Guarantee internal immutability
        if not isinstance(self.candles, tuple):
            object.__setattr__(self, "candles", tuple(self.candles))

    @property
    def is_warmed_up(self) -> bool:
        """Returns True if the context has enough candles to satisfy the lookback requirement."""
        return len(self.candles) >= self.lookback_size

    @property
    def current_candle(self) -> Optional[MarketCandle]:
        """Returns the most recent candle in the context window, or None if empty."""
        return self.candles[-1] if self.candles else None
