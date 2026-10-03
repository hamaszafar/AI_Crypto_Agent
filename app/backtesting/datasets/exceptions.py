from app.market_data.exceptions import CandleValidationError


class DatasetValidationError(ValueError):
    """Base exception for historical dataset validation errors."""


class EmptyDatasetError(DatasetValidationError):
    """Raised when a historical dataset is empty."""


class InvalidDatasetTimestampError(DatasetValidationError, CandleValidationError):
    """Raised when candle timestamps in dataset are invalid or timezone-naive."""


class NonChronologicalCandlesError(DatasetValidationError):
    """Raised when candles are not strictly chronological."""


class DuplicateTimestampError(DatasetValidationError):
    """Raised when duplicate timestamps exist in dataset."""


class MixedSymbolsError(DatasetValidationError):
    """Raised when candles or metadata contain inconsistent symbols."""


class MixedTimeframesError(DatasetValidationError):
    """Raised when candles or metadata contain inconsistent timeframes."""


class MixedExchangesError(DatasetValidationError):
    """Raised when candles or metadata contain inconsistent exchanges."""


class InvalidDatasetRangeError(DatasetValidationError):
    """Raised when start_timestamp > end_timestamp or boundary metadata mismatches."""


class InvalidOHLCVDataError(DatasetValidationError):
    """Raised when candle OHLC or volume data is invalid."""


class DatasetLoadError(Exception):
    """Base exception for data loader errors."""


class IncompleteDataError(DatasetLoadError):
    """Raised when data loaded does not cover the requested range."""


class NoDataError(DatasetLoadError):
    """Raised when no data is found."""


class InvalidDateRangeError(DatasetLoadError):
    """Raised when start_time >= end_time or datetimes are invalid/naive."""


class UnsupportedSymbolError(DatasetLoadError):
    """Raised when a symbol is invalid or unsupported."""


class UnsupportedTimeframeError(DatasetLoadError):
    """Raised when a timeframe is invalid or unsupported."""


class UnavailableSourceError(DatasetLoadError):
    """Raised when exchange source is invalid, empty, or unavailable."""
