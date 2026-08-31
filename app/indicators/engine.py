from app.indicators.base import BaseIndicator
from app.indicators.input import IndicatorInput
from app.indicators.models import IndicatorResult


class IndicatorEngine:
    """
    Engine to calculate multiple indicators for a given input dataset.
    """
    
    def __init__(self, indicators: list[BaseIndicator]) -> None:
        if not indicators:
            raise ValueError("At least one indicator must be provided.")
        self.indicators = list(indicators)
        
    def calculate_all(self, data: IndicatorInput) -> dict[str, IndicatorResult]:
        """
        Calculate all configured indicators.
        
        Args:
            data: The market data input.
            
        Returns:
            A dictionary mapping indicator name to its result.
        """
        if not data or data.size == 0:
            raise ValueError("Input data cannot be empty.")
            
        results = {}
        for indicator in self.indicators:
            meta = indicator.metadata
            if data.size < meta.minimum_period:
                raise ValueError(
                    f"Insufficient data for indicator '{meta.name}'. "
                    f"Required: {meta.minimum_period}, Provided: {data.size}"
                )
                
            results[meta.name] = indicator.calculate(data)
            
        return results
