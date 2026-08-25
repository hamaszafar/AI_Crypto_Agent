from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.exchanges.types import Symbol, Timeframe

@dataclass(frozen=True)
class Candle:
    """ Standard OHLCV candle used across exchanges.
    """
    exchange: str 
    symbol: Symbol 
    timeframe: Timeframe
    timestamp: datetime

    open: Decimal
    high: Decimal 
    low: Decimal
    close: Decimal
    volume: Decimal
