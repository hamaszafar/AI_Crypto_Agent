from datetime import datetime

from app.storage.models import StoredCandle
from app.storage.repositories.candle_repository import CandleRepository


class HistoricalMarketData:
    """
    Service for storing and retrieving historical market candles.

    Uses CandleRepository as the persistence abstraction so the
    underlying storage implementation can be swapped without
    changing historical-data logic.
    """

    def __init__(self, repository: CandleRepository) -> None:
        self.repository = repository

    def save_candle(self, candle: StoredCandle) -> None:
        """Store a single historical candle."""
        self.repository.save_candle(candle)

    def save_candles(self, candles: list[StoredCandle]) -> None:
        """Store multiple historical candles."""
        if not candles:
            return

        self.repository.save_candles(candles)

    def get_history(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> list[StoredCandle]:
        """
        Retrieve historical candles in chronological order.
        """

        if start_time is not None and end_time is not None:
            if start_time > end_time:
                raise ValueError(
                    "start_time cannot be greater than end_time"
                )

        if limit is not None and limit < 0:
            raise ValueError("limit cannot be negative")

        return self.repository.get_candles(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    def get_latest(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
    ) -> StoredCandle | None:
        """Return the latest historical candle."""

        return self.repository.get_latest_candle(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
        )

    def count(
        self,
        exchange: str | None = None,
        symbol: str | None = None,
        timeframe: str | None = None,
    ) -> int:
        """Count historical candles using optional filters."""

        return self.repository.count_all(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
        )