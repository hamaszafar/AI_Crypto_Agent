"""
Trade Contract.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
import uuid

from app.backtesting.contracts.enums import TradeStatus
from app.backtesting.contracts.exceptions import InvalidTradeError
from app.signals.models import SignalDirection


@dataclass(frozen=True, slots=True)
class SimulatedTrade:
    """Contract representing a simulated trade."""

    exchange: str
    symbol: str
    timeframe: str
    direction: SignalDirection
    entry_timestamp: datetime
    entry_price: Decimal
    quantity: Decimal
    trade_id: str = ""
    source_signal_id: Optional[str] = None
    exit_timestamp: Optional[datetime] = None
    exit_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    fees: Decimal = Decimal("0")
    slippage: Decimal = Decimal("0")
    realized_pnl: Optional[Decimal] = None
    status: TradeStatus = TradeStatus.PENDING
    exit_reason: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.trade_id:
            object.__setattr__(
                self, "trade_id", f"trd_{self.entry_timestamp.timestamp()}_{uuid.uuid4().hex[:6]}"
            )

        if not self.exchange or not isinstance(self.exchange, str):
            raise InvalidTradeError("exchange must be a non-empty string")
        if not self.symbol or not isinstance(self.symbol, str):
            raise InvalidTradeError("symbol must be a non-empty string")
        if not self.timeframe or not isinstance(self.timeframe, str):
            raise InvalidTradeError("timeframe must be a non-empty string")

        if not isinstance(self.direction, SignalDirection):
            if isinstance(self.direction, str):
                try:
                    object.__setattr__(self, "direction", SignalDirection(self.direction))
                except ValueError:
                    raise InvalidTradeError(f"Invalid direction: {self.direction}")
            else:
                raise InvalidTradeError(f"Invalid direction: {self.direction}")

        if not isinstance(self.entry_timestamp, datetime):
            raise InvalidTradeError("entry_timestamp must be a datetime")
        if self.entry_timestamp.tzinfo is None or self.entry_timestamp.tzinfo.utcoffset(self.entry_timestamp) is None:
            raise InvalidTradeError("entry_timestamp must be timezone-aware")

        if not isinstance(self.entry_price, Decimal):
            try:
                object.__setattr__(self, "entry_price", Decimal(str(self.entry_price)))
            except Exception as e:
                raise InvalidTradeError("entry_price must be a Decimal") from e
        if self.entry_price <= Decimal("0"):
            raise InvalidTradeError(f"entry_price must be strictly positive (> 0), got {self.entry_price}")

        if not isinstance(self.quantity, Decimal):
            try:
                object.__setattr__(self, "quantity", Decimal(str(self.quantity)))
            except Exception as e:
                raise InvalidTradeError("quantity must be a Decimal") from e
        if self.quantity <= Decimal("0"):
            raise InvalidTradeError(f"quantity must be strictly positive (> 0), got {self.quantity}")

        if not isinstance(self.fees, Decimal):
            try:
                object.__setattr__(self, "fees", Decimal(str(self.fees)))
            except Exception as e:
                raise InvalidTradeError("fees must be a Decimal") from e
        if self.fees < Decimal("0"):
            raise InvalidTradeError(f"fees cannot be negative, got {self.fees}")

        if not isinstance(self.slippage, Decimal):
            try:
                object.__setattr__(self, "slippage", Decimal(str(self.slippage)))
            except Exception as e:
                raise InvalidTradeError("slippage must be a Decimal") from e
        if self.slippage < Decimal("0"):
            raise InvalidTradeError(f"slippage cannot be negative, got {self.slippage}")

        if not isinstance(self.status, TradeStatus):
            if isinstance(self.status, str):
                try:
                    object.__setattr__(self, "status", TradeStatus(self.status))
                except ValueError:
                    raise InvalidTradeError(f"Invalid status: {self.status}")
            else:
                raise InvalidTradeError(f"Invalid status: {self.status}")

        if self.exit_timestamp is not None:
            if not isinstance(self.exit_timestamp, datetime):
                raise InvalidTradeError("exit_timestamp must be a datetime")
            if self.exit_timestamp.tzinfo is None or self.exit_timestamp.tzinfo.utcoffset(self.exit_timestamp) is None:
                raise InvalidTradeError("exit_timestamp must be timezone-aware")
            if self.exit_timestamp < self.entry_timestamp:
                raise InvalidTradeError(f"exit_timestamp ({self.exit_timestamp}) cannot be before entry_timestamp ({self.entry_timestamp})")

        if self.exit_price is not None:
            if not isinstance(self.exit_price, Decimal):
                try:
                    object.__setattr__(self, "exit_price", Decimal(str(self.exit_price)))
                except Exception as e:
                    raise InvalidTradeError("exit_price must be a Decimal") from e
            if self.exit_price <= Decimal("0"):
                raise InvalidTradeError(f"exit_price must be strictly positive (> 0), got {self.exit_price}")

        if self.status == TradeStatus.CLOSED:
            if self.exit_timestamp is None:
                raise InvalidTradeError("exit_timestamp must be provided when status is CLOSED")
            if self.exit_price is None:
                raise InvalidTradeError("exit_price must be provided when status is CLOSED")

        if self.stop_loss is not None:
            if not isinstance(self.stop_loss, Decimal):
                try:
                    object.__setattr__(self, "stop_loss", Decimal(str(self.stop_loss)))
                except Exception as e:
                    raise InvalidTradeError("stop_loss must be a Decimal") from e
            if self.stop_loss <= Decimal("0"):
                raise InvalidTradeError(f"stop_loss must be strictly positive (> 0), got {self.stop_loss}")

        if self.take_profit is not None:
            if not isinstance(self.take_profit, Decimal):
                try:
                    object.__setattr__(self, "take_profit", Decimal(str(self.take_profit)))
                except Exception as e:
                    raise InvalidTradeError("take_profit must be a Decimal") from e
            if self.take_profit <= Decimal("0"):
                raise InvalidTradeError(f"take_profit must be strictly positive (> 0), got {self.take_profit}")

        if self.realized_pnl is not None and not isinstance(self.realized_pnl, Decimal):
            try:
                object.__setattr__(self, "realized_pnl", Decimal(str(self.realized_pnl)))
            except Exception as e:
                raise InvalidTradeError("realized_pnl must be a Decimal") from e

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "source_signal_id": self.source_signal_id,
            "exchange": self.exchange,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "direction": self.direction.value,
            "entry_timestamp": self.entry_timestamp.isoformat(),
            "entry_price": str(self.entry_price),
            "exit_timestamp": self.exit_timestamp.isoformat() if self.exit_timestamp is not None else None,
            "exit_price": str(self.exit_price) if self.exit_price is not None else None,
            "quantity": str(self.quantity),
            "stop_loss": str(self.stop_loss) if self.stop_loss is not None else None,
            "take_profit": str(self.take_profit) if self.take_profit is not None else None,
            "fees": str(self.fees),
            "slippage": str(self.slippage),
            "realized_pnl": str(self.realized_pnl) if self.realized_pnl is not None else None,
            "status": self.status.value,
            "exit_reason": self.exit_reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SimulatedTrade":
        exit_ts = datetime.fromisoformat(data["exit_timestamp"]) if data.get("exit_timestamp") is not None else None
        exit_p = Decimal(str(data["exit_price"])) if data.get("exit_price") is not None else None
        sl = Decimal(str(data["stop_loss"])) if data.get("stop_loss") is not None else None
        tp = Decimal(str(data["take_profit"])) if data.get("take_profit") is not None else None
        pnl = Decimal(str(data["realized_pnl"])) if data.get("realized_pnl") is not None else None

        return cls(
            trade_id=str(data.get("trade_id", "")),
            source_signal_id=data.get("source_signal_id"),
            exchange=str(data["exchange"]),
            symbol=str(data["symbol"]),
            timeframe=str(data["timeframe"]),
            direction=SignalDirection(data["direction"]),
            entry_timestamp=datetime.fromisoformat(data["entry_timestamp"]),
            entry_price=Decimal(str(data["entry_price"])),
            exit_timestamp=exit_ts,
            exit_price=exit_p,
            quantity=Decimal(str(data["quantity"])),
            stop_loss=sl,
            take_profit=tp,
            fees=Decimal(str(data.get("fees", "0"))),
            slippage=Decimal(str(data.get("slippage", "0"))),
            realized_pnl=pnl,
            status=TradeStatus(data.get("status", TradeStatus.PENDING)),
            exit_reason=data.get("exit_reason"),
        )
