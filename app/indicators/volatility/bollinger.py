from decimal import Decimal, getcontext
from statistics import stdev
from app.indicators.base import BaseIndicator
from app.indicators.input import IndicatorInput, IndicatorCandle
from app.indicators.models import IndicatorMetadata, IndicatorResult

class BollingerBandsIndicator(BaseIndicator):
    """Bollinger Bands indicator.
    Calculates the simple moving average (SMA) and upper/lower bands as:
        upper = SMA + (width * std_dev)
        lower = SMA - (width * std_dev)
    """

    def __init__(self, period: int = 20, width: Decimal = Decimal("2")):
        if period < 1:
            raise ValueError("Period must be >= 1")
        self.period = period
        self.width = width

    @property
    def metadata(self) -> IndicatorMetadata:
        return IndicatorMetadata(
            name=f"BOLLINGER_{self.period}_{self.width}",
            description="Bollinger Bands",
            minimum_period=self.period,
        )

    def calculate(self, data: IndicatorInput) -> IndicatorResult:
        meta = self.metadata
        if data.size < meta.minimum_period:
            raise ValueError(f"Insufficient data for Bollinger Bands: need {meta.minimum_period}")
        candles = data.candles[-self.period:]
        closes = [c.close for c in candles]
        # Compute SMA
        sma = sum(closes) / Decimal(self.period)
        # Compute standard deviation using Decimal conversion for precision
        # Convert Decimal to float for stdev then back; acceptable for small error.
        std = Decimal(stdev([float(v) for v in closes]))
        upper = sma + self.width * std
        lower = sma - self.width * std
        return IndicatorResult(
            indicator_name=meta.name,
            timestamp=data.latest.timestamp,
            values={
                "sma": sma.quantize(Decimal("0.0001")),
                "upper": upper.quantize(Decimal("0.0001")),
                "lower": lower.quantize(Decimal("0.0001")),
                "std": std.quantize(Decimal("0.0001")),
            },
        )
