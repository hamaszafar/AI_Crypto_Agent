from decimal import Decimal
from app.indicators.base import BaseIndicator
from app.indicators.input import IndicatorInput
from app.indicators.models import IndicatorMetadata, IndicatorResult
from app.indicators.trend.ma import EMAIndicator

class MACDIndicator(BaseIndicator):
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.min_period = slow_period + signal_period
        
    @property
    def metadata(self) -> IndicatorMetadata:
        return IndicatorMetadata(
            name=f"MACD_{self.fast_period}_{self.slow_period}_{self.signal_period}",
            description="Moving Average Convergence Divergence",
            minimum_period=self.min_period
        )
        
    def calculate(self, data: IndicatorInput) -> IndicatorResult:
        meta = self.metadata
        if data.size < meta.minimum_period:
            raise ValueError(f"Insufficient data. Required {meta.minimum_period}")
            
        # We need a time series of MACD line to calculate the signal line
        macd_line_series = []
        
        # Calculate from the point where slow_period is available
        candles = data.candles
        
        multiplier_fast = Decimal("2.0") / Decimal(self.fast_period + 1)
        multiplier_slow = Decimal("2.0") / Decimal(self.slow_period + 1)
        
        # First EMA fast
        fast_ema = sum(c.close for c in candles[:self.fast_period]) / Decimal(self.fast_period)
        # First EMA slow
        slow_ema = sum(c.close for c in candles[:self.slow_period]) / Decimal(self.slow_period)
        
        # We need to advance fast_ema to slow_period index to sync them
        for c in candles[self.fast_period:self.slow_period]:
            fast_ema = (c.close - fast_ema) * multiplier_fast + fast_ema
            
        macd_line = fast_ema - slow_ema
        macd_line_series.append(macd_line)
        
        # Calculate the rest
        for c in candles[self.slow_period:]:
            fast_ema = (c.close - fast_ema) * multiplier_fast + fast_ema
            slow_ema = (c.close - slow_ema) * multiplier_slow + slow_ema
            macd_line_series.append(fast_ema - slow_ema)
            
        # Signal line is EMA of MACD line
        signal_ema = sum(macd_line_series[:self.signal_period]) / Decimal(self.signal_period)
        multiplier_signal = Decimal("2.0") / Decimal(self.signal_period + 1)
        
        for macd_val in macd_line_series[self.signal_period:]:
            signal_ema = (macd_val - signal_ema) * multiplier_signal + signal_ema
            
        latest_macd = macd_line_series[-1]
        histogram = latest_macd - signal_ema
        
        return IndicatorResult(
            indicator_name=meta.name,
            timestamp=data.latest.timestamp,
            values={
                "macd": latest_macd,
                "signal": signal_ema,
                "histogram": histogram
            }
        )
