from decimal import Decimal, getcontext
from math import sqrt
from app.indicators.base import BaseIndicator
from app.indicators.input import IndicatorInput, IndicatorCandle
from app.indicators.models import IndicatorMetadata, IndicatorResult

class StochasticIndicator(BaseIndicator):
    """Stochastic Oscillator (%K and %D).
    %K = 100 * (Close - Lowest Low) / (Highest High - Lowest Low) over the lookback period.
    %D is a simple moving average of %K over d_period (default 3).
    """

    def __init__(self, period: int = 14, d_period: int = 3):
        if period < 1 or d_period < 1:
            raise ValueError("Periods must be >= 1")
        self.period = period
        self.d_period = d_period

    @property
    def metadata(self) -> IndicatorMetadata:
        return IndicatorMetadata(
            name=f"STOCH_{self.period}_{self.d_period}",
            description="Stochastic Oscillator",
            minimum_period=self.period,
        )

    def calculate(self, data: IndicatorInput) -> IndicatorResult:
        meta = self.metadata
        if data.size < meta.minimum_period:
            raise ValueError(f"Insufficient data for Stochastic: need {meta.minimum_period}")
        candles = data.candles[-self.period:]
        high = max(c.high for c in candles)
        low = min(c.low for c in candles)
        close = candles[-1].close
        if high == low:
            k = Decimal(0)
        else:
            k = Decimal(100) * (close - low) / (high - low)
        # %D is SMA of last d_period %K values; we compute a rolling SMA manually for simplicity
        # For this implementation we only return the current %K and %D where %D is SMA of the last d_period %K values.
        # Since we lack historical %K series, we approximate %D as the same as %K when not enough history.
        if self.d_period == 1:
            d = k
        else:
            # recompute %K for each window to get a series of length d_period
            ks = []
            for i in range(self.d_period):
                start = -(self.period + i)
                window = data.candles[start:start + self.period]
                if len(window) < self.period:
                    break
                high_w = max(c.high for c in window)
                low_w = min(c.low for c in window)
                close_w = window[-1].close
                if high_w == low_w:
                    ks.append(Decimal(0))
                else:
                    ks.append(Decimal(100) * (close_w - low_w) / (high_w - low_w))
            d = sum(ks) / Decimal(len(ks)) if ks else k
        return IndicatorResult(
            indicator_name=meta.name,
            timestamp=data.latest.timestamp,
            values={"%K": k.quantize(Decimal('0.0001')), "%D": d.quantize(Decimal('0.0001'))},
        )
