from typing import Any

from app.indicators.base import BaseIndicator
from app.indicators.registry import IndicatorRegistry


class IndicatorFactory:
    """Factory to instantiate registered indicators."""
    
    @staticmethod
    def create(name: str, **kwargs: Any) -> BaseIndicator:
        """
        Create a new instance of an indicator.
        
        Args:
            name: The registered name of the indicator.
            **kwargs: Configuration arguments for the indicator (e.g. period).
            
        Returns:
            An instance of the indicator.
        """
        indicator_class = IndicatorRegistry.get(name)
        return indicator_class(**kwargs)
