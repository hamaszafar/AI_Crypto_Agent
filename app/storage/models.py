from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.exchanges.models import Candle


@dataclass(frozen=True)
class StoredCandle:
    """Candle representation used by the storage layer."""

    exchange: str
    symbol: str
    timeframe: str
    timestamp: datetime

    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    @classmethod
    def from_candle(cls, candle: Candle) -> "StoredCandle":
        """Create a stored candle from the common market Candle model."""

        return cls(
            exchange=candle.exchange,
            symbol=candle.symbol,
            timeframe=candle.timeframe,
            timestamp=candle.timestamp,
            open=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            volume=candle.volume,
        )