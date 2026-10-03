"""
Enums for Module 6C Backtesting Contracts.
"""

from enum import Enum


class PositionSizingType(str, Enum):
    """Position sizing modes."""

    FIXED_AMOUNT = "FIXED_AMOUNT"
    PERCENT_OF_EQUITY = "PERCENT_OF_EQUITY"
    RISK_PERCENT = "RISK_PERCENT"


class SignalOutcomeStatus(str, Enum):
    """Possible outcome states for a generated signal."""

    PENDING = "PENDING"
    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"
    EXPIRED = "EXPIRED"
    INVALID = "INVALID"
    CANCELLED = "CANCELLED"


class TradeStatus(str, Enum):
    """Lifecycle status of a simulated trade."""

    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class PositionSide(str, Enum):
    """Position side."""

    FLAT = "FLAT"
    LONG = "LONG"
    SHORT = "SHORT"


class BacktestStatus(str, Enum):
    """Overall execution status of a backtest."""

    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
