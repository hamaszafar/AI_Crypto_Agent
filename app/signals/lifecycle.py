import enum

class SignalState(enum.Enum):
    """Lifecycle states for a generated signal.

    - GENERATED: just created by the orchestrator.
    - ACTIVE: being used for trading decisions.
    - EXPIRED: no longer relevant (e.g., older than retention window).
    """
    GENERATED = "generated"
    ACTIVE = "active"
    EXPIRED = "expired"

def valid_transition(current: SignalState, next_state: SignalState) -> bool:
    """Return ``True`` if moving from ``current`` to ``next_state`` is allowed.

    Rules:
        GENERATED -> ACTIVE
        ACTIVE -> EXPIRED
        (any state -> same state) is a no‑op and allowed.
    """
    if current == next_state:
        return True
    allowed = {
        SignalState.GENERATED: {SignalState.ACTIVE},
        SignalState.ACTIVE: {SignalState.EXPIRED},
    }
    return next_state in allowed.get(current, set())
