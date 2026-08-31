from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping, Sequence

from app.signals.models import (
    Signal,
    SignalDirection,
    SignalStrength,
    SignalConfidence,
    SignalEvidence,
    SignalContext,
    ReasonCode,
)
from app.signals.conditions import ConditionEngine
from app.signals.scorer import Scorer
from app.signals.confidence import ConfidenceEngine


@dataclass(frozen=True)
class SignalConfig:
    """Configuration for the signal engine.

    Attributes:
        buy_threshold: Minimum score to emit a BUY.
        sell_threshold: Maximum score (negative) to emit a SELL.
        weights: Optional per‑ReasonCode weight overrides.
    """

    buy_threshold: Decimal = Decimal('0.5')
    sell_threshold: Decimal = Decimal('-0.5')
    weights: Mapping[ReasonCode, Decimal] | None = None

    def __post_init__(self) -> None:
        if self.buy_threshold <= self.sell_threshold:
            raise ValueError('buy_threshold must be greater than sell_threshold')


class SignalEngine:
    """High‑level service that produces a :class:`Signal` from raw indicator data.

    The engine is fully deterministic:

    * ``ConditionEngine`` turns indicator values into a list of ``SignalEvidence``.
    * ``Scorer`` aggregates those evidences using optional per‑reason weights.
    * ``ConfidenceEngine`` derives a confidence level from the score ratio.
    * The final direction/strength is decided by configurable thresholds.
    """

    def __init__(self, config: SignalConfig | None = None) -> None:
        self.config = config or SignalConfig()
        self.condition_engine = ConditionEngine()
        self.scorer = Scorer(self.config.weights)
        self.confidence_engine = ConfidenceEngine(self.scorer)

    # ---------------------------------------------------------------------
    @staticmethod
    def _direction_and_strength(score: Decimal, cfg: SignalConfig) -> tuple[SignalDirection, SignalStrength]:
        if score >= cfg.buy_threshold:
            direction = SignalDirection.BUY
            if score >= Decimal('1'):
                strength = SignalStrength.STRONG
            elif score >= Decimal('0.75'):
                strength = SignalStrength.MODERATE
            else:
                strength = SignalStrength.WEAK
        elif score <= cfg.sell_threshold:
            direction = SignalDirection.SELL
            if score <= Decimal('-1'):
                strength = SignalStrength.STRONG
            elif score <= Decimal('-0.75'):
                strength = SignalStrength.MODERATE
            else:
                strength = SignalStrength.WEAK
        else:
            direction = SignalDirection.HOLD
            strength = SignalStrength.NEUTRAL
        return direction, strength

    # ---------------------------------------------------------------------
    def generate(self, indicators: Mapping[str, Decimal], context: SignalContext) -> Signal:
        """Generate a :class:`Signal`.

        * ``indicators`` – mapping of indicator name → Decimal value (e.g. the output of
          the IndicatorEngine for a single timeframe).
        * ``context`` – ``SignalContext`` describing symbol, exchange, timeframe, etc.
        """
        evidences = list(self.condition_engine.evaluate(indicators))
        total_score = self.scorer.score(evidences)
        # Regime‑aware adjustment (deterministic tweak)
        if context.market_regime:
            from app.analysis.market_regime import MarketRegime
            if context.market_regime == MarketRegime.HIGH_VOLATILITY:
                total_score *= Decimal('0.8')
            elif context.market_regime == MarketRegime.LOW_VOLATILITY:
                total_score *= Decimal('1.2')
        direction, strength = self._direction_and_strength(total_score, self.config)
        confidence = self.confidence_engine.confidence(evidences)
        return Signal(
            direction=direction,
            strength=strength,
            confidence=confidence,
            score=total_score,
            context=context,
            evidences=tuple(evidences),
        )
