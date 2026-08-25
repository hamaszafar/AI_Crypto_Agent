from datetime import datetime

from app.indicators.input import IndicatorCandle, IndicatorInput
from app.market_data.historical import HistoricalMarketData


class IndicatorInputPipeline:
    """
    Builds clean indicator input from historical market data.

    This class does not calculate indicators. Its responsibility is
    to retrieve historical candles and convert them into the
    indicator-specific representation.
    """

    def __init__(
        self,
        historical_data: HistoricalMarketData,
    ) -> None:
        self.historical_data = historical_data

    def build(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> IndicatorInput:
        """
        Build indicator input for a market/timeframe.
        """

        candles = self.historical_data.get_history(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

        indicator_candles = tuple(
            IndicatorCandle(
                timestamp=candle.timestamp,
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                volume=candle.volume,
            )
            for candle in candles
        )

        return IndicatorInput(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            candles=indicator_candles,
        )

    def has_enough_data(
        self,
        indicator_input: IndicatorInput,
        minimum_candles: int,
    ) -> bool:
        """
        Check whether enough candles exist for an indicator.

        Example:
            RSI(14) requires at least 14 periods of input.
        """

        if minimum_candles < 1:
            raise ValueError(
                "minimum_candles must be greater than zero"
            )

        return indicator_input.size >= minimum_candles