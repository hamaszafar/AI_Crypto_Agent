"""
Backtest Configuration Contracts.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict

from app.backtesting.contracts.enums import PositionSizingType
from app.backtesting.contracts.exceptions import InvalidBacktestConfigError


@dataclass(frozen=True, slots=True)
class PositionSizingConfig:
    """Position sizing configuration for backtest execution."""

    sizing_type: PositionSizingType
    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.sizing_type, PositionSizingType):
            if isinstance(self.sizing_type, str):
                try:
                    object.__setattr__(
                        self, "sizing_type", PositionSizingType(self.sizing_type)
                    )
                except ValueError:
                    raise InvalidBacktestConfigError(
                        f"Invalid position sizing type: {self.sizing_type}"
                    )
            else:
                raise InvalidBacktestConfigError(
                    f"Invalid position sizing type: {self.sizing_type}"
                )

        if not isinstance(self.value, Decimal):
            try:
                object.__setattr__(self, "value", Decimal(str(self.value)))
            except Exception as e:
                raise InvalidBacktestConfigError(
                    f"Invalid position sizing value: {self.value}"
                ) from e

        if self.value <= Decimal("0"):
            raise InvalidBacktestConfigError(
                f"Position sizing value must be strictly positive (> 0), got {self.value}"
            )

        if self.sizing_type == PositionSizingType.PERCENT_OF_EQUITY and self.value > Decimal("1"):
            # Assume fraction 0..1 or 1..100. If > 100, reject
            if self.value > Decimal("100"):
                raise InvalidBacktestConfigError(
                    f"PERCENT_OF_EQUITY cannot exceed 100%, got {self.value}"
                )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sizing_type": self.sizing_type.value,
            "value": str(self.value),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PositionSizingConfig":
        return cls(
            sizing_type=PositionSizingType(data["sizing_type"]),
            value=Decimal(str(data["value"])),
        )


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    """Configuration required to execute a backtest."""

    exchange: str
    symbol: str
    timeframe: str
    start_time: datetime
    end_time: datetime
    initial_capital: Decimal
    position_sizing: PositionSizingConfig
    fee_rate: Decimal = Decimal("0")
    slippage_rate: Decimal = Decimal("0")
    strategy_id: str = "default_strategy"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.exchange or not isinstance(self.exchange, str):
            raise InvalidBacktestConfigError("exchange must be a non-empty string")
        if not self.symbol or not isinstance(self.symbol, str):
            raise InvalidBacktestConfigError("symbol must be a non-empty string")
        if not self.timeframe or not isinstance(self.timeframe, str):
            raise InvalidBacktestConfigError("timeframe must be a non-empty string")

        if not isinstance(self.start_time, datetime):
            raise InvalidBacktestConfigError("start_time must be a datetime")
        if self.start_time.tzinfo is None or self.start_time.tzinfo.utcoffset(self.start_time) is None:
            raise InvalidBacktestConfigError("start_time must be timezone-aware")

        if not isinstance(self.end_time, datetime):
            raise InvalidBacktestConfigError("end_time must be a datetime")
        if self.end_time.tzinfo is None or self.end_time.tzinfo.utcoffset(self.end_time) is None:
            raise InvalidBacktestConfigError("end_time must be timezone-aware")

        if self.start_time >= self.end_time:
            raise InvalidBacktestConfigError(
                f"start_time ({self.start_time}) must be strictly before end_time ({self.end_time})"
            )

        if not isinstance(self.initial_capital, Decimal):
            try:
                object.__setattr__(self, "initial_capital", Decimal(str(self.initial_capital)))
            except Exception as e:
                raise InvalidBacktestConfigError("initial_capital must be a Decimal") from e

        if self.initial_capital <= Decimal("0"):
            raise InvalidBacktestConfigError(
                f"initial_capital must be strictly positive (> 0), got {self.initial_capital}"
            )

        if not isinstance(self.position_sizing, PositionSizingConfig):
            if isinstance(self.position_sizing, dict):
                object.__setattr__(
                    self, "position_sizing", PositionSizingConfig.from_dict(self.position_sizing)
                )
            else:
                raise InvalidBacktestConfigError("position_sizing must be a PositionSizingConfig")

        if not isinstance(self.fee_rate, Decimal):
            try:
                object.__setattr__(self, "fee_rate", Decimal(str(self.fee_rate)))
            except Exception as e:
                raise InvalidBacktestConfigError("fee_rate must be a Decimal") from e

        if self.fee_rate < Decimal("0"):
            raise InvalidBacktestConfigError(f"fee_rate cannot be negative, got {self.fee_rate}")

        if not isinstance(self.slippage_rate, Decimal):
            try:
                object.__setattr__(self, "slippage_rate", Decimal(str(self.slippage_rate)))
            except Exception as e:
                raise InvalidBacktestConfigError("slippage_rate must be a Decimal") from e

        if self.slippage_rate < Decimal("0"):
            raise InvalidBacktestConfigError(
                f"slippage_rate cannot be negative, got {self.slippage_rate}"
            )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exchange": self.exchange,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "initial_capital": str(self.initial_capital),
            "position_sizing": self.position_sizing.to_dict(),
            "fee_rate": str(self.fee_rate),
            "slippage_rate": str(self.slippage_rate),
            "strategy_id": self.strategy_id,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BacktestConfig":
        return cls(
            exchange=str(data["exchange"]),
            symbol=str(data["symbol"]),
            timeframe=str(data["timeframe"]),
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]),
            initial_capital=Decimal(str(data["initial_capital"])),
            position_sizing=PositionSizingConfig.from_dict(data["position_sizing"]),
            fee_rate=Decimal(str(data.get("fee_rate", "0"))),
            slippage_rate=Decimal(str(data.get("slippage_rate", "0"))),
            strategy_id=str(data.get("strategy_id", "default_strategy")),
            metadata=dict(data.get("metadata", {})),
        )
