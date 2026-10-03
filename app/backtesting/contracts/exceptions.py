"""
Exceptions for Backtest Contracts.
"""


class BacktestContractError(ValueError):
    """Base exception for backtest contract validation errors."""

    pass


class InvalidBacktestConfigError(BacktestContractError):
    """Raised when backtest configuration parameters are invalid."""

    pass


class InvalidBacktestRequestError(BacktestContractError):
    """Raised when backtest execution request parameters are invalid."""

    pass


class InvalidSignalObservationError(BacktestContractError):
    """Raised when signal observation contract invariants are violated."""

    pass


class InvalidSignalOutcomeError(BacktestContractError):
    """Raised when signal outcome contract invariants are violated."""

    pass


class InvalidTradeError(BacktestContractError):
    """Raised when simulated trade contract invariants are violated."""

    pass


class InvalidPositionError(BacktestContractError):
    """Raised when position lifecycle state invariants are violated."""

    pass


class InvalidBacktestResultError(BacktestContractError):
    """Raised when backtest result contract invariants are violated."""

    pass
