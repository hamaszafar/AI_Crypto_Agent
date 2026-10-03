"""
Position Contract.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
import uuid

from app.backtesting.contracts.enums import PositionSide
from app.backtesting.contracts.exceptions import InvalidPositionError


@dataclass(frozen=True, slots=True)
class Position:
    """Contract representing a trading position."""

    exchange: str
    symbol: str
    side: PositionSide
    entry_timestamp: datetime
    entry_price: Decimal
    quantity: Decimal
    position_id: str = ""
    exit_timestamp: Optional[datetime] = None
    exit_price: Optional[Decimal] = None
    realized_pnl: Optional[Decimal] = None
    unrealized_pnl: Decimal = Decimal("0")
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None

    def __post_init__(self) -> None:
        if not self.position_id:
            object.__setattr__(
                self, "position_id", f"pos_{self.entry_timestamp.timestamp()}_{uuid.uuid4().hex[:6]}"
            )

        if not self.exchange or not isinstance(self.exchange, str):
            raise InvalidPositionError("exchange must be a non-empty string")
        if not self.symbol or not isinstance(self.symbol, str):
            raise InvalidPositionError("symbol must be a non-empty string")

        if not isinstance(self.side, PositionSide):
            if isinstance(self.side, str):
                try:
                    object.__setattr__(self, "side", PositionSide(self.side))
                except ValueError:
                    raise InvalidPositionError(f"Invalid side: {self.side}")
            else:
                raise InvalidPositionError(f"Invalid side: {self.side}")

        if not isinstance(self.entry_timestamp, datetime):
            raise InvalidPositionError("entry_timestamp must be a datetime")
        if self.entry_timestamp.tzinfo is None or self.entry_timestamp.tzinfo.utcoffset(self.entry_timestamp) is None:
            raise InvalidPositionError("entry_timestamp must be timezone-aware")

        if not isinstance(self.entry_price, Decimal):
            try:
                object.__setattr__(self, "entry_price", Decimal(str(self.entry_price)))
            except Exception as e:
                raise InvalidPositionError("entry_price must be a Decimal") from e
        if self.entry_price <= Decimal("0"):
            raise InvalidPositionError(f"entry_price must be strictly positive (> 0), got {self.entry_price}")

        if not isinstance(self.quantity, Decimal):
            try:
                object.__setattr__(self, "quantity", Decimal(str(self.quantity)))
            except Exception as e:
                raise InvalidPositionError("quantity must be a Decimal") from e
        if self.quantity < Decimal("0"):
            raise InvalidPositionError(f"quantity cannot be negative, got {self.quantity}")

        if self.side == PositionSide.FLAT and self.quantity != Decimal("0"):
             raise InvalidPositionError("FLAT position must have 0 quantity")

        if self.exit_timestamp is not None:
            if not isinstance(self.exit_timestamp, datetime):
                raise InvalidPositionError("exit_timestamp must be a datetime")
            if self.exit_timestamp.tzinfo is None or self.exit_timestamp.tzinfo.utcoffset(self.exit_timestamp) is None:
                raise InvalidPositionError("exit_timestamp must be timezone-aware")
            if self.exit_timestamp < self.entry_timestamp:
                raise InvalidPositionError(f"exit_timestamp ({self.exit_timestamp}) cannot be before entry_timestamp ({self.entry_timestamp})")

        if self.exit_price is not None:
            if not isinstance(self.exit_price, Decimal):
                try:
                    object.__setattr__(self, "exit_price", Decimal(str(self.exit_price)))
                except Exception as e:
                    raise InvalidPositionError("exit_price must be a Decimal") from e
            if self.exit_price <= Decimal("0"):
                raise InvalidPositionError(f"exit_price must be strictly positive (> 0), got {self.exit_price}")

        if self.realized_pnl is not None and not isinstance(self.realized_pnl, Decimal):
            try:
                object.__setattr__(self, "realized_pnl", Decimal(str(self.realized_pnl)))
            except Exception as e:
                raise InvalidPositionError("realized_pnl must be a Decimal") from e

        if not isinstance(self.unrealized_pnl, Decimal):
            try:
                object.__setattr__(self, "unrealized_pnl", Decimal(str(self.unrealized_pnl)))
            except Exception as e:
                raise InvalidPositionError("unrealized_pnl must be a Decimal") from e

        if self.stop_loss is not None:
            if not isinstance(self.stop_loss, Decimal):
                try:
                    object.__setattr__(self, "stop_loss", Decimal(str(self.stop_loss)))
                except Exception as e:
                    raise InvalidPositionError("stop_loss must be a Decimal") from e
            if self.stop_loss <= Decimal("0"):
                raise InvalidPositionError(f"stop_loss must be strictly positive (> 0), got {self.stop_loss}")

        if self.take_profit is not None:
            if not isinstance(self.take_profit, Decimal):
                try:
                    object.__setattr__(self, "take_profit", Decimal(str(self.take_profit)))
                except Exception as e:
                    raise InvalidPositionError("take_profit must be a Decimal") from e
            if self.take_profit <= Decimal("0"):
                raise InvalidPositionError(f"take_profit must be strictly positive (> 0), got {self.take_profit}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position_id": self.position_id,
            "exchange": self.exchange,
            "symbol": self.symbol,
            "side": self.side.value,
            "entry_timestamp": self.entry_timestamp.isoformat(),
            "entry_price": str(self.entry_price),
            "exit_timestamp": self.exit_timestamp.isoformat() if self.exit_timestamp is not None else None,
            "exit_price": str(self.exit_price) if self.exit_price is not None else None,
            "quantity": str(self.quantity),
            "realized_pnl": str(self.realized_pnl) if self.realized_pnl is not None else None,
            "unrealized_pnl": str(self.unrealized_pnl),
            "stop_loss": str(self.stop_loss) if self.stop_loss is not None else None,
            "take_profit": str(self.take_profit) if self.take_profit is not None else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Position":
        exit_ts = datetime.fromisoformat(data["exit_timestamp"]) if data.get("exit_timestamp") is not None else None
        exit_p = Decimal(str(data["exit_price"])) if data.get("exit_price") is not None else None
        sl = Decimal(str(data["stop_loss"])) if data.get("stop_loss") is not None else None
        tp = Decimal(str(data["take_profit"])) if data.get("take_profit") is not None else None
        rpnl = Decimal(str(data["realized_pnl"])) if data.get("realized_pnl") is not None else None
        upnl = Decimal(str(data.get("unrealized_pnl", "0")))

        return cls(
            position_id=str(data.get("position_id", "")),
            exchange=str(data["exchange"]),
            symbol=str(data["symbol"]),
            side=PositionSide(data["side"]),
            entry_timestamp=datetime.fromisoformat(data["entry_timestamp"]),
            entry_price=Decimal(str(data["entry_price"])),
            exit_timestamp=exit_ts,
            exit_price=exit_p,
            quantity=Decimal(str(data["quantity"])),
            realized_pnl=rpnl,
            unrealized_pnl=upnl,
            stop_loss=sl,
            take_profit=tp,
        )
