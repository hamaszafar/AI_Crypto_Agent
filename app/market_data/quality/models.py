from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class DataQualityStatus(str, Enum):
    """Overall status of data quality check."""
    VALID = "VALID"
    WARNING = "WARNING"
    INVALID = "INVALID"


@dataclass(frozen=True, slots=True)
class NormalizationConfig:
    """
    Configuration options for data quality checks and normalization.
    """
    allowed_timeframes: tuple[str, ...] = ("15m", "1h", "4h", "1d")
    allowed_symbols: tuple[str, ...] | None = None
    future_timestamp_tolerance_seconds: float = 5.0
    stale_data_threshold_seconds: float = 86400.0
    max_price_deviation_percent: Decimal = Decimal("5.0")
    duplicate_policy: str = "retain_first"  # "retain_first" or "strict"
    gap_policy: str = "report"  # "ignore", "report", or "reject"


@dataclass(slots=True)
class DataQualityResult:
    """
    Structured summary of a data quality pipeline run.
    """
    is_valid: bool = True
    status: DataQualityStatus = DataQualityStatus.VALID
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duplicate_count: int = 0
    gap_count: int = 0
    stale: bool = False
    future_timestamp_detected: bool = False
    consistency_issues: list[str] = field(default_factory=list)
    candle_count: int = 0
