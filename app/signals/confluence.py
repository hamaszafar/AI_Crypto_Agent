from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Sequence

from app.signals.models import Signal, SignalDirection, SignalStrength, SignalConfidence, ReasonCode, SignalContext
from app.signals.engine import SignalEngine
from app.analysis.market_regime import MarketRegime


class ConfluenceStrength(str, Enum):
    STRONG_BULLISH_ALIGNMENT = "STRONG_BULLISH_ALIGNMENT"
    BULLISH_ALIGNMENT = "BULLISH_ALIGNMENT"
    MIXED = "MIXED"
    BEARISH_ALIGNMENT = "BEARISH_ALIGNMENT"
    STRONG_BEARISH_ALIGNMENT = "STRONG_BEARISH_ALIGNMENT"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class ConfluenceResult:
    """Result of aggregating multiple timeframe signals.

    Attributes:
        overall_direction: The direction after majority voting.
        strength: ConfluenceStrength describing the quality of the alignment.
        signals: The original signals that were aggregated.
    """

    overall_direction: SignalDirection
    strength: ConfluenceStrength
    signals: tuple[Signal, ...]


def aggregate_signals(signals: Sequence[Signal]) -> ConfluenceResult:
    """Aggregate a list of signals from different timeframes.

    The algorithm is deterministic:
    * Count BUY, SELL, HOLD occurrences.
    * The direction with the highest count wins (majority vote).
    * If there is a tie, the result is HOLD with strength MIXED.
    * The strength enum reflects how strong the majority is:
        - 100% of signals same direction → STRONG_*_ALIGNMENT
        - >50% but <100% → *_ALIGNMENT
        - No clear majority → MIXED
        - Empty input → INSUFFICIENT_DATA (defaults to HOLD)
    """
    if not signals:
        return ConfluenceResult(
            overall_direction=SignalDirection.HOLD,
            strength=ConfluenceStrength.INSUFFICIENT_DATA,
            signals=tuple(),
        )

    # Count directions
    counts = {SignalDirection.BUY: 0, SignalDirection.SELL: 0, SignalDirection.HOLD: 0}
    for s in signals:
        counts[s.direction] += 1

    total = sum(counts.values())
    # Determine majority
    sorted_counts = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    top_dir, top_cnt = sorted_counts[0]
    # Check for tie (second count equal to top)
    if total > 0 and top_cnt == sorted_counts[1][1]:
        # Tie – treat as mixed
        return ConfluenceResult(
            overall_direction=SignalDirection.HOLD,
            strength=ConfluenceStrength.MIXED,
            signals=tuple(signals),
        )

    # Determine strength based on percentage
    pct = Decimal(top_cnt) / Decimal(total)
    if pct == Decimal('1'):
        strength = (
            ConfluenceStrength.STRONG_BULLISH_ALIGNMENT
            if top_dir == SignalDirection.BUY
            else ConfluenceStrength.STRONG_BEARISH_ALIGNMENT
            if top_dir == SignalDirection.SELL
            else ConfluenceStrength.MIXED
        )
    elif pct > Decimal('0.5'):
        strength = (
            ConfluenceStrength.BULLISH_ALIGNMENT
            if top_dir == SignalDirection.BUY
            else ConfluenceStrength.BEARISH_ALIGNMENT
            if top_dir == SignalDirection.SELL
            else ConfluenceStrength.MIXED
        )
    else:
        strength = ConfluenceStrength.MIXED

    return ConfluenceResult(
        overall_direction=top_dir,
        strength=strength,
        signals=tuple(signals),
    )
