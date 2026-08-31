from decimal import Decimal, getcontext
from math import sqrt
from app.indicators.base import BaseIndicator
from app.indicators.input import IndicatorInput, IndicatorCandle
from app.indicators.models import IndicatorMetadata, IndicatorResult

class ATRIndicator(BaseIndicator):
    """Average True Range (ATR) indicator.
    Computes the average of true ranges over a given period.
    """

    def __init__(self, period: int = 14):
        if period < 1:
            raise ValueError("Period must be >= 1")
        self.period = period

    @property
    def metadata(self) -> IndicatorMetadata:
        return IndicatorMetadata(
            name=f"ATR_{self.period}",
            description="Average True Range",
            minimum_period=self.period + 1,  # need previous close for first TR
        )

    def _true_range(self, cur: IndicatorCandle, prev: IndicatorCandle) -> Decimal:
        high_low = cur.high - cur.low
        high_prev_close = abs(cur.high - prev.close)
        low_prev_close = abs(cur.low - prev.close)
        return max(high_low, high_prev_close, low_prev_close)

    def calculate(self, data: IndicatorInput) -> IndicatorResult:
        meta = self.metadata
        if data.size < meta.minimum_period:
            raise ValueError(f"Insufficient data for ATR: need {meta.minimum_period}")
        candles = data.candles[-(self.period + 1):]
        tr_sum = Decimal(0)
        for i in range(1, len(candles)):
            tr_sum += self._true_range(candles[i], candles[i - 1])
        atr = tr_sum / Decimal(self.period)
        return IndicatorResult(
            indicator_name=meta.name,
            timestamp=data.latest.timestamp,
            values={"atr": atr.quantize(Decimal("0.0001"))},
        )
