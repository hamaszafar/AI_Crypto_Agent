from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Sequence, List, Optional, Dict, Any

from app.backtesting.datasets.models import HistoricalDataset
from app.backtesting.datasets.metadata import DatasetMetadata
from app.market_data.models import MarketCandle
from app.market_data.validator import is_valid_ohlc, is_valid_volume
from app.market_data.gap_detector import GapDetector, Gap


class ValidationSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class ValidationIssueType(str, Enum):
    TIMESTAMP_INVALID = "TIMESTAMP_INVALID"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    DUPLICATE_TIMESTAMP = "DUPLICATE_TIMESTAMP"
    OHLC_INVALID = "OHLC_INVALID"
    VOLUME_INVALID = "VOLUME_INVALID"
    MIXED_SYMBOLS = "MIXED_SYMBOLS"
    MIXED_TIMEFRAMES = "MIXED_TIMEFRAMES"
    MIXED_EXCHANGES = "MIXED_EXCHANGES"
    BOUNDARY_MISMATCH = "BOUNDARY_MISMATCH"
    GAP_DETECTED = "GAP_DETECTED"
    SUSPICIOUS_PRICE = "SUSPICIOUS_PRICE"


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    issue_type: ValidationIssueType
    severity: ValidationSeverity
    message: str
    timestamp: Optional[datetime] = None
    affected_indices: tuple[int, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_type": self.issue_type.value,
            "severity": self.severity.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "affected_indices": list(self.affected_indices),
        }


@dataclass(slots=True)
class DatasetValidationResult:
    is_valid: bool
    status: str  # "VALID", "WARNING", "INVALID"
    dataset_id: Optional[str]
    issues: List[ValidationIssue] = field(default_factory=list)
    candle_count: int = 0
    gaps: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.severity == ValidationSeverity.WARNING]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "status": self.status,
            "dataset_id": self.dataset_id,
            "candle_count": self.candle_count,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "gap_count": len(self.gaps),
            "issues": [i.to_dict() for i in self.issues],
            "gaps": self.gaps,
        }


class HistoricalDatasetValidator:
    """Dedicated validator for historical market datasets before backtesting.

    Detects quality issues (invalid OHLCV, duplicates, out-of-order, mixed metadata,
    gaps, price anomalies) without mutating or silently discarding data.
    """

    def __init__(self, price_change_threshold_pct: Decimal = Decimal("50.0")):
        self.price_change_threshold_pct = price_change_threshold_pct

    def validate(self, dataset: HistoricalDataset) -> DatasetValidationResult:
        """Validate a HistoricalDataset instance."""
        return self.validate_raw(candles=dataset.candles, metadata=dataset.metadata, dataset_id=dataset.dataset_id)

    def validate_raw(
        self,
        candles: Sequence[MarketCandle],
        metadata: Optional[DatasetMetadata] = None,
        dataset_id: Optional[str] = None,
    ) -> DatasetValidationResult:
        """Validate a sequence of candles and optional metadata, accumulating all issues."""
        issues: List[ValidationIssue] = []
        detected_gaps: List[Dict[str, Any]] = []

        if not candles:
            issues.append(
                ValidationIssue(
                    issue_type=ValidationIssueType.BOUNDARY_MISMATCH,
                    severity=ValidationSeverity.ERROR,
                    message="Candle dataset is empty",
                )
            )
            return DatasetValidationResult(
                is_valid=False,
                status="INVALID",
                dataset_id=dataset_id,
                issues=issues,
                candle_count=0,
                gaps=[],
            )

        first = candles[0]
        expected_exchange = first.exchange
        expected_symbol = first.symbol
        expected_timeframe = first.timeframe

        seen_timestamps: dict[datetime, int] = {}

        for idx, candle in enumerate(candles):
            # 1. Timestamp validity check
            if not isinstance(candle.timestamp, datetime) or candle.timestamp.tzinfo is None or candle.timestamp.tzinfo.utcoffset(candle.timestamp) is None:
                issues.append(
                    ValidationIssue(
                        issue_type=ValidationIssueType.TIMESTAMP_INVALID,
                        severity=ValidationSeverity.ERROR,
                        message=f"Candle at index {idx} has invalid or naive timestamp: {candle.timestamp}",
                        timestamp=candle.timestamp if isinstance(candle.timestamp, datetime) else None,
                        affected_indices=(idx,),
                    )
                )

            # 2. OHLC validity
            if not is_valid_ohlc(candle):
                issues.append(
                    ValidationIssue(
                        issue_type=ValidationIssueType.OHLC_INVALID,
                        severity=ValidationSeverity.ERROR,
                        message=f"Invalid OHLC relationship at index {idx}: open={candle.open}, high={candle.high}, low={candle.low}, close={candle.close}",
                        timestamp=candle.timestamp,
                        affected_indices=(idx,),
                    )
                )

            # 3. Volume validity
            if not is_valid_volume(candle):
                issues.append(
                    ValidationIssue(
                        issue_type=ValidationIssueType.VOLUME_INVALID,
                        severity=ValidationSeverity.ERROR,
                        message=f"Invalid volume at index {idx}: volume={candle.volume}",
                        timestamp=candle.timestamp,
                        affected_indices=(idx,),
                    )
                )

            # 4. Exchange consistency
            if candle.exchange != expected_exchange:
                issues.append(
                    ValidationIssue(
                        issue_type=ValidationIssueType.MIXED_EXCHANGES,
                        severity=ValidationSeverity.ERROR,
                        message=f"Inconsistent exchange at index {idx}: expected '{expected_exchange}', got '{candle.exchange}'",
                        timestamp=candle.timestamp,
                        affected_indices=(idx,),
                    )
                )

            # 5. Symbol consistency
            if candle.symbol != expected_symbol:
                issues.append(
                    ValidationIssue(
                        issue_type=ValidationIssueType.MIXED_SYMBOLS,
                        severity=ValidationSeverity.ERROR,
                        message=f"Inconsistent symbol at index {idx}: expected '{expected_symbol}', got '{candle.symbol}'",
                        timestamp=candle.timestamp,
                        affected_indices=(idx,),
                    )
                )

            # 6. Timeframe consistency
            if candle.timeframe != expected_timeframe:
                issues.append(
                    ValidationIssue(
                        issue_type=ValidationIssueType.MIXED_TIMEFRAMES,
                        severity=ValidationSeverity.ERROR,
                        message=f"Inconsistent timeframe at index {idx}: expected '{expected_timeframe}', got '{candle.timeframe}'",
                        timestamp=candle.timestamp,
                        affected_indices=(idx,),
                    )
                )

            # 7. Duplicate timestamp check
            if candle.timestamp in seen_timestamps:
                prev_idx = seen_timestamps[candle.timestamp]
                issues.append(
                    ValidationIssue(
                        issue_type=ValidationIssueType.DUPLICATE_TIMESTAMP,
                        severity=ValidationSeverity.ERROR,
                        message=f"Duplicate timestamp detected at index {idx} (first seen at index {prev_idx}): {candle.timestamp}",
                        timestamp=candle.timestamp,
                        affected_indices=(prev_idx, idx),
                    )
                )
            else:
                seen_timestamps[candle.timestamp] = idx

        # 8. Chronological ordering & Price anomaly checks between consecutive candles
        for idx in range(1, len(candles)):
            prev = candles[idx - 1]
            curr = candles[idx]

            if curr.timestamp < prev.timestamp:
                issues.append(
                    ValidationIssue(
                        issue_type=ValidationIssueType.OUT_OF_ORDER,
                        severity=ValidationSeverity.ERROR,
                        message=f"Out-of-order candles at index {idx}: timestamp {curr.timestamp} is earlier than previous {prev.timestamp}",
                        timestamp=curr.timestamp,
                        affected_indices=(idx - 1, idx),
                    )
                )

            # Suspicious price anomaly (> threshold % change from previous close to current close)
            if prev.close > Decimal("0") and curr.close > Decimal("0"):
                diff = abs(curr.close - prev.close)
                pct_change = (diff / prev.close) * Decimal("100")
                if pct_change >= self.price_change_threshold_pct:
                    issues.append(
                        ValidationIssue(
                            issue_type=ValidationIssueType.SUSPICIOUS_PRICE,
                            severity=ValidationSeverity.WARNING,
                            message=f"Suspicious price change of {pct_change:.2f}% detected between index {idx-1} ({prev.close}) and index {idx} ({curr.close})",
                            timestamp=curr.timestamp,
                            affected_indices=(idx - 1, idx),
                        )
                    )

        # 9. Metadata boundary validation
        if metadata:
            if metadata.exchange != expected_exchange:
                issues.append(
                    ValidationIssue(
                        issue_type=ValidationIssueType.MIXED_EXCHANGES,
                        severity=ValidationSeverity.ERROR,
                        message=f"Metadata exchange '{metadata.exchange}' does not match candle exchange '{expected_exchange}'",
                    )
                )
            if metadata.symbol != expected_symbol:
                issues.append(
                    ValidationIssue(
                        issue_type=ValidationIssueType.MIXED_SYMBOLS,
                        severity=ValidationSeverity.ERROR,
                        message=f"Metadata symbol '{metadata.symbol}' does not match candle symbol '{expected_symbol}'",
                    )
                )
            if metadata.timeframe != expected_timeframe:
                issues.append(
                    ValidationIssue(
                        issue_type=ValidationIssueType.MIXED_TIMEFRAMES,
                        severity=ValidationSeverity.ERROR,
                        message=f"Metadata timeframe '{metadata.timeframe}' does not match candle timeframe '{expected_timeframe}'",
                    )
                )
            if metadata.start_timestamp != first.timestamp:
                issues.append(
                    ValidationIssue(
                        issue_type=ValidationIssueType.BOUNDARY_MISMATCH,
                        severity=ValidationSeverity.ERROR,
                        message=f"Metadata start_timestamp ({metadata.start_timestamp}) does not match first candle timestamp ({first.timestamp})",
                        timestamp=metadata.start_timestamp,
                        affected_indices=(0,),
                    )
                )
            if metadata.end_timestamp != candles[-1].timestamp:
                issues.append(
                    ValidationIssue(
                        issue_type=ValidationIssueType.BOUNDARY_MISMATCH,
                        severity=ValidationSeverity.ERROR,
                        message=f"Metadata end_timestamp ({metadata.end_timestamp}) does not match last candle timestamp ({candles[-1].timestamp})",
                        timestamp=metadata.end_timestamp,
                        affected_indices=(len(candles) - 1,),
                    )
                )
            if metadata.candle_count != len(candles):
                issues.append(
                    ValidationIssue(
                        issue_type=ValidationIssueType.BOUNDARY_MISMATCH,
                        severity=ValidationSeverity.ERROR,
                        message=f"Metadata candle_count ({metadata.candle_count}) does not match actual candle count ({len(candles)})",
                    )
                )

        # 10. Gap detection
        try:
            detected_raw_gaps = GapDetector.detect_gaps(candles, expected_timeframe)
            for g in detected_raw_gaps:
                gap_dict = {
                    "start_time": g.start_time.isoformat(),
                    "end_time": g.end_time.isoformat(),
                    "missing_count": g.missing_count,
                }
                detected_gaps.append(gap_dict)
                issues.append(
                    ValidationIssue(
                        issue_type=ValidationIssueType.GAP_DETECTED,
                        severity=ValidationSeverity.WARNING,
                        message=f"Detected gap of {g.missing_count} missing candle(s) between {g.start_time} and {g.end_time}",
                        timestamp=g.start_time,
                    )
                )
        except Exception:
            pass  # Gap detection optional if timeframe not supported

        has_errors = any(i.severity == ValidationSeverity.ERROR for i in issues)
        has_warnings = any(i.severity == ValidationSeverity.WARNING for i in issues)

        if has_errors:
            status = "INVALID"
            is_valid = False
        elif has_warnings:
            status = "WARNING"
            is_valid = True
        else:
            status = "VALID"
            is_valid = True

        return DatasetValidationResult(
            is_valid=is_valid,
            status=status,
            dataset_id=dataset_id,
            issues=issues,
            candle_count=len(candles),
            gaps=detected_gaps,
        )
