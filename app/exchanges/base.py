from abc import ABC, abstractmethod
from datetime import datetime

from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe


class BaseExchange(ABC):
    """Abstract interface that every exchange implementation must follow."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the exchange identifier."""
        raise NotImplementedError

    @abstractmethod
    def get_symbols(self) -> list[Symbol]:
        """Return symbols supported by this exchange."""
        raise NotImplementedError

    @abstractmethod
    def get_ohlcv(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
    ) -> list[Candle]:
        """Return OHLCV candles for a symbol and timeframe."""
        raise NotImplementedError

    @abstractmethod
    def get_latest_candle(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
    ) -> Candle | None:
        """Return the latest available candle."""
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> bool:
        """Return True when the exchange is healthy/reachable."""
        raise NotImplementedError
