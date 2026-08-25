from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class IndicatorCandle:
    """
    Candle representation prepared for indicator calculations.

    This is intentionally independent from the storage layer.
    """

    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class IndicatorInput:
    """
    Input dataset supplied to an indicator engine.
    """

    exchange: str
    symbol: str
    timeframe: str
    candles: tuple[IndicatorCandle, ...]

    @property
    def size(self) -> int:
        """Return the number of candles available."""
        return len(self.candles)

    @property
    def latest(self) -> IndicatorCandle | None:
        """Return the latest candle, if available."""
        if not self.candles:
            return None

        return self.candles[-1]