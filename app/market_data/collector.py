from datetime import datetime

from app.exchanges.base import BaseExchange
from app.exchanges.factory import ExchangeFactory
from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe


class MarketDataCollector:
    """
    Unified market-data collector.

    The collector works with BaseExchange and does not
    depend on any specific exchange implementation.
    """

    def __init__(self, exchange: BaseExchange) -> None:
        self.exchange = exchange

    @classmethod
    def from_exchange(cls, exchange_name: str) -> "MarketDataCollector":
        exchange = ExchangeFactory.create(exchange_name)
        return cls(exchange)

    def get_symbols(self) -> list[Symbol]:
        return self.exchange.get_symbols()

    def get_ohlcv(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
    ) -> list[Candle]:
        return self.exchange.get_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    def get_latest_candle(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
    ) -> Candle | None:
        return self.exchange.get_latest_candle(
            symbol=symbol,
            timeframe=timeframe,
        )

    def health_check(self) -> bool:
        return self.exchange.health_check()

    @property
    def exchange_name(self) -> str:
        return self.exchange.name