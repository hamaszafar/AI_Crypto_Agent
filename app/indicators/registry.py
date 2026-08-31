from typing import Type
from app.indicators.base import BaseIndicator


class IndicatorRegistry:
    """Registry of available indicators."""
    
    _indicators: dict[str, Type[BaseIndicator]] = {}
    
    @classmethod
    def register(cls, name: str, indicator_class: Type[BaseIndicator]) -> None:
        """Register an indicator class."""
        if not name or not name.strip():
            raise ValueError("Indicator name cannot be empty.")
            
        name_lower = name.strip().lower()
        if name_lower in cls._indicators:
            raise ValueError(f"Indicator '{name_lower}' is already registered.")
            
        cls._indicators[name_lower] = indicator_class
        
    @classmethod
    def get(cls, name: str) -> Type[BaseIndicator]:
        """Retrieve an indicator class by name."""
        if not name or not name.strip():
            raise ValueError("Indicator name cannot be empty.")
            
        name_lower = name.strip().lower()
        if name_lower not in cls._indicators:
            raise ValueError(f"Indicator '{name_lower}' not found in registry.")
            
        return cls._indicators[name_lower]
        
    @classmethod
    def clear(cls) -> None:
        """Clear the registry (useful for testing)."""
        cls._indicators.clear()
        
    @classmethod
    def available(cls) -> list[str]:
        """Return a list of available indicator names."""
        return list(cls._indicators.keys())
