class TradingSignalException(Exception):
    """Base exception for all application-level errors."""
    def __init__(self, message: str, original_exception: Exception | None = None):
        super().__init__(message)
        self.message = message
        self.original_exception = original_exception

class DependencyError(TradingSignalException):
    """Raised when an external dependency (Database, Redis, Exchange) is unavailable or fails."""

class ConfigurationError(TradingSignalException):
    """Raised when configuration is invalid or missing."""

class TimeoutError(TradingSignalException):
    """Raised when an operation times out."""

class TransientError(TradingSignalException):
    """Raised for temporary failures that might succeed if retried."""

class ValidationError(TradingSignalException):
    """Raised when input data validation fails."""
