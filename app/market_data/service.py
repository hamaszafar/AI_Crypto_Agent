from __future__ import annotations

from datetime import datetime

from app.exchanges.types import Symbol, Timeframe
from app.market_data.collector import MarketDataCollector
from app.market_data.models import MarketCandle
from app.market_data.validator import validate_market_data


class MarketDataService:
    """
    Application service responsible for retrieving and validating
    market data from an exchange.

    The service does not implement validation rules itself.
    It delegates validation to the market-data validation pipeline.
    """

    def __init__(self, collector: MarketDataCollector) -> None:
        self._collector = collector

    @classmethod
    def from_exchange(cls, exchange_name: str) -> "MarketDataService":
        """Create a market-data service for an exchange."""

        collector = MarketDataCollector.from_exchange(exchange_name)

        return cls(collector)

    @property
    def exchange_name(self) -> str:
        """Return the active exchange name."""

        return self._collector.exchange_name

    def health_check(self) -> bool:
        """Return whether the underlying exchange is healthy."""

        return self._collector.health_check()

    def get_symbols(self) -> list[Symbol]:
        """Return symbols supported by the exchange."""

        return self._collector.get_symbols()

    def get_candles(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
    ) -> list[MarketCandle]:
        """
        Retrieve and validate market candles.

        The returned candles have passed the complete
        market-data validation pipeline.
        """

        candles = self._collector.get_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

        return validate_market_data(candles)

    def get_latest_candle(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
    ) -> MarketCandle | None:
        """
        Retrieve the latest candle and validate it.
        """

        candle = self._collector.get_latest_candle(
            symbol=symbol,
            timeframe=timeframe,
        )

        if candle is None:
            return None

        validate_market_data([candle])

        return candle