from __future__ import annotations

from decimal import Decimal
from typing import Mapping, Sequence

from app.signals.models import ReasonCode, SignalEvidence


class ConditionEngine:
    """Stateless helper that turns raw indicator results into evidence.

    The method ``evaluate`` receives a mapping of indicator name → Decimal value and
    returns a list of :class:`SignalEvidence` objects according to a deterministic
    rule‑set. The rule‑set mirrors the examples from the Phase 4 specification
    (trend, momentum, volatility, volume, cross‑exchange). Unknown indicators are
    ignored (no evidence added). This class can be extended with more sophisticated
    condition categories without affecting the deterministic nature of the engine.
    """

    @staticmethod
    def _evidence(reason: ReasonCode, magnitude: Decimal, details: str | None = None) -> SignalEvidence:
        return SignalEvidence(reason=reason, value=magnitude, details=details)

    def evaluate(self, indicators: Mapping[str, Decimal]) -> Sequence[SignalEvidence]:
        evidences: list[SignalEvidence] = []
        for name, value in indicators.items():
            # ------- Trend conditions ------------------------------------------------
            if name == "ema_fast_vs_slow":
                # Positive means fast EMA above slow EMA -> bullish
                reason = ReasonCode.BULLISH_EMA_ALIGNMENT if value > 0 else ReasonCode.BEARISH_EMA_ALIGNMENT
                evidences.append(self._evidence(reason, Decimal('0.4') * (1 if value > 0 else -1)))
            elif name == "macd":
                reason = ReasonCode.MACD_BULLISH if value > 0 else ReasonCode.MACD_BEARISH
                evidences.append(self._evidence(reason, Decimal('0.2') * (1 if value > 0 else -1)))
            # ------- Momentum conditions -------------------------------------------
            elif name == "rsi":
                if value >= Decimal('70'):
                    evidences.append(self._evidence(ReasonCode.RSI_OVERBOUGHT, Decimal('-0.3')))
                elif value <= Decimal('30'):
                    evidences.append(self._evidence(ReasonCode.RSI_OVERSOLD, Decimal('0.3')))
            # ------- Volume conditions ----------------------------------------------
            elif name == "volume_vs_avg":
                if value > 0:
                    evidences.append(self._evidence(ReasonCode.VOLUME_ABOVE_AVG, Decimal('0.2')))
                else:
                    evidences.append(self._evidence(ReasonCode.VOLUME_BELOW_AVG, Decimal('-0.2')))
            # ------- Volatility conditions ------------------------------------------
            elif name == "atr_expansion":
                evidences.append(self._evidence(ReasonCode.HIGH_VOLATILITY, Decimal('0.2')))
            elif name == "atr_contraction":
                evidences.append(self._evidence(ReasonCode.LOW_VOLATILITY, Decimal('-0.2')))
            # ------- Cross‑exchange conditions --------------------------------------
            elif name == "exchange_consensus":
                # Positive = bullish consensus, negative = bearish
                if value > 0:
                    evidences.append(self._evidence(ReasonCode.CROSS_EXCHANGE_BULLISH, Decimal('0.3')))
                else:
                    evidences.append(self._evidence(ReasonCode.CROSS_EXCHANGE_BEARISH, Decimal('-0.3')))
            # ------- Unknown / not‑handled indicators -------------------------------
            else:
                # No evidence for unknown indicators – keep deterministic
                continue
        return evidences
