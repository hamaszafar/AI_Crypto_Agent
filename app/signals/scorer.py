from __future__ import annotations

from decimal import Decimal
from typing import Mapping, Sequence

from app.signals.models import ReasonCode, SignalEvidence


class Scorer:
    """Score a list of evidences using configurable weights.

    The default weight for any reason code is ``Decimal('1')``. Users can supply
    a ``weights`` mapping to override individual reason weights.
    """

    def __init__(self, weights: Mapping[ReasonCode, Decimal] | None = None) -> None:
        self.weights: Mapping[ReasonCode, Decimal] = weights or {}

    def weight_for(self, reason: ReasonCode) -> Decimal:
        return self.weights.get(reason, Decimal('1'))

    def score(self, evidences: Sequence[SignalEvidence]) -> Decimal:
        """Return the aggregate score.

        Each evidence contributes ``evidence.value * weight``. Positive values are
        bullish, negative values are bearish.
        """
        total = Decimal('0')
        for ev in evidences:
            total += ev.value * self.weight_for(ev.reason)
        return total

    def max_possible(self, evidences: Sequence[SignalEvidence]) -> Decimal:
        """Compute the theoretical maximum absolute score for the given evidences.

        This is useful for confidence calculation.
        """
        total = Decimal('0')
        for ev in evidences:
            total += abs(ev.value) * self.weight_for(ev.reason)
        return total
