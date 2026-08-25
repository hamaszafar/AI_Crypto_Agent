from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class MarketCandle:
    """Canonical normalized OHLCV market candle."""

    exchange: str
    symbol: str
    timeframe: str
    timestamp: datetime

    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
