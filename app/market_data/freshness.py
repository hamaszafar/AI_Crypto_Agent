from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from app.market_data.gap_detector import GapDetector


class FreshnessState(str, Enum):
    FRESH = "FRESH"
    DELAYED = "DELAYED"
    STALE = "STALE"


@dataclass(frozen=True)
class FreshnessResult:
    """
    Evaluation result of market-data freshness.
    """

    exchange: str
    symbol: str
    timeframe: str
    latest_timestamp: datetime | None
    delay_seconds: float | None
    state: FreshnessState


class FreshnessMonitor:
    """
    Monitors data freshness per exchange/symbol/timeframe.
    """

    def __init__(
        self,
        fresh_multiplier: float = 2.0,
        delayed_multiplier: float = 5.0,
    ) -> None:
        if fresh_multiplier <= 0:
            raise ValueError("fresh_multiplier must be greater than zero")
        if delayed_multiplier <= fresh_multiplier:
            raise ValueError("delayed_multiplier must be greater than fresh_multiplier")

        self.fresh_mult = fresh_multiplier
        self.delayed_mult = delayed_multiplier

    def evaluate(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        latest_timestamp: datetime | None,
        now: datetime | None = None,
    ) -> FreshnessResult:
        if latest_timestamp is None:
            return FreshnessResult(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                latest_timestamp=None,
                delay_seconds=None,
                state=FreshnessState.STALE,
            )

        current_time = now or datetime.now(timezone.utc)
        delay = (current_time - latest_timestamp).total_seconds()
        if delay < 0:
            delay = 0.0

        step_seconds = GapDetector.get_step(timeframe).total_seconds()
        fresh_cutoff = step_seconds * self.fresh_mult
        delayed_cutoff = step_seconds * self.delayed_mult

        if delay <= fresh_cutoff:
            state = FreshnessState.FRESH
        elif delay <= delayed_cutoff:
            state = FreshnessState.DELAYED
        else:
            state = FreshnessState.STALE

        return FreshnessResult(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            latest_timestamp=latest_timestamp,
            delay_seconds=delay,
            state=state,
        )
