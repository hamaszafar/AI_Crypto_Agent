from __future__ import annotations

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
from app.signals.scorer import Scorer
from app.signals.confidence import ConfidenceEngine


class SignalGenerator:
    """High‑level service that builds a :class:`Signal` from market intelligence.

    The implementation is deliberately simple but deterministic:

    * For every known indicator present in the ``intelligence`` mapping we add a
      ``SignalEvidence`` with a small signed ``value``.
    * Positive values represent bullish evidence, negative values bearish.
    * The ``Scorer`` aggregates the values (using optional per‑reason weights).
    * The final ``direction`` is derived from the sign of the total score and
      mapped to a ``SignalStrength`` tier.
    * ``ConfidenceEngine`` supplies a confidence level based on the ratio of the
      absolute score to the maximum possible magnitude.
    * All contextual fields are taken from the supplied ``context`` argument.

    This engine is deterministic, configurable via ``Scorer`` weights and
    thresholds, and provides full explainability via the ``evidences`` list and
    derived ``reasons``.
    """

    # Default thresholds – can be overridden via constructor arguments.
    BUY_THRESHOLD: Decimal = Decimal('0.5')
    SELL_THRESHOLD: Decimal = Decimal('-0.5')

    def __init__(
        self,
        scorer: Scorer | None = None,
        confidence_engine: ConfidenceEngine | None = None,
        buy_threshold: Decimal | None = None,
        sell_threshold: Decimal | None = None,
    ) -> None:
        self.scorer = scorer or Scorer()
        self.confidence_engine = confidence_engine or ConfidenceEngine(self.scorer)
        if buy_threshold is not None:
            self.BUY_THRESHOLD = buy_threshold
        if sell_threshold is not None:
            self.SELL_THRESHOLD = sell_threshold
        if self.BUY_THRESHOLD <= self.SELL_THRESHOLD:
            raise ValueError('Buy threshold must be greater than sell threshold')

    # ---------------------------------------------------------------------
    # Helper: map a numeric score to direction / strength
    # ---------------------------------------------------------------------
    @staticmethod
    def _direction_and_strength(score: Decimal) -> tuple[SignalDirection, SignalStrength]:
        if score >= SignalGenerator.BUY_THRESHOLD:
            direction = SignalDirection.BUY
            if score >= Decimal('1'):
                strength = SignalStrength.STRONG
            elif score >= Decimal('0.75'):
                strength = SignalStrength.MODERATE
            else:
                strength = SignalStrength.WEAK
        elif score <= SignalGenerator.SELL_THRESHOLD:
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
    # Core generation method
    # ---------------------------------------------------------------------
    def generate(
        self,
        intelligence: Mapping[str, Decimal],
        context: SignalContext,
    ) -> Signal:
        """Create a :class:`Signal` from a mapping of indicator results.

        ``intelligence`` is a simple ``name -> Decimal`` mapping where the key
        matches the indicator name (e.g. ``"ema_fast"``). The generator interprets
        a few well‑known keys; any unknown key is still added as neutral evidence
        with a tiny magnitude so that the engine remains deterministic.
        """
        evidences: list[SignalEvidence] = []
        for name, value in intelligence.items():
            # Basic deterministic rule set – expand as needed.
            if name == "ema_fast_vs_slow":
                reason = ReasonCode.BULLISH_EMA_ALIGNMENT if value > 0 else ReasonCode.BEARISH_EMA_ALIGNMENT
                evidences.append(SignalEvidence(reason, Decimal('0.4') * (1 if value > 0 else -1)))
            elif name == "rsi":
                if value > Decimal('70'):
                    reason = ReasonCode.RSI_OVERBOUGHT
                    evidences.append(SignalEvidence(reason, Decimal('-0.3')))
                elif value < Decimal('30'):
                    reason = ReasonCode.RSI_OVERSOLD
                    evidences.append(SignalEvidence(reason, Decimal('0.3')))
            elif name == "macd":
                if value > 0:
                    reason = ReasonCode.MACD_BULLISH
                else:
                    reason = ReasonCode.MACD_BEARISH
                evidences.append(SignalEvidence(reason, Decimal('0.2') * (1 if value > 0 else -1)))
            elif name == "volume_vs_avg":
                if value > 0:
                    reason = ReasonCode.VOLUME_ABOVE_AVG
                    evidences.append(SignalEvidence(reason, Decimal('0.2')))
                else:
                    reason = ReasonCode.VOLUME_BELOW_AVG
                    evidences.append(SignalEvidence(reason, Decimal('-0.2')))
            else:
                # Fallback – treat as neutral small evidence
                evidences.append(SignalEvidence(ReasonCode.UNKNOWN, Decimal('0')))

        # Scoring and confidence
        total_score = self.scorer.score(evidences)
        direction, strength = self._direction_and_strength(total_score)
        confidence = self.confidence_engine.confidence(evidences)

        # Build final immutable Signal object
        signal = Signal(
            direction=direction,
            strength=strength,
            confidence=confidence,
            score=total_score,
            context=context,
            evidences=tuple(evidences),
        )
        return signal
