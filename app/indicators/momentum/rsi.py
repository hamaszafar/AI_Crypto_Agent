from decimal import Decimal
from app.indicators.base import BaseIndicator
from app.indicators.input import IndicatorInput, IndicatorCandle
from app.indicators.models import IndicatorMetadata, IndicatorResult

class RSIIndicator(BaseIndicator):
    """Relative Strength Index (RSI) implementation.
    Uses the standard 100 - (100 / (1 + RS)) formula where RS is average gain / average loss.
    """

    def __init__(self, period: int = 14):
        if period < 1:
            raise ValueError("Period must be >= 1")
        self.period = period

    @property
    def metadata(self) -> IndicatorMetadata:
        return IndicatorMetadata(
            name=f"RSI_{self.period}",
            description="Relative Strength Index",
            minimum_period=self.period + 1,  # need one extra candle for change
        )

    def calculate(self, data: IndicatorInput) -> IndicatorResult:
        meta = self.metadata
        if data.size < meta.minimum_period:
            raise ValueError(f"Insufficient data for RSI: need {meta.minimum_period}")
        candles = data.candles[-(self.period + 1):]
        gains = Decimal(0)
        losses = Decimal(0)
        for i in range(1, len(candles)):
            change = candles[i].close - candles[i - 1].close
            if change > 0:
                gains += change
            else:
                losses -= change  # change is negative
        if losses == 0:
            rsi = Decimal(100)
        else:
            rs = gains / losses
            rsi = Decimal(100) - (Decimal(100) / (Decimal(1) + rs))
        return IndicatorResult(
            indicator_name=meta.name,
            timestamp=data.latest.timestamp,
            values={"rsi": rsi.quantize(Decimal("0.0001"))},
        )
