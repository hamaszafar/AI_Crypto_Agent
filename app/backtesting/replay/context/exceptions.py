class ContextWindowError(Exception):
    """Base exception for Context Window related errors."""
    pass

class InvalidLookbackError(ContextWindowError):
    """Raised when an invalid lookback size is provided."""
    pass

class FutureDataLeakError(ContextWindowError):
    """Raised if future data is ever detected in the context window. This is a critical security violation."""
    pass
