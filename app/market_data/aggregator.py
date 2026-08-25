from __future__ import annotations

from datetime import datetime

from app.exchanges.types import Symbol, Timeframe
from app.market_data.models import MarketCandle
from app.market_data.service import MarketDataService


class MarketDataAggregator:
    """
    Aggregate validated market data from multiple exchanges.

    Each exchange is represented by its own MarketDataService.
    """

    def __init__(
        self,
        services: dict[str, MarketDataService],
    ) -> None:
        if not services:
            raise ValueError(
                "At least one market data service is required."
            )

        self._services = dict(services)

    @classmethod
    def from_exchanges(
        cls,
        exchange_names: list[str],
    ) -> "MarketDataAggregator":
        """Create an aggregator from exchange names."""

        if not exchange_names:
            raise ValueError(
                "At least one exchange is required."
            )

        services: dict[str, MarketDataService] = {}

        for exchange_name in exchange_names:
            service = MarketDataService.from_exchange(
                exchange_name
            )

            services[service.exchange_name] = service

        return cls(services)

    @property
    def exchange_names(self) -> list[str]:
        """Return configured exchange names."""

        return list(self._services.keys())

    def health_check(self) -> dict[str, bool]:
        """Check the health of every configured exchange."""

        result: dict[str, bool] = {}

        for name, service in self._services.items():
            try:
                result[name] = service.health_check()
            except Exception:
                result[name] = False

        return result

    def get_candles(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
    ) -> dict[str, list[MarketCandle]]:
        """
        Retrieve validated candles from every configured exchange.
        """

        result: dict[str, list[MarketCandle]] = {}

        for name, service in self._services.items():
            candles = service.get_candles(
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )

            result[name] = candles

        return result

    def get_latest_candles(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
    ) -> dict[str, MarketCandle | None]:
        """Retrieve the latest candle from every exchange."""

        result: dict[str, MarketCandle | None] = {}

        for name, service in self._services.items():
            result[name] = service.get_latest_candle(
                symbol=symbol,
                timeframe=timeframe,
            )

        return result
