"""
Backtest Request Contract.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import uuid

from app.backtesting.contracts.config import BacktestConfig
from app.backtesting.contracts.exceptions import InvalidBacktestRequestError
from app.backtesting.datasets.models import HistoricalDataset


@dataclass(frozen=True, slots=True)
class BacktestRequest:
    """Contract representing an executable backtest request."""

    config: BacktestConfig
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    dataset_id: Optional[str] = None
    dataset: Optional[HistoricalDataset] = None
    signal_config: Dict[str, Any] = field(default_factory=dict)
    execution_config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.config, BacktestConfig):
            if isinstance(self.config, dict):
                object.__setattr__(self, "config", BacktestConfig.from_dict(self.config))
            else:
                raise InvalidBacktestRequestError("config must be a BacktestConfig instance")

        if not self.request_id or not isinstance(self.request_id, str):
            raise InvalidBacktestRequestError("request_id must be a non-empty string")

        if self.dataset is not None:
            if not isinstance(self.dataset, HistoricalDataset):
                raise InvalidBacktestRequestError("dataset must be an instance of HistoricalDataset")

            # Validate consistency between BacktestConfig and dataset metadata
            if self.config.exchange.lower() != self.dataset.exchange.lower():
                raise InvalidBacktestRequestError(
                    f"Config exchange '{self.config.exchange}' does not match dataset exchange '{self.dataset.exchange}'"
                )
            if self.config.symbol.upper() != self.dataset.symbol.upper():
                raise InvalidBacktestRequestError(
                    f"Config symbol '{self.config.symbol}' does not match dataset symbol '{self.dataset.symbol}'"
                )
            if self.config.timeframe.lower() != self.dataset.timeframe.lower():
                raise InvalidBacktestRequestError(
                    f"Config timeframe '{self.config.timeframe}' does not match dataset timeframe '{self.dataset.timeframe}'"
                )

            # Check if dataset_id matches
            if self.dataset_id is None:
                object.__setattr__(self, "dataset_id", self.dataset.dataset_id)
            elif self.dataset_id != self.dataset.dataset_id:
                raise InvalidBacktestRequestError(
                    f"Provided dataset_id '{self.dataset_id}' does not match dataset's actual ID '{self.dataset.dataset_id}'"
                )

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "request_id": self.request_id,
            "config": self.config.to_dict(),
            "dataset_id": self.dataset_id,
            "signal_config": dict(self.signal_config),
            "execution_config": dict(self.execution_config),
        }
        if self.dataset is not None:
            d["dataset"] = self.dataset.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BacktestRequest":
        dataset = HistoricalDataset.from_dict(data["dataset"]) if "dataset" in data and data["dataset"] is not None else None
        return cls(
            request_id=str(data["request_id"]),
            config=BacktestConfig.from_dict(data["config"]),
            dataset_id=data.get("dataset_id"),
            dataset=dataset,
            signal_config=dict(data.get("signal_config", {})),
            execution_config=dict(data.get("execution_config", {})),
        )
