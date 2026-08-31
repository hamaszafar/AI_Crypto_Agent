from decimal import Decimal
from app.indicators.base import BaseIndicator
from app.indicators.input import IndicatorInput
from app.indicators.models import IndicatorMetadata, IndicatorResult

class SMAIndicator(BaseIndicator):
    def __init__(self, period: int = 14):
        if period < 1:
            raise ValueError("Period must be >= 1")
        self.period = period
        
    @property
    def metadata(self) -> IndicatorMetadata:
        return IndicatorMetadata(
            name=f"SMA_{self.period}",
            description="Simple Moving Average",
            minimum_period=self.period
        )
        
    def calculate(self, data: IndicatorInput) -> IndicatorResult:
        meta = self.metadata
        if data.size < meta.minimum_period:
            raise ValueError(f"Insufficient data. Required {meta.minimum_period}")
            
        candles = data.candles[-self.period:]
        total = sum(c.close for c in candles)
        sma = total / Decimal(self.period)
        
        return IndicatorResult(
            indicator_name=meta.name,
            timestamp=data.latest.timestamp,
            values={"sma": sma}
        )

class EMAIndicator(BaseIndicator):
    def __init__(self, period: int = 14):
        if period < 1:
            raise ValueError("Period must be >= 1")
        self.period = period
        
    @property
    def metadata(self) -> IndicatorMetadata:
        return IndicatorMetadata(
            name=f"EMA_{self.period}",
            description="Exponential Moving Average",
            minimum_period=self.period
        )
        
    def calculate(self, data: IndicatorInput) -> IndicatorResult:
        meta = self.metadata
        if data.size < meta.minimum_period:
            raise ValueError(f"Insufficient data. Required {meta.minimum_period}")
            
        candles = data.candles
        
        # Calculate initial SMA for the first 'period' candles
        initial_sma = sum(c.close for c in candles[:self.period]) / Decimal(self.period)
        
        multiplier = Decimal("2.0") / Decimal(self.period + 1)
        ema = initial_sma
        
        for c in candles[self.period:]:
            ema = (c.close - ema) * multiplier + ema
            
        return IndicatorResult(
            indicator_name=meta.name,
            timestamp=data.latest.timestamp,
            values={"ema": ema}
        )
