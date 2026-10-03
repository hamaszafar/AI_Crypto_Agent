import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.backtesting.contracts.position import Position
from app.backtesting.contracts.enums import PositionSide
from app.backtesting.contracts.exceptions import InvalidPositionError

def test_long_position():
    now = datetime.now(timezone.utc)
    pos = Position(
        exchange="BINANCE",
        symbol="BTC/USDT",
        side=PositionSide.LONG,
        entry_timestamp=now,
        entry_price=Decimal("50000"),
        quantity=Decimal("1.5"),
        stop_loss=Decimal("49000"),
        take_profit=Decimal("55000")
    )
    assert pos.side == PositionSide.LONG
    assert pos.quantity == Decimal("1.5")
    
    pos_dict = pos.to_dict()
    restored = Position.from_dict(pos_dict)
    assert restored.position_id == pos.position_id
    assert restored.side == PositionSide.LONG

def test_short_position():
    now = datetime.now(timezone.utc)
    pos = Position(
        exchange="BINANCE",
        symbol="BTC/USDT",
        side=PositionSide.SHORT,
        entry_timestamp=now,
        entry_price=Decimal("50000"),
        quantity=Decimal("1.5"),
        stop_loss=Decimal("51000"),
        take_profit=Decimal("45000")
    )
    assert pos.side == PositionSide.SHORT

def test_neutral_position():
    now = datetime.now(timezone.utc)
    pos = Position(
        exchange="BINANCE",
        symbol="BTC/USDT",
        side=PositionSide.FLAT,
        entry_timestamp=now,
        entry_price=Decimal("50000"),
        quantity=Decimal("0")
    )
    assert pos.side == PositionSide.FLAT
    assert pos.quantity == Decimal("0")

def test_invalid_position_state():
    now = datetime.now(timezone.utc)
    with pytest.raises(InvalidPositionError):
        Position(
            exchange="BINANCE",
            symbol="BTC/USDT",
            side=PositionSide.LONG,
            entry_timestamp=now,
            entry_price=Decimal("-50000"),
            quantity=Decimal("1.5")
        )
        
    with pytest.raises(InvalidPositionError):
        Position(
            exchange="BINANCE",
            symbol="BTC/USDT",
            side=PositionSide.LONG,
            entry_timestamp=now,
            entry_price=Decimal("50000"),
            quantity=Decimal("-1.5")
        )
        
    with pytest.raises(InvalidPositionError):
        Position(
            exchange="BINANCE",
            symbol="BTC/USDT",
            side=PositionSide.FLAT,
            entry_timestamp=now,
            entry_price=Decimal("50000"),
            quantity=Decimal("1.5") # Flat must have 0 qty
        )
