from datetime import datetime, timezone
from decimal import Decimal
from typing import Protocol, Union, Optional

from app.backtesting.datasets.models import HistoricalDataset
from app.backtesting.datasets.metadata import DatasetMetadata
from app.backtesting.datasets.validator import HistoricalDatasetValidator
from app.backtesting.datasets.exceptions import (
    DatasetLoadError,
    NoDataError,
    IncompleteDataError,
    InvalidDateRangeError,
    UnsupportedSymbolError,
    UnsupportedTimeframeError,
    UnavailableSourceError,
)
from app.exchanges.types import Symbol, Timeframe
from app.market_data.models import MarketCandle
from app.market_data.storage import MarketDataStorage


class HistoricalDataLoader(Protocol):
    """Contract for loading historical datasets."""

    def load(
        self,
        exchange: str,
        symbol: Union[Symbol, str],
        timeframe: Union[Timeframe, str],
        start_time: datetime,
        end_time: datetime,
    ) -> HistoricalDataset:
        ...


class StorageHistoricalDataLoader:
    """Loads historical datasets from the application's market data storage."""

    def __init__(
        self,
        storage: MarketDataStorage,
        validator: Optional[HistoricalDatasetValidator] = None,
    ):
        if storage is None:
            raise UnavailableSourceError("StorageService/MarketDataStorage instance cannot be None")
        self.storage = storage
        self.validator = validator or HistoricalDatasetValidator()

    def load(
        self,
        exchange: str,
        symbol: Union[Symbol, str],
        timeframe: Union[Timeframe, str],
        start_time: datetime,
        end_time: datetime,
    ) -> HistoricalDataset:
        # 1. Exchange / Source validation
        if not exchange or not isinstance(exchange, str) or not exchange.strip():
            raise UnavailableSourceError("Exchange source must be a non-empty string")
        norm_exchange = exchange.strip().lower()

        # 2. Symbol validation
        if isinstance(symbol, Symbol):
            str_symbol = symbol.value
        elif isinstance(symbol, str):
            if "/" not in symbol or len(symbol.split("/")) != 2:
                raise UnsupportedSymbolError(f"Invalid or unsupported symbol format: {symbol!r}")
            str_symbol = symbol
        else:
            raise UnsupportedSymbolError(f"Symbol must be a Symbol enum or valid symbol string, got {type(symbol).__name__}")

        # 3. Timeframe validation
        valid_timeframe_values = {t.value for t in Timeframe}
        if isinstance(timeframe, Timeframe):
            str_timeframe = timeframe.value
        elif isinstance(timeframe, str):
            if timeframe not in valid_timeframe_values:
                raise UnsupportedTimeframeError(f"Invalid or unsupported timeframe: {timeframe!r}")
            str_timeframe = timeframe
        else:
            raise UnsupportedTimeframeError(f"Timeframe must be a Timeframe enum or valid timeframe string, got {type(timeframe).__name__}")

        # 4. Date range validation
        if not isinstance(start_time, datetime) or start_time.tzinfo is None or start_time.tzinfo.utcoffset(start_time) is None:
            raise InvalidDateRangeError("start_time must be a timezone-aware UTC datetime")

        if not isinstance(end_time, datetime) or end_time.tzinfo is None or end_time.tzinfo.utcoffset(end_time) is None:
            raise InvalidDateRangeError("end_time must be a timezone-aware UTC datetime")

        if start_time >= end_time:
            raise InvalidDateRangeError("start_time must be strictly before end_time")

        # 5. Fetch stored candles
        try:
            stored_candles = self.storage.get_candles(
                exchange=norm_exchange,
                symbol=str_symbol,
                timeframe=str_timeframe,
                start_time=start_time,
                end_time=end_time,
            )
        except Exception as e:
            raise UnavailableSourceError(f"Storage error: {e}") from e

        # 6. Check for empty result
        if not stored_candles:
            raise NoDataError(
                f"No data found for {str_symbol} {str_timeframe} from {start_time} to {end_time}"
            )

        # 7. Convert to canonical MarketCandle instances
        market_candles = []
        for idx, c in enumerate(stored_candles):
            try:
                mc = MarketCandle(
                    exchange=getattr(c, "exchange", norm_exchange),
                    symbol=getattr(c, "symbol", str_symbol),
                    timeframe=getattr(c, "timeframe", str_timeframe),
                    timestamp=getattr(c, "timestamp"),
                    open=Decimal(str(getattr(c, "open"))),
                    high=Decimal(str(getattr(c, "high"))),
                    low=Decimal(str(getattr(c, "low"))),
                    close=Decimal(str(getattr(c, "close"))),
                    volume=Decimal(str(getattr(c, "volume"))),
                )
                market_candles.append(mc)
            except Exception as e:
                raise DatasetLoadError(f"Malformed data encountered: {e}") from e

        # 8. Boundary checking
        first_candle_time = market_candles[0].timestamp
        last_candle_time = market_candles[-1].timestamp

        if first_candle_time > start_time or last_candle_time < end_time:
            raise IncompleteDataError(
                f"Data incomplete: requested {start_time} to {end_time}, "
                f"but got {first_candle_time} to {last_candle_time}"
            )

        # 9. Run Dataset Validation
        temp_meta = DatasetMetadata(
            exchange=norm_exchange,
            symbol=str_symbol,
            timeframe=str_timeframe,
            start_timestamp=first_candle_time,
            end_timestamp=last_candle_time,
            candle_count=len(market_candles),
        )
        val_result = self.validator.validate_raw(market_candles, temp_meta)
        if not val_result.is_valid:
            error_msg = val_result.errors[0].message if val_result.errors else "Unknown validation error"
            raise DatasetLoadError(f"Validation failed for dataset: {error_msg}")

        # 10. Construct final DatasetMetadata with validation status
        final_metadata = DatasetMetadata(
            exchange=norm_exchange,
            symbol=str_symbol,
            timeframe=str_timeframe,
            start_timestamp=first_candle_time,
            end_timestamp=last_candle_time,
            candle_count=len(market_candles),
            validation_status=val_result.status,
        )

        try:
            return HistoricalDataset(candles=tuple(market_candles), metadata=final_metadata)
        except Exception as e:
            raise DatasetLoadError(f"Validation failed for dataset: {e}") from e
