"""
Phase 6C.2 — Signal Outcome Tracker Exceptions.

These exceptions cover the tracker's own operational error domain and are
intentionally distinct from the contract-level InvalidSignalOutcomeError.
"""


class OutcomeTrackerError(ValueError):
    """Base exception for Signal Outcome Tracker operational errors."""

    pass


class SignalAlreadyRegisteredError(OutcomeTrackerError):
    """
    Raised when a caller attempts to register a signal_id that is already
    present in the active tracking table.

    Each signal_id must be unique within a single tracker instance.
    """

    pass


class OutcomeTrackerStateError(OutcomeTrackerError):
    """
    Raised when the tracker is used in an inconsistent or invalid state,
    e.g. calling flush_expired with a timestamp that pre-dates registered signals.
    """

    pass
