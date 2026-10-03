"""
Signal Observation Contract.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
import uuid

from app.backtesting.contracts.exceptions import InvalidSignalObservationError
from app.signals.models import (
    Signal,
    SignalConfidence,
    SignalDirection,
    SignalStrength,
)


@dataclass(frozen=True, slots=True)
class SignalObservation:
    """Contract representing a signal produced during replay."""

    signal_id: str
    timestamp: datetime
    exchange: str
    symbol: str
    timeframe: str
    direction: SignalDirection
    strength: SignalStrength
    confidence: SignalConfidence
    score: Decimal
    entry_price: Decimal
    stop_loss: Optional[Decimal] = None
    take_profit: Optional[Decimal] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_signal: Optional[Signal] = None

    def __post_init__(self) -> None:
        if not self.signal_id or not isinstance(self.signal_id, str):
            raise InvalidSignalObservationError("signal_id must be a non-empty string")

        if not isinstance(self.timestamp, datetime):
            raise InvalidSignalObservationError("timestamp must be a datetime")
        if self.timestamp.tzinfo is None or self.timestamp.tzinfo.utcoffset(self.timestamp) is None:
            raise InvalidSignalObservationError("timestamp must be timezone-aware")

        if not self.exchange or not isinstance(self.exchange, str):
            raise InvalidSignalObservationError("exchange must be a non-empty string")
        if not self.symbol or not isinstance(self.symbol, str):
            raise InvalidSignalObservationError("symbol must be a non-empty string")
        if not self.timeframe or not isinstance(self.timeframe, str):
            raise InvalidSignalObservationError("timeframe must be a non-empty string")

        if not isinstance(self.direction, SignalDirection):
            if isinstance(self.direction, str):
                try:
                    object.__setattr__(self, "direction", SignalDirection(self.direction))
                except ValueError:
                    raise InvalidSignalObservationError(f"Invalid signal direction: {self.direction}")
            else:
                raise InvalidSignalObservationError(f"Invalid signal direction: {self.direction}")

        if not isinstance(self.strength, SignalStrength):
            if isinstance(self.strength, str):
                try:
                    object.__setattr__(self, "strength", SignalStrength(self.strength))
                except ValueError:
                    raise InvalidSignalObservationError(f"Invalid signal strength: {self.strength}")
            else:
                raise InvalidSignalObservationError(f"Invalid signal strength: {self.strength}")

        if not isinstance(self.confidence, SignalConfidence):
            if isinstance(self.confidence, str):
                try:
                    object.__setattr__(self, "confidence", SignalConfidence(self.confidence))
                except ValueError:
                    raise InvalidSignalObservationError(f"Invalid signal confidence: {self.confidence}")
            else:
                raise InvalidSignalObservationError(f"Invalid signal confidence: {self.confidence}")

        if not isinstance(self.score, Decimal):
            try:
                object.__setattr__(self, "score", Decimal(str(self.score)))
            except Exception as e:
                raise InvalidSignalObservationError("score must be a Decimal") from e

        if not isinstance(self.entry_price, Decimal):
            try:
                object.__setattr__(self, "entry_price", Decimal(str(self.entry_price)))
            except Exception as e:
                raise InvalidSignalObservationError("entry_price must be a Decimal") from e

        if self.entry_price <= Decimal("0"):
            raise InvalidSignalObservationError(
                f"entry_price must be strictly positive (> 0), got {self.entry_price}"
            )

        if self.stop_loss is not None:
            if not isinstance(self.stop_loss, Decimal):
                try:
                    object.__setattr__(self, "stop_loss", Decimal(str(self.stop_loss)))
                except Exception as e:
                    raise InvalidSignalObservationError("stop_loss must be a Decimal") from e
            if self.stop_loss <= Decimal("0"):
                raise InvalidSignalObservationError(
                    f"stop_loss must be strictly positive (> 0), got {self.stop_loss}"
                )

        if self.take_profit is not None:
            if not isinstance(self.take_profit, Decimal):
                try:
                    object.__setattr__(self, "take_profit", Decimal(str(self.take_profit)))
                except Exception as e:
                    raise InvalidSignalObservationError("take_profit must be a Decimal") from e
            if self.take_profit <= Decimal("0"):
                raise InvalidSignalObservationError(
                    f"take_profit must be strictly positive (> 0), got {self.take_profit}"
                )

    @classmethod
    def from_signal(
        cls,
        signal: Signal,
        entry_price: Decimal,
        stop_loss: Optional[Decimal] = None,
        take_profit: Optional[Decimal] = None,
        signal_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "SignalObservation":
        """Adapt an existing Signal Engine object into a SignalObservation contract."""
        sid = signal_id or f"sig_{signal.context.timestamp.timestamp()}_{uuid.uuid4().hex[:8]}"
        meta = metadata or {}
        if "reasons" not in meta:
            meta["reasons"] = [r.value for r in signal.reasons]

        return cls(
            signal_id=sid,
            timestamp=signal.context.timestamp,
            exchange=signal.context.exchange,
            symbol=signal.context.symbol,
            timeframe=signal.context.timeframe,
            direction=signal.direction,
            strength=signal.strength,
            confidence=signal.confidence,
            score=signal.score,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata=meta,
            raw_signal=signal,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "timestamp": self.timestamp.isoformat(),
            "exchange": self.exchange,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "direction": self.direction.value,
            "strength": self.strength.value,
            "confidence": self.confidence.value,
            "score": str(self.score),
            "entry_price": str(self.entry_price),
            "stop_loss": str(self.stop_loss) if self.stop_loss is not None else None,
            "take_profit": str(self.take_profit) if self.take_profit is not None else None,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SignalObservation":
        stop_loss = Decimal(str(data["stop_loss"])) if data.get("stop_loss") is not None else None
        take_profit = (
            Decimal(str(data["take_profit"])) if data.get("take_profit") is not None else None
        )
        return cls(
            signal_id=str(data["signal_id"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            exchange=str(data["exchange"]),
            symbol=str(data["symbol"]),
            timeframe=str(data["timeframe"]),
            direction=SignalDirection(data["direction"]),
            strength=SignalStrength(data["strength"]),
            confidence=SignalConfidence(data["confidence"]),
            score=Decimal(str(data["score"])),
            entry_price=Decimal(str(data["entry_price"])),
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata=dict(data.get("metadata", {})),
        )
