from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Mapping


@dataclass(frozen=True)
class IndicatorMetadata:
    """Metadata describing an indicator."""
    name: str
    description: str
    minimum_period: int


@dataclass(frozen=True)
class IndicatorResult:
    """Result from an indicator calculation for a specific point in time."""
    indicator_name: str
    timestamp: datetime
    values: Mapping[str, Decimal]

    def get(self, key: str) -> Decimal:
        """Get a specific value from the result."""
        if key not in self.values:
            raise KeyError(f"Value '{key}' not found in indicator '{self.indicator_name}' result.")
        return self.values[key]
