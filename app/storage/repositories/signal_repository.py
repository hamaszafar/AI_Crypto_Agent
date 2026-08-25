from datetime import datetime

from app.storage.models import StoredCandle
from app.storage.repositories.candle_repository import CandleRepository


class MemoryCandleRepository(CandleRepository):
    """In-memory candle repository for testing and development."""

    def __init__(self) -> None:
        self._candles: list[StoredCandle] = []

    def save_candle(
        self,
        candle: StoredCandle,
    ) -> None:
        """Save one candle."""

        self._candles = [
            existing
            for existing in self._candles
            if not self._same_identity(existing, candle)
        ]

        self._candles.append(candle)

    def save_candles(
        self,
        candles: list[StoredCandle],
    ) -> None:
        """Save multiple candles."""

        for candle in candles:
            self.save_candle(candle)

    def get_candles(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> list[StoredCandle]:
        """Retrieve candles matching the requested filters."""

        if limit is not None and limit < 0:
            raise ValueError("limit cannot be negative")

        candles = [
            candle
            for candle in self._candles
            if candle.exchange == exchange
            and candle.symbol == symbol
            and candle.timeframe == timeframe
        ]

        if start_time is not None:
            candles = [
                candle
                for candle in candles
                if candle.timestamp >= start_time
            ]

        if end_time is not None:
            candles = [
                candle
                for candle in candles
                if candle.timestamp <= end_time
            ]

        candles.sort(
            key=lambda candle: candle.timestamp
        )

        if limit is not None:
            candles = candles[:limit]

        return candles

    def get_latest_candle(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
    ) -> StoredCandle | None:
        """Return the latest candle."""

        candles = self.get_candles(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
        )

        return candles[-1] if candles else None

    def count_candles(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
    ) -> int:
        """Count candles for a specific market/timeframe."""

        return len(
            self.get_candles(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
            )
        )

    def count_all(self) -> int:
        """Return the total number of stored candles."""

        return len(self._candles)

    @staticmethod
    def _same_identity(
        first: StoredCandle,
        second: StoredCandle,
    ) -> bool:
        """Check whether two candles have the same storage identity."""

        return (
            first.exchange == second.exchange
            and first.symbol == second.symbol
            and first.timeframe == second.timeframe
            and first.timestamp == second.timestamp
        )