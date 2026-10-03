import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.backtesting.contracts.result import BacktestResult
from app.backtesting.contracts.config import BacktestConfig, PositionSizingConfig
from app.backtesting.contracts.enums import BacktestStatus, PositionSizingType
from app.backtesting.contracts.exceptions import InvalidBacktestResultError

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

def test_valid_completed_result(config):
    res = BacktestResult(
        config=config,
        status=BacktestStatus.COMPLETED,
        start_timestamp=config.start_time,
        end_timestamp=config.end_time,
        candles_processed=24,
        signals_generated=5,
        signals_resolved=5,
        trades_opened=3,
        trades_closed=3,
        final_capital=Decimal("10500"),
        realized_pnl=Decimal("500")
    )
    
    assert res.status == BacktestStatus.COMPLETED
    assert res.candles_processed == 24
    
    res_dict = res.to_dict()
    restored = BacktestResult.from_dict(res_dict)
    assert restored.result_id == res.result_id
    assert restored.final_capital == Decimal("10500")

def test_empty_result(config):
    res = BacktestResult(
        config=config,
        status=BacktestStatus.CREATED
    )
    assert res.status == BacktestStatus.CREATED
    assert res.candles_processed == 0

def test_failed_result(config):
    res = BacktestResult(
        config=config,
        status=BacktestStatus.FAILED,
        errors=["Data missing"]
    )
    assert res.status == BacktestStatus.FAILED
    assert "Data missing" in res.errors

def test_invalid_completed_result(config):
    # Completed result must have final_capital
    with pytest.raises(InvalidBacktestResultError):
        BacktestResult(
            config=config,
            status=BacktestStatus.COMPLETED,
            start_timestamp=config.start_time,
            end_timestamp=config.end_time
        )
