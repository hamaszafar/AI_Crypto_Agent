from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence

from app.market_data.models import MarketCandle

TIMEFRAME_DELTAS: dict[str, timedelta] = {
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "1d": timedelta(days=1),
}


@dataclass(frozen=True, slots=True)
class CandleGapInfo:
    """Detailed information about a gap between candles."""
    exchange: str
    symbol: str
    timeframe: str
    expected_timestamp: datetime
    previous_timestamp: datetime
    next_timestamp: datetime
    missing_count: int


def find_candle_gaps(
    candles: Sequence[MarketCandle],
    timeframe: str | None = None,
) -> list[CandleGapInfo]:
    """
    Detect missing intervals between candles in a sequence.

    Args:
        candles: Sequence of MarketCandle objects (assumed sorted chronologically).
        timeframe: Optional timeframe override; uses candle.timeframe if None.

    Returns:
        List of CandleGapInfo objects representing detected gaps.
    """
    if len(candles) < 2:
        return []

    tf = timeframe or candles[0].timeframe
    if tf not in TIMEFRAME_DELTAS:
        return []

    delta = TIMEFRAME_DELTAS[tf]
    gaps: list[CandleGapInfo] = []

    for i in range(len(candles) - 1):
        curr_candle = candles[i]
        next_candle = candles[i + 1]

        expected_ts = curr_candle.timestamp + delta
        if next_candle.timestamp > expected_ts:
            diff = next_candle.timestamp - curr_candle.timestamp
            missing_count = int(diff / delta) - 1
            if missing_count > 0:
                gaps.append(
                    CandleGapInfo(
                        exchange=curr_candle.exchange,
                        symbol=curr_candle.symbol,
                        timeframe=tf,
                        expected_timestamp=expected_ts,
                        previous_timestamp=curr_candle.timestamp,
                        next_timestamp=next_candle.timestamp,
                        missing_count=missing_count,
                    )
                )

    return gaps
