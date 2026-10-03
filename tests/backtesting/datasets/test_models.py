import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from app.market_data.models import MarketCandle
from app.backtesting.datasets.models import HistoricalDataset
from app.backtesting.datasets.metadata import DatasetMetadata
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


def make_candle(
    ts: datetime,
    exchange: str = "binance",
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
    open_price: Decimal = Decimal("30000"),
    high_price: Decimal = Decimal("31000"),
    low_price: Decimal = Decimal("29500"),
    close_price: Decimal = Decimal("30500"),
    volume: Decimal = Decimal("123.45"),
) -> MarketCandle:
    return MarketCandle(
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        timestamp=ts,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
    )


# 1. Valid dataset construction
def test_valid_historical_dataset():
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = tuple(make_candle(start + timedelta(hours=i)) for i in range(3))
    metadata = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=candles[0].timestamp,
        end_timestamp=candles[-1].timestamp,
        candle_count=len(candles),
    )
    ds = HistoricalDataset(candles=candles, metadata=metadata)
    assert ds.metadata == metadata
    assert ds.candles == candles
    assert ds.exchange == "binance"
    assert ds.symbol == "BTC/USDT"
    assert ds.timeframe == "1h"
    assert ds.start_timestamp == candles[0].timestamp
    assert ds.end_timestamp == candles[-1].timestamp
    assert ds.candle_count == 3
    assert len(ds) == 3
    assert ds[0] == candles[0]
    assert list(ds) == list(candles)


# 2. Empty dataset behavior
def test_empty_dataset_behavior():
    metadata = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
        end_timestamp=datetime(2023, 1, 1, tzinfo=timezone.utc),
        candle_count=0,
    )
    with pytest.raises(EmptyDatasetError):
        HistoricalDataset(candles=tuple(), metadata=metadata)


# 3. Invalid timestamp
def test_invalid_timestamp():
    start_naive = datetime(2023, 1, 1, 0, 0)  # naive timestamp
    with pytest.raises(DatasetValidationError):
        DatasetMetadata(
            exchange="binance",
            symbol="BTC/USDT",
            timeframe="1h",
            start_timestamp=start_naive,
            end_timestamp=datetime(2023, 1, 1, 1, 0, tzinfo=timezone.utc),
            candle_count=1,
        )


# 4. Chronological ordering
def test_chronological_ordering():
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    c1 = make_candle(start)
    c2 = make_candle(start - timedelta(hours=1))  # earlier timestamp second
    candles = (c1, c2)
    metadata = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=c2.timestamp,
        end_timestamp=c1.timestamp,
        candle_count=2,
    )
    with pytest.raises(NonChronologicalCandlesError):
        HistoricalDataset(candles=candles, metadata=metadata)


# 5. Duplicate timestamps
def test_duplicate_timestamps():
    ts = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    c1 = make_candle(ts)
    c2 = make_candle(ts)
    candles = (c1, c2)
    metadata = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=ts,
        end_timestamp=ts,
        candle_count=2,
    )
    with pytest.raises(DuplicateTimestampError):
        HistoricalDataset(candles=candles, metadata=metadata)


# 6. Symbol consistency
def test_symbol_consistency():
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    c1 = make_candle(start, symbol="BTC/USDT")
    c2 = make_candle(start + timedelta(hours=1), symbol="ETH/USDT")
    candles = (c1, c2)
    metadata = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=c1.timestamp,
        end_timestamp=c2.timestamp,
        candle_count=2,
    )
    with pytest.raises(MixedSymbolsError):
        HistoricalDataset(candles=candles, metadata=metadata)


# 7. Timeframe consistency
def test_timeframe_consistency():
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    c1 = make_candle(start, timeframe="1h")
    c2 = make_candle(start + timedelta(hours=1), timeframe="4h")
    candles = (c1, c2)
    metadata = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=c1.timestamp,
        end_timestamp=c2.timestamp,
        candle_count=2,
    )
    with pytest.raises(MixedTimeframesError):
        HistoricalDataset(candles=candles, metadata=metadata)


# 8. Source/exchange consistency
def test_exchange_consistency():
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    c1 = make_candle(start, exchange="binance")
    c2 = make_candle(start + timedelta(hours=1), exchange="bybit")
    candles = (c1, c2)
    metadata = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=c1.timestamp,
        end_timestamp=c2.timestamp,
        candle_count=2,
    )
    with pytest.raises(MixedExchangesError):
        HistoricalDataset(candles=candles, metadata=metadata)


# 9. Invalid OHLCV
def test_invalid_ohlcv():
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    # High price < Low price is invalid for dataset candles
    invalid_candle = make_candle(start, high_price=Decimal("100"), low_price=Decimal("200"))
    metadata = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=start,
        end_timestamp=start,
        candle_count=1,
    )
    with pytest.raises(InvalidOHLCVDataError):
        HistoricalDataset(candles=(invalid_candle,), metadata=metadata)


# 10. Invalid date range
def test_invalid_date_range():
    start = datetime(2023, 1, 2, 0, 0, tzinfo=timezone.utc)
    end = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(InvalidDatasetRangeError):
        DatasetMetadata(
            exchange="binance",
            symbol="BTC/USDT",
            timeframe="1h",
            start_timestamp=start,
            end_timestamp=end,
            candle_count=2,
        )


# 11. Candle count mismatch
def test_candle_count_mismatch():
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = tuple(make_candle(start + timedelta(hours=i)) for i in range(2))
    metadata = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=candles[0].timestamp,
        end_timestamp=candles[-1].timestamp,
        candle_count=999,  # incorrect count
    )
    with pytest.raises(DatasetValidationError):
        HistoricalDataset(candles=candles, metadata=metadata)


# 12. Start/end boundaries mismatch
def test_start_end_boundaries_mismatch():
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = tuple(make_candle(start + timedelta(hours=i)) for i in range(2))
    metadata = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=start - timedelta(hours=5),  # mismatch start
        end_timestamp=candles[-1].timestamp,
        candle_count=2,
    )
    with pytest.raises(InvalidDatasetRangeError):
        HistoricalDataset(candles=candles, metadata=metadata)


# 13. Deterministic dataset identity
def test_deterministic_dataset_identity():
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = tuple(make_candle(start + timedelta(hours=i)) for i in range(3))
    metadata = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=candles[0].timestamp,
        end_timestamp=candles[-1].timestamp,
        candle_count=len(candles),
    )
    ds1 = HistoricalDataset(candles=candles, metadata=metadata)
    ds2 = HistoricalDataset(candles=candles, metadata=metadata)
    assert ds1.dataset_id == ds2.dataset_id
    assert len(ds1.dataset_id) == 64  # SHA-256 hex string


# 14. Identity changes when meaningful data changes
def test_identity_changes_when_data_changes():
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    c1 = make_candle(start, close_price=Decimal("30000"))
    c2 = make_candle(start + timedelta(hours=1), high_price=Decimal("31000"), close_price=Decimal("30500"))
    metadata = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=start,
        end_timestamp=start + timedelta(hours=1),
        candle_count=2,
    )
    ds1 = HistoricalDataset(candles=(c1, c2), metadata=metadata)

    # Modify candle price content (valid OHLC close price change)
    c2_modified = make_candle(
        start + timedelta(hours=1),
        open_price=Decimal("30000"),
        high_price=Decimal("36000"),
        low_price=Decimal("29500"),
        close_price=Decimal("35000"),
        volume=Decimal("123.45"),
    )
    ds2 = HistoricalDataset(candles=(c1, c2_modified), metadata=metadata)

    assert ds1.dataset_id != ds2.dataset_id


# 15. Protection against accidental mutation
def test_protection_against_accidental_mutation():
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = tuple(make_candle(start + timedelta(hours=i)) for i in range(2))
    metadata = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=candles[0].timestamp,
        end_timestamp=candles[-1].timestamp,
        candle_count=2,
    )
    ds = HistoricalDataset(candles=candles, metadata=metadata)
    with pytest.raises(AttributeError):
        ds.candles = ()  # type: ignore[attr-defined]
    with pytest.raises(AttributeError):
        ds.metadata = metadata  # type: ignore[attr-defined]
    with pytest.raises(TypeError):
        ds.candles[0] = candles[1]  # type: ignore[index]


# 16. Serialization roundtrip
def test_serialization_roundtrip():
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = tuple(make_candle(start + timedelta(hours=i)) for i in range(2))
    metadata = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=candles[0].timestamp,
        end_timestamp=candles[-1].timestamp,
        candle_count=2,
    )
    ds = HistoricalDataset(candles=candles, metadata=metadata)
    serialized = ds.to_dict()
    ds_deserialized = HistoricalDataset.from_dict(serialized)
    assert ds_deserialized == ds
    assert ds_deserialized.dataset_id == ds.dataset_id
