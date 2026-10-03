import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.backtesting.contracts.trade import SimulatedTrade
from app.backtesting.contracts.enums import TradeStatus
from app.backtesting.contracts.exceptions import InvalidTradeError
from app.signals.models import SignalDirection

def test_valid_trade():
    now = datetime.now(timezone.utc)
    exit_time = now + timedelta(hours=2)
    trade = SimulatedTrade(
        exchange="BINANCE",
        symbol="BTC/USDT",
        timeframe="1h",
        direction=SignalDirection.BUY,
        entry_timestamp=now,
        entry_price=Decimal("50000"),
        quantity=Decimal("1.5"),
        exit_timestamp=exit_time,
        exit_price=Decimal("52000"),
        stop_loss=Decimal("49000"),
        take_profit=Decimal("53000"),
        fees=Decimal("15"),
        slippage=Decimal("5"),
        realized_pnl=Decimal("2980"),
        status=TradeStatus.CLOSED
    )
    
    assert trade.exchange == "BINANCE"
    assert trade.status == TradeStatus.CLOSED
    
    trade_dict = trade.to_dict()
    restored = SimulatedTrade.from_dict(trade_dict)
    assert restored.trade_id == trade.trade_id
    assert restored.entry_price == trade.entry_price

def test_invalid_trade():
    now = datetime.now(timezone.utc)
    with pytest.raises(InvalidTradeError):
        SimulatedTrade(
            exchange="BINANCE",
            symbol="BTC/USDT",
            timeframe="1h",
            direction=SignalDirection.BUY,
            entry_timestamp=now,
            entry_price=Decimal("-50000"),
            quantity=Decimal("1.5")
        )
        
    with pytest.raises(InvalidTradeError):
        SimulatedTrade(
            exchange="BINANCE",
            symbol="BTC/USDT",
            timeframe="1h",
            direction=SignalDirection.BUY,
            entry_timestamp=now,
            entry_price=Decimal("50000"),
            quantity=Decimal("-1.5")
        )

def test_invalid_lifecycle_timestamps():
    now = datetime.now(timezone.utc)
    exit_time = now - timedelta(hours=2)
    with pytest.raises(InvalidTradeError):
        SimulatedTrade(
            exchange="BINANCE",
            symbol="BTC/USDT",
            timeframe="1h",
            direction=SignalDirection.BUY,
            entry_timestamp=now,
            entry_price=Decimal("50000"),
            quantity=Decimal("1.5"),
            exit_timestamp=exit_time,
            exit_price=Decimal("52000")
        )

def test_closed_trade_requires_exit():
    now = datetime.now(timezone.utc)
    with pytest.raises(InvalidTradeError):
        SimulatedTrade(
            exchange="BINANCE",
            symbol="BTC/USDT",
            timeframe="1h",
            direction=SignalDirection.BUY,
            entry_timestamp=now,
            entry_price=Decimal("50000"),
            quantity=Decimal("1.5"),
            status=TradeStatus.CLOSED
        )
