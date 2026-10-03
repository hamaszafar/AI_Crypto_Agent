class LeakageError(Exception):
    """Base exception for all leakage guard violations."""
    pass

class FutureDataDetectedError(LeakageError):
    """Raised when a future candle is detected in a context window (candle.timestamp > replay_timestamp)."""
    pass

class InvalidReplayTimestampError(LeakageError):
    """Raised when the replay timestamp used for validation is invalid (e.g., missing timezone)."""
    pass
