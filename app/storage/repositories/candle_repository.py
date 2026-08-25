from abc import ABC, abstractmethod
from datetime import datetime

from app.storage.models import StoredCandle


class CandleRepository(ABC):
    """
    Abstract repository for market candle storage.

    Defines the contract that every candle repository
    implementation must follow.
    """

    @abstractmethod
    def save_candle(
        self,
        candle: StoredCandle,
    ) -> None:
        """Persist a single candle."""
        raise NotImplementedError

    @abstractmethod
    def save_candles(
        self,
        candles: list[StoredCandle],
    ) -> None:
        """Persist multiple candles."""
        raise NotImplementedError

    @abstractmethod
    def get_candles(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> list[StoredCandle]:
        """
        Retrieve candles for a specific exchange,
        symbol, and timeframe.
        """
        raise NotImplementedError

    @abstractmethod
    def get_latest_candle(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
    ) -> StoredCandle | None:
        """Retrieve the latest candle."""
        raise NotImplementedError

    @abstractmethod
    def count_candles(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
    ) -> int:
        """
        Count candles for a specific exchange,
        symbol, and timeframe.
        """
        raise NotImplementedError

    @abstractmethod
    def count_all(
        self,
        exchange: str | None = None,
        symbol: str | None = None,
        timeframe: str | None = None,
    ) -> int:
        """
        Count candles with optional filters.

        If no filters are supplied, return the total
        number of stored candles.
        """
        raise NotImplementedError