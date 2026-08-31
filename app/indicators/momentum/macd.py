from decimal import Decimal
from app.indicators.base import BaseIndicator
from app.indicators.input import IndicatorInput, IndicatorCandle
from app.indicators.models import IndicatorMetadata, IndicatorResult

class MACDIndicator(BaseIndicator):
    """Momentum MACD – thin wrapper around the trend MACD implementation.
    It re‑uses the calculation logic from ``app.indicators.trend.macd`` to avoid
    duplication. The class exists so that users can request a ``macd`` indicator
    from the ``momentum`` namespace.
    """

    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.min_period = slow_period + signal_period

    @property
    def metadata(self) -> IndicatorMetadata:
        return IndicatorMetadata(
            name=f"MACD_{self.fast_period}_{self.slow_period}_{self.signal_period}",
            description="Moving Average Convergence Divergence (momentum)",
            minimum_period=self.min_period,
        )

    def calculate(self, data: IndicatorInput) -> IndicatorResult:
        # Import locally to avoid circular import at module load time.
        from app.indicators.trend.macd import MACDIndicator as TrendMACD
        trend_macd = TrendMACD(self.fast_period, self.slow_period, self.signal_period)
        return trend_macd.calculate(data)
