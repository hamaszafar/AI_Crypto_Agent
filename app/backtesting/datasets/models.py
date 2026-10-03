from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Tuple, List, Sequence, Any, Dict

from app.market_data.models import MarketCandle
from app.market_data.validator import (
    is_valid_ohlc,
    is_valid_volume,
    is_strictly_chronological,
    has_duplicates,
)
from app.backtesting.datasets.exceptions import (
    DatasetValidationError,
    EmptyDatasetError,
    InvalidDatasetTimestampError,
    NonChronologicalCandlesError,
    DuplicateTimestampError,
    MixedSymbolsError,
    MixedTimeframesError,
    MixedExchangesError,
    InvalidDatasetRangeError,
    InvalidOHLCVDataError,
)
from app.backtesting.datasets.metadata import DatasetMetadata, compute_dataset_id


@dataclass(frozen=True, slots=True)
class HistoricalDataset:
    """Immutable collection of historical market candles with strict validation.

    The dataset is defined by its metadata and an ordered tuple of ``MarketCandle``
    instances. All validation rules from the market-data layer are applied to
    guarantee a deterministic, self-contained representation suitable for back-
    testing.
    """

    candles: Tuple[MarketCandle, ...]
    metadata: DatasetMetadata

    def __post_init__(self) -> None:
        # Guarantee internal immutability by coercing candles to tuple if passed as another sequence
        if not isinstance(self.candles, tuple):
            object.__setattr__(self, "candles", tuple(self.candles))

        # 1. Non-empty check
        if not self.candles:
            raise EmptyDatasetError("HistoricalDataset cannot be empty")

        # 2. Individual candle validation & timezone check
        first = self.candles[0]
        for idx, candle in enumerate(self.candles):
            if not isinstance(candle, MarketCandle):
                raise InvalidOHLCVDataError(f"Element at index {idx} is not a MarketCandle: {candle!r}")

            if candle.timestamp.tzinfo is None or candle.timestamp.tzinfo.utcoffset(candle.timestamp) is None:
                raise InvalidDatasetTimestampError(
                    f"Candle timestamp at index {idx} must be timezone-aware: {candle.timestamp}"
                )

            if not is_valid_ohlc(candle) or not is_valid_volume(candle):
                raise InvalidOHLCVDataError(
                    f"Candle at index {idx} contains invalid OHLCV prices/volume: {candle!r}"
                )

        # 3. Consistency checks (exchange, symbol, timeframe)
        for idx, candle in enumerate(self.candles):
            if candle.exchange != first.exchange:
                raise MixedExchangesError(
                    f"Inconsistent exchange at index {idx}: expected '{first.exchange}', got '{candle.exchange}'"
                )
            if candle.symbol != first.symbol:
                raise MixedSymbolsError(
                    f"Inconsistent symbol at index {idx}: expected '{first.symbol}', got '{candle.symbol}'"
                )
            if candle.timeframe != first.timeframe:
                raise MixedTimeframesError(
                    f"Inconsistent timeframe at index {idx}: expected '{first.timeframe}', got '{candle.timeframe}'"
                )

        # 4. Duplicate timestamps check
        if has_duplicates(self.candles):
            raise DuplicateTimestampError("Duplicate candles detected in dataset")

        # 5. Chronological ordering check
        if not is_strictly_chronological(self.candles):
            raise NonChronologicalCandlesError("Candles are not strictly chronological")

        # 6. Metadata alignment with candle series
        last = self.candles[-1]
        if self.metadata.exchange != first.exchange:
            raise MixedExchangesError(
                f"Metadata exchange '{self.metadata.exchange}' does not match candle exchange '{first.exchange}'"
            )
        if self.metadata.symbol != first.symbol:
            raise MixedSymbolsError(
                f"Metadata symbol '{self.metadata.symbol}' does not match candle symbol '{first.symbol}'"
            )
        if self.metadata.timeframe != first.timeframe:
            raise MixedTimeframesError(
                f"Metadata timeframe '{self.metadata.timeframe}' does not match candle timeframe '{first.timeframe}'"
            )
        if self.metadata.start_timestamp != first.timestamp:
            raise InvalidDatasetRangeError(
                f"Metadata start_timestamp ({self.metadata.start_timestamp}) does not match first candle timestamp ({first.timestamp})"
            )
        if self.metadata.end_timestamp != last.timestamp:
            raise InvalidDatasetRangeError(
                f"Metadata end_timestamp ({self.metadata.end_timestamp}) does not match last candle timestamp ({last.timestamp})"
            )
        if self.metadata.candle_count != len(self.candles):
            raise DatasetValidationError(
                f"Metadata candle_count ({self.metadata.candle_count}) does not match number of candles ({len(self.candles)})"
            )

    # ---------------------------------------------------------------------
    # Convenience Properties & Sequence Protocol
    # ---------------------------------------------------------------------
    @property
    def exchange(self) -> str:
        return self.metadata.exchange

    @property
    def symbol(self) -> str:
        return self.metadata.symbol

    @property
    def timeframe(self) -> str:
        return self.metadata.timeframe

    @property
    def start_timestamp(self) -> datetime:
        return self.metadata.start_timestamp

    @property
    def end_timestamp(self) -> datetime:
        return self.metadata.end_timestamp

    @property
    def candle_count(self) -> int:
        return self.metadata.candle_count

    def __len__(self) -> int:
        return len(self.candles)

    def __getitem__(self, index: int) -> MarketCandle:
        return self.candles[index]

    def __iter__(self):
        return iter(self.candles)

    # ---------------------------------------------------------------------
    # Deterministic Identity
    # ---------------------------------------------------------------------
    @property
    def dataset_id(self) -> str:
        """Return a stable deterministic identifier for the dataset."""
        return compute_dataset_id(self.metadata, self.candles)

    # ---------------------------------------------------------------------
    # Serialization Helpers
    # ---------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Serialize the dataset to a JSON-compatible dictionary representation."""
        return {
            "metadata": self.metadata.to_dict(),
            "candles": [
                {
                    "exchange": c.exchange,
                    "symbol": c.symbol,
                    "timeframe": c.timeframe,
                    "timestamp": c.timestamp.isoformat(),
                    "open": str(c.open),
                    "high": str(c.high),
                    "low": str(c.low),
                    "close": str(c.close),
                    "volume": str(c.volume),
                }
                for c in self.candles
            ],
            "dataset_id": self.dataset_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HistoricalDataset":
        """Deserialize a ``HistoricalDataset`` from a dictionary produced by :meth:`to_dict`."""
        metadata = DatasetMetadata.from_dict(data["metadata"])

        candles: List[MarketCandle] = []
        for c in data["candles"]:
            c_dict = dict(c)
            ts = c_dict["timestamp"]
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)

            candles.append(
                MarketCandle(
                    exchange=str(c_dict["exchange"]),
                    symbol=str(c_dict["symbol"]),
                    timeframe=str(c_dict["timeframe"]),
                    timestamp=ts,
                    open=Decimal(str(c_dict["open"])),
                    high=Decimal(str(c_dict["high"])),
                    low=Decimal(str(c_dict["low"])),
                    close=Decimal(str(c_dict["close"])),
                    volume=Decimal(str(c_dict["volume"])),
                )
            )

        return cls(candles=tuple(candles), metadata=metadata)
