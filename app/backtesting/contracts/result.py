"""
Backtest Result Contract.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from app.backtesting.contracts.config import BacktestConfig
from app.backtesting.contracts.enums import BacktestStatus
from app.backtesting.contracts.exceptions import InvalidBacktestResultError
from app.backtesting.contracts.signal_outcome import SignalOutcome
from app.backtesting.contracts.trade import SimulatedTrade


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Contract representing the complete result of a backtest run."""

    config: BacktestConfig
    status: BacktestStatus
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    start_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None
    candles_processed: int = 0
    signals_generated: int = 0
    signals_resolved: int = 0
    trades_opened: int = 0
    trades_closed: int = 0
    final_capital: Optional[Decimal] = None
    realized_pnl: Optional[Decimal] = None
    signal_outcomes: List[SignalOutcome] = field(default_factory=list)
    trades: List[SimulatedTrade] = field(default_factory=list)
    execution_metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.result_id or not isinstance(self.result_id, str):
            raise InvalidBacktestResultError("result_id must be a non-empty string")

        if not isinstance(self.config, BacktestConfig):
            if isinstance(self.config, dict):
                object.__setattr__(self, "config", BacktestConfig.from_dict(self.config))
            else:
                raise InvalidBacktestResultError("config must be a BacktestConfig")

        if not isinstance(self.status, BacktestStatus):
            if isinstance(self.status, str):
                try:
                    object.__setattr__(self, "status", BacktestStatus(self.status))
                except ValueError:
                    raise InvalidBacktestResultError(f"Invalid status: {self.status}")
            else:
                raise InvalidBacktestResultError(f"Invalid status: {self.status}")

        if self.start_timestamp is not None:
            if not isinstance(self.start_timestamp, datetime):
                raise InvalidBacktestResultError("start_timestamp must be a datetime")
            if self.start_timestamp.tzinfo is None or self.start_timestamp.tzinfo.utcoffset(self.start_timestamp) is None:
                raise InvalidBacktestResultError("start_timestamp must be timezone-aware")

        if self.end_timestamp is not None:
            if not isinstance(self.end_timestamp, datetime):
                raise InvalidBacktestResultError("end_timestamp must be a datetime")
            if self.end_timestamp.tzinfo is None or self.end_timestamp.tzinfo.utcoffset(self.end_timestamp) is None:
                raise InvalidBacktestResultError("end_timestamp must be timezone-aware")

            if self.start_timestamp is not None and self.end_timestamp < self.start_timestamp:
                raise InvalidBacktestResultError(
                    f"end_timestamp ({self.end_timestamp}) cannot be before start_timestamp ({self.start_timestamp})"
                )

        if not isinstance(self.candles_processed, int) or self.candles_processed < 0:
            raise InvalidBacktestResultError("candles_processed must be a non-negative integer")

        if not isinstance(self.signals_generated, int) or self.signals_generated < 0:
            raise InvalidBacktestResultError("signals_generated must be a non-negative integer")

        if not isinstance(self.signals_resolved, int) or self.signals_resolved < 0:
            raise InvalidBacktestResultError("signals_resolved must be a non-negative integer")

        if not isinstance(self.trades_opened, int) or self.trades_opened < 0:
            raise InvalidBacktestResultError("trades_opened must be a non-negative integer")

        if not isinstance(self.trades_closed, int) or self.trades_closed < 0:
            raise InvalidBacktestResultError("trades_closed must be a non-negative integer")

        if self.final_capital is not None:
            if not isinstance(self.final_capital, Decimal):
                try:
                    object.__setattr__(self, "final_capital", Decimal(str(self.final_capital)))
                except Exception as e:
                    raise InvalidBacktestResultError("final_capital must be a Decimal") from e

        if self.realized_pnl is not None:
            if not isinstance(self.realized_pnl, Decimal):
                try:
                    object.__setattr__(self, "realized_pnl", Decimal(str(self.realized_pnl)))
                except Exception as e:
                    raise InvalidBacktestResultError("realized_pnl must be a Decimal") from e

        if self.status == BacktestStatus.COMPLETED:
            if self.final_capital is None:
                raise InvalidBacktestResultError("final_capital must be provided when status is COMPLETED")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "config": self.config.to_dict(),
            "status": self.status.value,
            "start_timestamp": self.start_timestamp.isoformat() if self.start_timestamp else None,
            "end_timestamp": self.end_timestamp.isoformat() if self.end_timestamp else None,
            "candles_processed": self.candles_processed,
            "signals_generated": self.signals_generated,
            "signals_resolved": self.signals_resolved,
            "trades_opened": self.trades_opened,
            "trades_closed": self.trades_closed,
            "final_capital": str(self.final_capital) if self.final_capital is not None else None,
            "realized_pnl": str(self.realized_pnl) if self.realized_pnl is not None else None,
            "signal_outcomes": [o.to_dict() for o in self.signal_outcomes],
            "trades": [t.to_dict() for t in self.trades],
            "execution_metadata": dict(self.execution_metadata),
            "errors": list(self.errors),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BacktestResult":
        start_ts = datetime.fromisoformat(data["start_timestamp"]) if data.get("start_timestamp") else None
        end_ts = datetime.fromisoformat(data["end_timestamp"]) if data.get("end_timestamp") else None
        fc = Decimal(str(data["final_capital"])) if data.get("final_capital") is not None else None
        rpnl = Decimal(str(data["realized_pnl"])) if data.get("realized_pnl") is not None else None

        return cls(
            result_id=str(data.get("result_id", "")),
            config=BacktestConfig.from_dict(data["config"]),
            status=BacktestStatus(data["status"]),
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            candles_processed=int(data.get("candles_processed", 0)),
            signals_generated=int(data.get("signals_generated", 0)),
            signals_resolved=int(data.get("signals_resolved", 0)),
            trades_opened=int(data.get("trades_opened", 0)),
            trades_closed=int(data.get("trades_closed", 0)),
            final_capital=fc,
            realized_pnl=rpnl,
            signal_outcomes=[SignalOutcome.from_dict(o) for o in data.get("signal_outcomes", [])],
            trades=[SimulatedTrade.from_dict(t) for t in data.get("trades", [])],
            execution_metadata=dict(data.get("execution_metadata", {})),
            errors=list(data.get("errors", [])),
        )
