from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from app.signals.models import SignalConfidence, SignalEvidence, ReasonCode
from app.signals.scorer import Scorer


class ConfidenceEngine:
    """Calculate a confidence level for a set of evidences.

    The confidence is derived from the ratio of the absolute score to the
    theoretical maximum possible score (taking configured weights into account).
    Additional heuristics can be added later (e.g., regime, data‑quality, multi‑
    timeframe confluence). For now it follows a simple tiered mapping:

    * >= 0.75 → HIGH
    * >= 0.5  → MEDIUM
    * > 0    → LOW
    * else    → UNKNOWN
    """

    def __init__(self, scorer: Scorer | None = None) -> None:
        self.scorer = scorer or Scorer()

    def confidence(self, evidences: Sequence[SignalEvidence]) -> SignalConfidence:
        if not evidences:
            return SignalConfidence.UNKNOWN
        score = self.scorer.score(evidences)
        max_score = self.scorer.max_possible(evidences)
        if max_score == 0:
            return SignalConfidence.UNKNOWN
        ratio = abs(score) / max_score
        if ratio >= Decimal('0.75'):
            return SignalConfidence.HIGH
        if ratio >= Decimal('0.5'):
            return SignalConfidence.MEDIUM
        if ratio > 0:
            return SignalConfidence.LOW
        return SignalConfidence.UNKNOWN
