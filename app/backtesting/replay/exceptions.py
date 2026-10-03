class ReplayError(Exception):
    """Base class for replay-related errors."""
    pass

class ReplayInitializationError(ReplayError):
    """Raised when the replay engine fails to initialize properly."""
    pass

class ReplayFinishedError(ReplayError):
    """Raised when an attempt is made to step forward after replay has finished."""
    pass

class InvalidReplayRequestError(ReplayError):
    """Raised when the provided replay request configuration is invalid."""
    pass
