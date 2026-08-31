class CandleValidationError(ValueError):
    """Base exception for all market candle validation errors."""


class InvalidExchangeError(CandleValidationError):
    """Raised when exchange name is invalid or malformed."""


class InvalidSymbolError(CandleValidationError):
    """Raised when symbol format is invalid or malformed."""


class InvalidTimeframeError(CandleValidationError):
    """Raised when timeframe is invalid or unsupported."""


class InvalidTimestampError(CandleValidationError):
    """Raised when timestamp is invalid, naive, or malformed."""


class InvalidOHLCError(CandleValidationError):
    """Raised when OHLC price relationships or values are invalid."""


class InvalidVolumeError(CandleValidationError):
    """Raised when volume is invalid or negative."""


class DuplicateCandleError(CandleValidationError):
    """Raised when duplicate candles are detected in strict mode."""


class CandleGapError(CandleValidationError):
    """Raised when candle gaps are detected in strict mode."""


class FutureTimestampError(CandleValidationError):
    """Raised when a candle timestamp is beyond future tolerance."""


class ExchangeConsistencyError(CandleValidationError):
    """Raised when cross-exchange data consistency check fails."""
