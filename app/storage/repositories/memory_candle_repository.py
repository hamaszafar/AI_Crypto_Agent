from datetime import datetime

from app.storage.models import StoredCandle
from app.storage.repositories.candle_repository import CandleRepository


class InMemoryCandleRepository(CandleRepository):
    """
    In-memory candle repository for testing and development.
    """

    def __init__(self) -> None:
        self._candles: list[StoredCandle] = []

    def save_candle(
        self,
        candle: StoredCandle,
    ) -> None:
        """
        Save a single candle.

        If the same candle identity already exists,
        replace the existing candle.
        """

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
        """
        Retrieve candles for a specific market.

        Results are returned in chronological order.
        """

        if limit is not None and limit < 0:
            raise ValueError("limit cannot be negative")

        candles = [
            candle
            for candle in self._candles
            if (
                candle.exchange == exchange
                and candle.symbol == symbol
                and candle.timeframe == timeframe
            )
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

        if not candles:
            return None

        return candles[-1]

    def count_candles(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
    ) -> int:
        """Count candles for a specific market."""

        return len(
            self.get_candles(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
            )
        )

    def count_all(
        self,
        exchange: str | None = None,
        symbol: str | None = None,
        timeframe: str | None = None,
    ) -> int:
        """
        Count candles with optional filters.

        No filters:
            count all candles.

        Any supplied filter:
            count only matching candles.
        """

        candles = self._candles

        if exchange is not None:
            candles = [
                candle
                for candle in candles
                if candle.exchange == exchange
            ]

        if symbol is not None:
            candles = [
                candle
                for candle in candles
                if candle.symbol == symbol
            ]

        if timeframe is not None:
            candles = [
                candle
                for candle in candles
                if candle.timeframe == timeframe
            ]

        return len(candles)

    @staticmethod
    def _same_identity(
        first: StoredCandle,
        second: StoredCandle,
    ) -> bool:
        """Check whether two candles represent the same candle."""

        return (
            first.exchange == second.exchange
            and first.symbol == second.symbol
            and first.timeframe == second.timeframe
            and first.timestamp == second.timestamp
        )


# Backward-compatible alias.
#
# Some newer code may use MemoryCandleRepository,
# while the existing test suite uses InMemoryCandleRepository.
MemoryCandleRepository = InMemoryCandleRepository