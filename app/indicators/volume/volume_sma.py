from decimal import Decimal
from app.indicators.base import BaseIndicator
from app.indicators.input import IndicatorInput, IndicatorCandle
from app.indicators.models import IndicatorMetadata, IndicatorResult

class VolumeSMAIndicator(BaseIndicator):
    """Simple Moving Average of volume over a period."""

    def __init__(self, period: int = 14):
        if period < 1:
            raise ValueError("Period must be >= 1")
        self.period = period

    @property
    def metadata(self) -> IndicatorMetadata:
        return IndicatorMetadata(
            name=f"VOL_SMA_{self.period}",
            description="Volume Simple Moving Average",
            minimum_period=self.period,
        )

    def calculate(self, data: IndicatorInput) -> IndicatorResult:
        meta = self.metadata
        if data.size < meta.minimum_period:
            raise ValueError(f"Insufficient data for Volume SMA: need {meta.minimum_period}")
        candles = data.candles[-self.period:]
        total = sum(c.volume for c in candles)
        sma = total / Decimal(self.period)
        return IndicatorResult(
            indicator_name=meta.name,
            timestamp=data.latest.timestamp,
            values={"vol_sma": sma.quantize(Decimal("0.0001"))},
        )
