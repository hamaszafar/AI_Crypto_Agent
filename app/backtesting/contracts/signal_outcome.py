"""
Signal Outcome Contract.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
import uuid

from app.backtesting.contracts.enums import SignalOutcomeStatus
from app.backtesting.contracts.exceptions import InvalidSignalOutcomeError
from app.signals.models import SignalDirection


@dataclass(frozen=True, slots=True)
class SignalOutcome:
    """Contract representing what happened to a generated signal after replay continued."""

    signal_id: str
    signal_timestamp: datetime
    status: SignalOutcomeStatus
    entry_price: Decimal
    direction: SignalDirection
    outcome_id: str = ""
    resolution_timestamp: Optional[datetime] = None
    exit_price: Optional[Decimal] = None
    realized_pnl: Optional[Decimal] = None
    realized_return: Optional[Decimal] = None
    reason: Optional[str] = None
    related_trade_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.outcome_id:
            object.__setattr__(
                self, "outcome_id", f"out_{self.signal_id}_{uuid.uuid4().hex[:6]}"
            )

        if not self.signal_id or not isinstance(self.signal_id, str):
            raise InvalidSignalOutcomeError("signal_id must be a non-empty string")

        if not isinstance(self.signal_timestamp, datetime):
            raise InvalidSignalOutcomeError("signal_timestamp must be a datetime")
        if (
            self.signal_timestamp.tzinfo is None
            or self.signal_timestamp.tzinfo.utcoffset(self.signal_timestamp) is None
        ):
            raise InvalidSignalOutcomeError("signal_timestamp must be timezone-aware")

        if not isinstance(self.status, SignalOutcomeStatus):
            if isinstance(self.status, str):
                try:
                    object.__setattr__(self, "status", SignalOutcomeStatus(self.status))
                except ValueError:
                    raise InvalidSignalOutcomeError(f"Invalid signal outcome status: {self.status}")
            else:
                raise InvalidSignalOutcomeError(f"Invalid signal outcome status: {self.status}")

        if not isinstance(self.direction, SignalDirection):
            if isinstance(self.direction, str):
                try:
                    object.__setattr__(self, "direction", SignalDirection(self.direction))
                except ValueError:
                    raise InvalidSignalOutcomeError(f"Invalid direction: {self.direction}")
            else:
                raise InvalidSignalOutcomeError(f"Invalid direction: {self.direction}")

        if not isinstance(self.entry_price, Decimal):
            try:
                object.__setattr__(self, "entry_price", Decimal(str(self.entry_price)))
            except Exception as e:
                raise InvalidSignalOutcomeError("entry_price must be a Decimal") from e

        if self.entry_price <= Decimal("0"):
            raise InvalidSignalOutcomeError(
                f"entry_price must be strictly positive (> 0), got {self.entry_price}"
            )

        if self.resolution_timestamp is not None:
            if not isinstance(self.resolution_timestamp, datetime):
                raise InvalidSignalOutcomeError("resolution_timestamp must be a datetime")
            if (
                self.resolution_timestamp.tzinfo is None
                or self.resolution_timestamp.tzinfo.utcoffset(self.resolution_timestamp) is None
            ):
                raise InvalidSignalOutcomeError("resolution_timestamp must be timezone-aware")

            if self.resolution_timestamp < self.signal_timestamp:
                raise InvalidSignalOutcomeError(
                    f"resolution_timestamp ({self.resolution_timestamp}) cannot be before signal_timestamp ({self.signal_timestamp})"
                )

        if self.exit_price is not None:
            if not isinstance(self.exit_price, Decimal):
                try:
                    object.__setattr__(self, "exit_price", Decimal(str(self.exit_price)))
                except Exception as e:
                    raise InvalidSignalOutcomeError("exit_price must be a Decimal") from e
            if self.exit_price <= Decimal("0"):
                raise InvalidSignalOutcomeError(
                    f"exit_price must be strictly positive (> 0), got {self.exit_price}"
                )

        if self.realized_pnl is not None and not isinstance(self.realized_pnl, Decimal):
            try:
                object.__setattr__(self, "realized_pnl", Decimal(str(self.realized_pnl)))
            except Exception as e:
                raise InvalidSignalOutcomeError("realized_pnl must be a Decimal") from e

        if self.realized_return is not None and not isinstance(self.realized_return, Decimal):
            try:
                object.__setattr__(self, "realized_return", Decimal(str(self.realized_return)))
            except Exception as e:
                raise InvalidSignalOutcomeError("realized_return must be a Decimal") from e

    def to_dict(self) -> Dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "signal_id": self.signal_id,
            "signal_timestamp": self.signal_timestamp.isoformat(),
            "resolution_timestamp": (
                self.resolution_timestamp.isoformat()
                if self.resolution_timestamp is not None
                else None
            ),
            "status": self.status.value,
            "entry_price": str(self.entry_price),
            "exit_price": str(self.exit_price) if self.exit_price is not None else None,
            "direction": self.direction.value,
            "realized_pnl": str(self.realized_pnl) if self.realized_pnl is not None else None,
            "realized_return": (
                str(self.realized_return) if self.realized_return is not None else None
            ),
            "reason": self.reason,
            "related_trade_id": self.related_trade_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignalOutcome":
        res_ts = (
            datetime.fromisoformat(data["resolution_timestamp"])
            if data.get("resolution_timestamp") is not None
            else None
        )
        exit_p = (
            Decimal(str(data["exit_price"])) if data.get("exit_price") is not None else None
        )
        pnl = Decimal(str(data["realized_pnl"])) if data.get("realized_pnl") is not None else None
        ret = (
            Decimal(str(data["realized_return"]))
            if data.get("realized_return") is not None
            else None
        )
        return cls(
            outcome_id=str(data.get("outcome_id", "")),
            signal_id=str(data["signal_id"]),
            signal_timestamp=datetime.fromisoformat(data["signal_timestamp"]),
            resolution_timestamp=res_ts,
            status=SignalOutcomeStatus(data["status"]),
            entry_price=Decimal(str(data["entry_price"])),
            exit_price=exit_p,
            direction=SignalDirection(data["direction"]),
            realized_pnl=pnl,
            realized_return=ret,
            reason=data.get("reason"),
            related_trade_id=data.get("related_trade_id"),
        )
