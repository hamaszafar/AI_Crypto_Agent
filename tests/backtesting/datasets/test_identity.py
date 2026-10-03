import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import subprocess
import sys

from app.market_data.models import MarketCandle
from app.backtesting.datasets.models import HistoricalDataset
from app.backtesting.datasets.metadata import DatasetMetadata, compute_dataset_id


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


# 1. Same dataset → same ID
def test_same_dataset_same_id():
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles1 = tuple(make_candle(start + timedelta(hours=i)) for i in range(3))
    candles2 = tuple(make_candle(start + timedelta(hours=i)) for i in range(3))

    meta1 = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=candles1[0].timestamp,
        end_timestamp=candles1[-1].timestamp,
        candle_count=len(candles1),
    )
    meta2 = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=candles2[0].timestamp,
        end_timestamp=candles2[-1].timestamp,
        candle_count=len(candles2),
    )

    ds1 = HistoricalDataset(candles=candles1, metadata=meta1)
    ds2 = HistoricalDataset(candles=candles2, metadata=meta2)

    assert ds1.dataset_id == ds2.dataset_id
    assert len(ds1.dataset_id) == 64  # SHA-256 hex string


# 2. Process-independent identity
def test_process_independent_identity():
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = tuple(make_candle(start + timedelta(hours=i)) for i in range(2))
    meta = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=candles[0].timestamp,
        end_timestamp=candles[-1].timestamp,
        candle_count=2,
    )
    ds = HistoricalDataset(candles=candles, metadata=meta)
    id_in_process = ds.dataset_id

    # Compute expected ID manually using compute_dataset_id
    computed_id = compute_dataset_id(meta, candles)
    assert id_in_process == computed_id


# 3. Changed candle → changed ID
def test_changed_candle_changed_id():
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    c1 = make_candle(start)
    c2 = make_candle(start + timedelta(hours=1), close_price=Decimal("30500"))
    meta = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=start,
        end_timestamp=start + timedelta(hours=1),
        candle_count=2,
    )
    ds1 = HistoricalDataset(candles=(c1, c2), metadata=meta)

    # Change candle volume or close price
    c2_modified = make_candle(start + timedelta(hours=1), close_price=Decimal("30900"))
    ds2 = HistoricalDataset(candles=(c1, c2_modified), metadata=meta)

    assert ds1.dataset_id != ds2.dataset_id


# 4. Changed timeframe → changed ID
def test_changed_timeframe_changed_id():
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    c1_1h = make_candle(start, timeframe="1h")
    c2_1h = make_candle(start + timedelta(hours=1), timeframe="1h")
    meta_1h = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=start,
        end_timestamp=start + timedelta(hours=1),
        candle_count=2,
    )
    ds1 = HistoricalDataset(candles=(c1_1h, c2_1h), metadata=meta_1h)

    c1_4h = make_candle(start, timeframe="4h")
    c2_4h = make_candle(start + timedelta(hours=1), timeframe="4h")
    meta_4h = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="4h",
        start_timestamp=start,
        end_timestamp=start + timedelta(hours=1),
        candle_count=2,
    )
    ds2 = HistoricalDataset(candles=(c1_4h, c2_4h), metadata=meta_4h)

    assert ds1.dataset_id != ds2.dataset_id


# 5. Changed symbol → changed ID
def test_changed_symbol_changed_id():
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    c1_btc = make_candle(start, symbol="BTC/USDT")
    c2_btc = make_candle(start + timedelta(hours=1), symbol="BTC/USDT")
    meta_btc = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=start,
        end_timestamp=start + timedelta(hours=1),
        candle_count=2,
    )
    ds_btc = HistoricalDataset(candles=(c1_btc, c2_btc), metadata=meta_btc)

    c1_eth = make_candle(start, symbol="ETH/USDT")
    c2_eth = make_candle(start + timedelta(hours=1), symbol="ETH/USDT")
    meta_eth = DatasetMetadata(
        exchange="binance",
        symbol="ETH/USDT",
        timeframe="1h",
        start_timestamp=start,
        end_timestamp=start + timedelta(hours=1),
        candle_count=2,
    )
    ds_eth = HistoricalDataset(candles=(c1_eth, c2_eth), metadata=meta_eth)

    assert ds_btc.dataset_id != ds_eth.dataset_id


# 6. Changed source → changed ID
def test_changed_source_changed_id():
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    c1_bin = make_candle(start, exchange="binance")
    c2_bin = make_candle(start + timedelta(hours=1), exchange="binance")
    meta_bin = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=start,
        end_timestamp=start + timedelta(hours=1),
        candle_count=2,
    )
    ds_bin = HistoricalDataset(candles=(c1_bin, c2_bin), metadata=meta_bin)

    c1_byb = make_candle(start, exchange="bybit")
    c2_byb = make_candle(start + timedelta(hours=1), exchange="bybit")
    meta_byb = DatasetMetadata(
        exchange="bybit",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=start,
        end_timestamp=start + timedelta(hours=1),
        candle_count=2,
    )
    ds_byb = HistoricalDataset(candles=(c1_byb, c2_byb), metadata=meta_byb)

    assert ds_bin.dataset_id != ds_byb.dataset_id


# 7. Metadata consistency & extended fields
def test_metadata_consistency_and_extended_fields():
    created_at = datetime(2023, 1, 1, 12, 0, tzinfo=timezone.utc)
    meta = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc),
        end_timestamp=datetime(2023, 1, 1, 2, 0, tzinfo=timezone.utc),
        candle_count=3,
        schema_version="1.0",
        created_at=created_at,
        validation_status="VALID",
    )

    d = meta.to_dict()
    assert d["exchange"] == "binance"
    assert d["symbol"] == "BTC/USDT"
    assert d["timeframe"] == "1h"
    assert d["schema_version"] == "1.0"
    assert d["created_at"] == created_at.isoformat()
    assert d["validation_status"] == "VALID"

    meta_restored = DatasetMetadata.from_dict(d)
    assert meta_restored == meta


# 8. Serialization determinism
def test_serialization_determinism():
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = tuple(make_candle(start + timedelta(hours=i)) for i in range(2))
    meta = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=candles[0].timestamp,
        end_timestamp=candles[-1].timestamp,
        candle_count=2,
        created_at=datetime(2023, 1, 1, 10, 0, tzinfo=timezone.utc),
        validation_status="VALID",
    )
    ds1 = HistoricalDataset(candles=candles, metadata=meta)

    # Serialize and deserialize multiple times
    d1 = ds1.to_dict()
    ds2 = HistoricalDataset.from_dict(d1)
    d2 = ds2.to_dict()

    assert d1 == d2
    assert ds1.dataset_id == ds2.dataset_id
