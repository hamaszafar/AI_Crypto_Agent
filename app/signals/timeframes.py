from __future__ import annotations

from decimal import Decimal
from enum import Enum

# Supported timeframes for the engine
class Timeframe(str, Enum):
    """Standard timeframes used throughout the system."""

    TF_15M = "15m"
    TF_1H = "1h"
    TF_4H = "4h"
    TF_1D = "1d"

    @classmethod
    def from_str(cls, value: str) -> "Timeframe":
        """Parse a string into a Timeframe enum, raising ValueError for unknown values."""
        for tf in cls:
            if tf.value == value:
                return tf
        raise ValueError(f"Unsupported timeframe: {value}")
