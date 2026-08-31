from decimal import Decimal
from app.indicators.base import BaseIndicator
from app.indicators.input import IndicatorInput, IndicatorCandle
from app.indicators.models import IndicatorMetadata, IndicatorResult

class OBVIndicator(BaseIndicator):
    """On-Balance Volume (OBV) indicator.
    OBV is a cumulative total of volume where each period's volume is added
    when the closing price rises and subtracted when it falls.
    """

    def __init__(self):
        # No configurable period; we operate on the entire input.
        pass

    @property
    def metadata(self) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="OBV",
            description="On-Balance Volume",
            minimum_period=2,  # need at least two candles to compute a change
        )

    def calculate(self, data: IndicatorInput) -> IndicatorResult:
        meta = self.metadata
        if data.size < meta.minimum_period:
            raise ValueError("Insufficient data for OBV: need at least 2 candles")
        candles = data.candles
        obv = Decimal(0)
        for i in range(1, len(candles)):
            cur = candles[i]
            prev = candles[i - 1]
            if cur.close > prev.close:
                obv += cur.volume
            elif cur.close < prev.close:
                obv -= cur.volume
            # if equal, obv unchanged
        return IndicatorResult(
            indicator_name=meta.name,
            timestamp=data.latest.timestamp,
            values={"obv": obv.quantize(Decimal("0.0001"))},
        )
