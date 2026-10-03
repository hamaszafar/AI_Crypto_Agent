"""
Phase 6C.2 — Outcome Evaluation Configuration.

OutcomeEvaluationConfig controls how the SignalOutcomeTracker evaluates
each active signal against subsequent candles.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TP_SL_AMBIGUITY_SL_WINS: str = "sl_wins"
TP_SL_AMBIGUITY_TP_WINS: str = "tp_wins"
_VALID_AMBIGUITY_RULES = frozenset({TP_SL_AMBIGUITY_SL_WINS, TP_SL_AMBIGUITY_TP_WINS})


@dataclass(frozen=True, slots=True)
class OutcomeEvaluationConfig:
    """
    Configuration that governs how the SignalOutcomeTracker resolves signal outcomes.

    Attributes:
        breakeven_threshold:
            Fractional distance from entry_price within which a resolved exit_price
            is classified as BREAKEVEN rather than WIN or LOSS.
            E.g. Decimal("0.001") means exits within 0.1% of entry → BREAKEVEN.
            Decimal("0") disables breakeven detection (default).

        max_candles:
            Maximum number of candles (after and including the registration candle)
            to evaluate a signal before forcibly resolving it as EXPIRED.
            None means the signal never expires automatically (flush_expired must
            be called explicitly to expire remaining signals at end-of-replay).

        tp_sl_ambiguity_rule:
            Determines priority when a single candle simultaneously touches both
            Take Profit and Stop Loss:
              "sl_wins" (default) — resolve as LOSS.  Conservative; mirrors the
                real-market assumption that a stop is triggered before a TP fill.
              "tp_wins" — resolve as WIN.

    TP/SL Ambiguity Rule:
        When a candle's low <= SL and high >= TP (for a BUY), or the symmetric
        case for a SELL, the rule is inherently ambiguous.  This config lets
        callers choose a deterministic policy rather than guessing.  The default
        "sl_wins" is the more conservative choice.
    """

    breakeven_threshold: Decimal = Decimal("0")
    max_candles: Optional[int] = None
    tp_sl_ambiguity_rule: str = TP_SL_AMBIGUITY_SL_WINS

    def __post_init__(self) -> None:
        if not isinstance(self.breakeven_threshold, Decimal):
            try:
                object.__setattr__(
                    self, "breakeven_threshold", Decimal(str(self.breakeven_threshold))
                )
            except Exception as exc:
                raise ValueError(
                    "breakeven_threshold must be convertible to Decimal"
                ) from exc

        if self.breakeven_threshold < Decimal("0"):
            raise ValueError(
                f"breakeven_threshold must be >= 0, got {self.breakeven_threshold}"
            )

        if self.max_candles is not None:
            if not isinstance(self.max_candles, int) or self.max_candles < 1:
                raise ValueError(
                    f"max_candles must be a positive integer or None, got {self.max_candles}"
                )

        if self.tp_sl_ambiguity_rule not in _VALID_AMBIGUITY_RULES:
            raise ValueError(
                f"tp_sl_ambiguity_rule must be one of {sorted(_VALID_AMBIGUITY_RULES)}, "
                f"got {self.tp_sl_ambiguity_rule!r}"
            )
