import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

from app.backtesting.datasets.loader import StorageHistoricalDataLoader
from app.backtesting.datasets.exceptions import (
    DatasetLoadError,
    NoDataError,
    IncompleteDataError,
    InvalidDateRangeError,
    UnsupportedSymbolError,
    UnsupportedTimeframeError,
    UnavailableSourceError,
)
from app.backtesting.datasets.models import HistoricalDataset
from app.market_data.storage import MarketDataStorage
from app.storage.models import StoredCandle
from app.exchanges.types import Symbol, Timeframe


@pytest.fixture
def mock_storage():
    return MagicMock(spec=MarketDataStorage)


@pytest.fixture
def loader(mock_storage):
    return StorageHistoricalDataLoader(storage=mock_storage)


@pytest.fixture
def sample_stored_candles():
    base_time = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    return [
        StoredCandle(
            exchange="binance",
            symbol="BTC/USDT",
            timeframe="15m",
            timestamp=base_time,
            open=Decimal("100"),
            high=Decimal("110"),
            low=Decimal("90"),
            close=Decimal("105"),
            volume=Decimal("1000"),
        ),
        StoredCandle(
            exchange="binance",
            symbol="BTC/USDT",
            timeframe="15m",
            timestamp=base_time + timedelta(minutes=15),
            open=Decimal("105"),
            high=Decimal("115"),
            low=Decimal("95"),
            close=Decimal("110"),
            volume=Decimal("1200"),
        ),
    ]


# 1. Valid historical loading with Symbol/Timeframe enums
def test_loader_valid_loading(loader, mock_storage, sample_stored_candles):
    mock_storage.get_candles.return_value = sample_stored_candles

    start_time = sample_stored_candles[0].timestamp
    end_time = sample_stored_candles[-1].timestamp

    dataset = loader.load(
        exchange="binance",
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        start_time=start_time,
        end_time=end_time,
    )

    assert isinstance(dataset, HistoricalDataset)
    assert len(dataset.candles) == 2
    assert dataset.metadata.exchange == "binance"
    assert dataset.metadata.symbol == "BTC/USDT"
    assert dataset.metadata.timeframe == "15m"
    assert dataset.metadata.start_timestamp == start_time
    assert dataset.metadata.end_timestamp == end_time
    assert dataset.metadata.candle_count == 2

    # Deterministic identity check
    assert dataset.dataset_id is not None
    assert len(dataset.dataset_id) == 64

    mock_storage.get_candles.assert_called_once_with(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
        start_time=start_time,
        end_time=end_time,
    )


# 2. Valid loading with string parameters
def test_loader_valid_string_parameters(loader, mock_storage, sample_stored_candles):
    mock_storage.get_candles.return_value = sample_stored_candles
    start_time = sample_stored_candles[0].timestamp
    end_time = sample_stored_candles[-1].timestamp

    dataset = loader.load(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
        start_time=start_time,
        end_time=end_time,
    )
    assert isinstance(dataset, HistoricalDataset)
    assert dataset.symbol == "BTC/USDT"
    assert dataset.timeframe == "15m"


# 3. Empty storage result
def test_loader_empty_result(loader, mock_storage):
    mock_storage.get_candles.return_value = []
    start_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end_time = start_time + timedelta(days=1)

    with pytest.raises(NoDataError):
        loader.load(
            exchange="binance",
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
            start_time=start_time,
            end_time=end_time,
        )


# 4. Incomplete data range loading
def test_loader_incomplete_data(loader, mock_storage, sample_stored_candles):
    mock_storage.get_candles.return_value = sample_stored_candles
    start_time = sample_stored_candles[0].timestamp - timedelta(minutes=15)
    end_time = sample_stored_candles[-1].timestamp

    with pytest.raises(IncompleteDataError):
        loader.load(
            exchange="binance",
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
            start_time=start_time,
            end_time=end_time,
        )


# 5. Malformed data handling
def test_loader_malformed_data(loader, mock_storage, sample_stored_candles):
    sample_stored_candles[0] = StoredCandle(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="invalid_tf",
        timestamp=sample_stored_candles[0].timestamp,
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
        volume=Decimal("1000"),
    )

    mock_storage.get_candles.return_value = sample_stored_candles
    start_time = sample_stored_candles[0].timestamp
    end_time = sample_stored_candles[-1].timestamp

    with pytest.raises(DatasetLoadError, match="Malformed data encountered"):
        loader.load(
            exchange="binance",
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
            start_time=start_time,
            end_time=end_time,
        )


# 6. Validation failure handling
def test_loader_validation_failure(loader, mock_storage, sample_stored_candles):
    start_time = sample_stored_candles[0].timestamp
    end_time = sample_stored_candles[1].timestamp

    # Duplicate candle at same timestamp
    invalid_candles = [sample_stored_candles[0], sample_stored_candles[0], sample_stored_candles[1]]
    mock_storage.get_candles.return_value = invalid_candles

    with pytest.raises(DatasetLoadError, match="Validation failed for dataset"):
        loader.load(
            exchange="binance",
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
            start_time=start_time,
            end_time=end_time,
        )


# 7. Storage failure handling
def test_loader_storage_failure(loader, mock_storage):
    mock_storage.get_candles.side_effect = RuntimeError("Database connection lost")
    start_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end_time = start_time + timedelta(days=1)

    with pytest.raises(UnavailableSourceError, match="Storage error"):
        loader.load(
            exchange="binance",
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
            start_time=start_time,
            end_time=end_time,
        )


# 8. Date range validation
def test_loader_invalid_date_range(loader, mock_storage):
    start_time = datetime(2023, 1, 2, tzinfo=timezone.utc)
    end_time = datetime(2023, 1, 1, tzinfo=timezone.utc)  # End before start

    with pytest.raises(InvalidDateRangeError):
        loader.load(
            exchange="binance",
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
            start_time=start_time,
            end_time=end_time,
        )


def test_loader_naive_date_range(loader, mock_storage):
    start_time = datetime(2023, 1, 1, 0, 0)  # Naive datetime
    end_time = datetime(2023, 1, 2, 0, 0, tzinfo=timezone.utc)

    with pytest.raises(InvalidDateRangeError):
        loader.load(
            exchange="binance",
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
            start_time=start_time,
            end_time=end_time,
        )


# 9. Symbol validation failure
def test_loader_invalid_symbol(loader):
    start_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end_time = start_time + timedelta(days=1)

    with pytest.raises(UnsupportedSymbolError):
        loader.load(
            exchange="binance",
            symbol="INVALID_SYMBOL",
            timeframe=Timeframe.FIFTEEN_MINUTES,
            start_time=start_time,
            end_time=end_time,
        )


# 10. Timeframe validation failure
def test_loader_invalid_timeframe(loader):
    start_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end_time = start_time + timedelta(days=1)

    with pytest.raises(UnsupportedTimeframeError):
        loader.load(
            exchange="binance",
            symbol=Symbol.BTC_USDT,
            timeframe="1000m",  # Unsupported timeframe
            start_time=start_time,
            end_time=end_time,
        )


# 11. Source/Exchange validation failure
def test_loader_invalid_exchange(loader):
    start_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
    end_time = start_time + timedelta(days=1)

    with pytest.raises(UnavailableSourceError):
        loader.load(
            exchange="",
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
            start_time=start_time,
            end_time=end_time,
        )


# 12. Initialization with None storage
def test_loader_init_none_storage():
    with pytest.raises(UnavailableSourceError):
        StorageHistoricalDataLoader(storage=None)
