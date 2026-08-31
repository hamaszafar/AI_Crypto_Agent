from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.market_data.normalization.candle import validate_candle_fields


@dataclass(frozen=True, slots=True)
class MarketCandle:
    """
    Canonical normalized OHLCV market candle.

    Immutable dataclass enforcing strict contracts upon initialization:
    - exchange: normalized lowercase string (e.g., "binance")
    - symbol: canonical BASE/QUOTE string (e.g., "BTC/USDT")
    - timeframe: canonical timeframe string ("15m", "1h", "4h", "1d")
    - timestamp: timezone-aware UTC datetime
    - open, high, low, close: positive finite Decimal
    - volume: non-negative finite Decimal
    """

    exchange: str
    symbol: str
    timeframe: str
    timestamp: datetime

    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal

    def __post_init__(self) -> None:
        validate_candle_fields(
            exchange=self.exchange,
            symbol=self.symbol,
            timeframe=self.timeframe,
            timestamp=self.timestamp,
            open_price=self.open,
            high_price=self.high,
            low_price=self.low,
            close_price=self.close,
            volume=self.volume,
        )
