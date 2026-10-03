from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from typing import Optional, Dict, Any, Sequence

from app.backtesting.datasets.exceptions import (
    DatasetValidationError,
    InvalidDatasetRangeError,
    InvalidDatasetTimestampError,
)
from app.market_data.models import MarketCandle


@dataclass(frozen=True, slots=True)
class DatasetMetadata:
    """Metadata describing a historical dataset.

    Fields are minimal, explicit, and deterministic so that a dataset can be
    uniquely identified and reproduced from the stored representation.
    """

    exchange: str
    symbol: str
    timeframe: str
    start_timestamp: datetime
    end_timestamp: datetime
    candle_count: int
    schema_version: str = "1.0"
    created_at: Optional[datetime] = None
    validation_status: Optional[str] = None

    def __post_init__(self) -> None:
        if self.start_timestamp.tzinfo is None or self.start_timestamp.tzinfo.utcoffset(self.start_timestamp) is None:
            raise InvalidDatasetTimestampError("start_timestamp must be timezone-aware UTC datetime")

        if self.end_timestamp.tzinfo is None or self.end_timestamp.tzinfo.utcoffset(self.end_timestamp) is None:
            raise InvalidDatasetTimestampError("end_timestamp must be timezone-aware UTC datetime")

        if self.created_at is not None:
            if self.created_at.tzinfo is None or self.created_at.tzinfo.utcoffset(self.created_at) is None:
                raise InvalidDatasetTimestampError("created_at must be timezone-aware UTC datetime")

        if self.start_timestamp > self.end_timestamp:
            raise InvalidDatasetRangeError(
                f"start_timestamp ({self.start_timestamp}) cannot be after end_timestamp ({self.end_timestamp})"
            )

        if self.candle_count < 0:
            raise DatasetValidationError(
                f"candle_count cannot be negative, got {self.candle_count}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize metadata to a JSON-compatible dictionary."""
        return {
            "exchange": self.exchange,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "start_timestamp": self.start_timestamp.isoformat(),
            "end_timestamp": self.end_timestamp.isoformat(),
            "candle_count": self.candle_count,
            "schema_version": self.schema_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "validation_status": self.validation_status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatasetMetadata":
        """Deserialize DatasetMetadata from dictionary."""
        start_ts = data["start_timestamp"]
        if isinstance(start_ts, str):
            start_ts = datetime.fromisoformat(start_ts)

        end_ts = data["end_timestamp"]
        if isinstance(end_ts, str):
            end_ts = datetime.fromisoformat(end_ts)

        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        return cls(
            exchange=str(data["exchange"]),
            symbol=str(data["symbol"]),
            timeframe=str(data["timeframe"]),
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            candle_count=int(data["candle_count"]),
            schema_version=str(data.get("schema_version", "1.0")),
            created_at=created_at,
            validation_status=data.get("validation_status"),
        )


def compute_dataset_id(metadata: DatasetMetadata, candles: Sequence[MarketCandle]) -> str:
    """Compute a deterministic, process-independent SHA-256 identifier for a dataset.

    The identity is computed by concatenating metadata attributes and a full
    SHA-256 fingerprint of all contained candle timestamps and OHLCV values.
    """
    candle_fingerprint = hashlib.sha256(
        "|".join(
            f"{c.timestamp.isoformat()}:{c.open}:{c.high}:{c.low}:{c.close}:{c.volume}"
            for c in candles
        ).encode("utf-8")
    ).hexdigest()

    data = {
        "exchange": metadata.exchange.strip().lower(),
        "symbol": metadata.symbol.strip(),
        "timeframe": metadata.timeframe.strip().lower(),
        "start": metadata.start_timestamp.isoformat(),
        "end": metadata.end_timestamp.isoformat(),
        "count": str(metadata.candle_count),
        "candles_hash": candle_fingerprint,
        "schema_version": metadata.schema_version,
    }
    json_repr = "".join(f"{k}:{data[k]}|" for k in sorted(data))
    return hashlib.sha256(json_repr.encode("utf-8")).hexdigest()
