import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.backtesting.contracts.request import BacktestRequest
from app.backtesting.contracts.config import BacktestConfig, PositionSizingConfig
from app.backtesting.contracts.enums import PositionSizingType
from app.backtesting.contracts.exceptions import InvalidBacktestRequestError
from app.backtesting.datasets.models import HistoricalDataset

@pytest.fixture
def config():
    now = datetime.now(timezone.utc)
    return BacktestConfig(
        exchange="BINANCE",
        symbol="BTC/USDT",
        timeframe="1h",
        start_time=now,
        end_time=now + timedelta(days=1),
        initial_capital=Decimal("10000"),
        position_sizing=PositionSizingConfig(sizing_type=PositionSizingType.PERCENT_OF_EQUITY, value=Decimal("10")),
    )

def test_valid_backtest_request(config):
    req = BacktestRequest(
        config=config,
        dataset_id="ds_123"
    )
    
    assert req.dataset_id == "ds_123"
    
    req_dict = req.to_dict()
    assert req_dict["dataset_id"] == "ds_123"
    
    restored = BacktestRequest.from_dict(req_dict)
    assert restored.request_id == req.request_id

def test_dataset_validation(config):
    from app.backtesting.datasets.metadata import DatasetMetadata
    from app.market_data.models import MarketCandle
    
    now = datetime.now(timezone.utc)
    candle = MarketCandle(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        timestamp=now,
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
        volume=Decimal("1000")
    )
    metadata = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=now,
        end_timestamp=now,
        candle_count=1
    )
    dataset = HistoricalDataset(
        candles=(candle,),
        metadata=metadata
    )
    
    req = BacktestRequest(
        config=config,
        dataset=dataset
    )
    
    assert req.dataset_id == dataset.dataset_id

def test_invalid_dataset_validation(config):
    now = datetime.now(timezone.utc)
    from app.backtesting.datasets.metadata import DatasetMetadata
    from app.market_data.models import MarketCandle
    
    candle = MarketCandle(
        exchange="binance",
        symbol="ETH/USDT", # Mismatched symbol
        timeframe="1h",
        timestamp=now,
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
        volume=Decimal("1000")
    )
    metadata = DatasetMetadata(
        exchange="binance",
        symbol="ETH/USDT",
        timeframe="1h",
        start_timestamp=now,
        end_timestamp=now,
        candle_count=1
    )
    dataset = HistoricalDataset(
        candles=(candle,),
        metadata=metadata
    )
    
    with pytest.raises(InvalidBacktestRequestError):
        BacktestRequest(
            config=config,
            dataset=dataset
        )
