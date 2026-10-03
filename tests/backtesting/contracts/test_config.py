import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.backtesting.contracts.config import BacktestConfig, PositionSizingConfig
from app.backtesting.contracts.enums import PositionSizingType
from app.backtesting.contracts.exceptions import InvalidBacktestConfigError

def test_valid_position_sizing_config():
    config = PositionSizingConfig(sizing_type=PositionSizingType.PERCENT_OF_EQUITY, value=Decimal("10"))
    assert config.sizing_type == PositionSizingType.PERCENT_OF_EQUITY
    assert config.value == Decimal("10")
    
    config_dict = config.to_dict()
    assert config_dict == {"sizing_type": "PERCENT_OF_EQUITY", "value": "10"}
    
    restored = PositionSizingConfig.from_dict(config_dict)
    assert restored == config

def test_invalid_position_sizing_config():
    with pytest.raises(InvalidBacktestConfigError):
        PositionSizingConfig(sizing_type=PositionSizingType.PERCENT_OF_EQUITY, value=Decimal("-10"))
        
    with pytest.raises(InvalidBacktestConfigError):
        PositionSizingConfig(sizing_type=PositionSizingType.PERCENT_OF_EQUITY, value=Decimal("101"))
        
def test_valid_backtest_config():
    now = datetime.now(timezone.utc)
    config = BacktestConfig(
        exchange="BINANCE",
        symbol="BTC/USDT",
        timeframe="1h",
        start_time=now,
        end_time=now + timedelta(days=1),
        initial_capital=Decimal("10000"),
        position_sizing=PositionSizingConfig(sizing_type=PositionSizingType.PERCENT_OF_EQUITY, value=Decimal("10")),
        fee_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.002"),
    )
    assert config.exchange == "BINANCE"
    assert config.initial_capital == Decimal("10000")
    assert config.fee_rate == Decimal("0.001")
    
    config_dict = config.to_dict()
    assert config_dict["exchange"] == "BINANCE"
    
    restored = BacktestConfig.from_dict(config_dict)
    assert restored == config

def test_invalid_date_range_backtest_config():
    now = datetime.now(timezone.utc)
    with pytest.raises(InvalidBacktestConfigError):
        BacktestConfig(
            exchange="BINANCE",
            symbol="BTC/USDT",
            timeframe="1h",
            start_time=now + timedelta(days=1),
            end_time=now,
            initial_capital=Decimal("10000"),
            position_sizing=PositionSizingConfig(sizing_type=PositionSizingType.PERCENT_OF_EQUITY, value=Decimal("10")),
        )

def test_invalid_capital_and_fees():
    now = datetime.now(timezone.utc)
    with pytest.raises(InvalidBacktestConfigError):
        BacktestConfig(
            exchange="BINANCE",
            symbol="BTC/USDT",
            timeframe="1h",
            start_time=now,
            end_time=now + timedelta(days=1),
            initial_capital=Decimal("-1000"),
            position_sizing=PositionSizingConfig(sizing_type=PositionSizingType.PERCENT_OF_EQUITY, value=Decimal("10")),
        )
        
    with pytest.raises(InvalidBacktestConfigError):
        BacktestConfig(
            exchange="BINANCE",
            symbol="BTC/USDT",
            timeframe="1h",
            start_time=now,
            end_time=now + timedelta(days=1),
            initial_capital=Decimal("10000"),
            position_sizing=PositionSizingConfig(sizing_type=PositionSizingType.PERCENT_OF_EQUITY, value=Decimal("10")),
            fee_rate=Decimal("-0.001")
        )
