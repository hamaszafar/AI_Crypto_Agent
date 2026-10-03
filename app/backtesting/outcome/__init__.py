"""
Phase 6C.2 — Signal Outcome Tracking public package.
"""

from app.backtesting.outcome.config import (
    OutcomeEvaluationConfig,
    TP_SL_AMBIGUITY_SL_WINS,
    TP_SL_AMBIGUITY_TP_WINS,
)
from app.backtesting.outcome.exceptions import (
    OutcomeTrackerError,
    SignalAlreadyRegisteredError,
    OutcomeTrackerStateError,
)
from app.backtesting.outcome.tracker import SignalOutcomeTracker

__all__ = [
    # Config
    "OutcomeEvaluationConfig",
    "TP_SL_AMBIGUITY_SL_WINS",
    "TP_SL_AMBIGUITY_TP_WINS",
    # Exceptions
    "OutcomeTrackerError",
    "SignalAlreadyRegisteredError",
    "OutcomeTrackerStateError",
    # Tracker
    "SignalOutcomeTracker",
]
