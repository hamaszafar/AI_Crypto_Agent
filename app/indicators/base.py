import abc
from decimal import Decimal
from typing import Mapping

from app.indicators.input import IndicatorInput
from app.indicators.models import IndicatorMetadata, IndicatorResult


class BaseIndicator(abc.ABC):
    """Base interface for all technical indicators."""

    @property
    @abc.abstractmethod
    def metadata(self) -> IndicatorMetadata:
        """Return the indicator's metadata."""
        pass

    @abc.abstractmethod
    def calculate(self, data: IndicatorInput) -> IndicatorResult:
        """
        Calculate the indicator for the provided input data.
        
        Args:
            data: IndicatorInput containing chronological candles.
            
        Returns:
            IndicatorResult with the calculated values for the latest candle.
            
        Raises:
            ValueError: If the input data is insufficient or invalid.
        """
        pass
