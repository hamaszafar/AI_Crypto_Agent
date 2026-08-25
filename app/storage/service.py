from datetime import datetime

from app.exchanges.models import Candle
from app.storage.models import StoredCandle
from app.storage.repositories.candle_repository import CandleRepository


class StorageService:
    """
    Application service responsible for market candle storage.

    The service converts domain Candle objects into
    StoredCandle objects and delegates persistence to
    the repository.
    """

    def __init__(
        self,
        repository: CandleRepository,
    ) -> None:
        self._repository = repository

    def save_candle(
        self,
        candle: Candle,
    ) -> StoredCandle:
        """
        Convert and store a single market candle.
        """
        stored_candle = StoredCandle.from_candle(candle)

        self._repository.save_candle(stored_candle)

        return stored_candle

    def save_candles(
        self,
        candles: list[Candle],
    ) -> list[StoredCandle]:
        """
        Convert and store multiple market candles.
        """
        stored_candles = [
            StoredCandle.from_candle(candle)
            for candle in candles
        ]

        self._repository.save_candles(stored_candles)

        return stored_candles

    def get_candles(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> list[StoredCandle]:
        """Retrieve candles from the repository."""

        return self._repository.get_candles(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    def get_latest_candle(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
    ) -> StoredCandle | None:
        """Retrieve the latest candle."""

        return self._repository.get_latest_candle(
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
        """
        Count stored candles.

        All filters are optional.

        Examples:
            service.count()

            service.count(
                exchange="binance"
            )

            service.count(
                symbol="BTC/USDT"
            )

            service.count(
                timeframe="15m"
            )

            service.count(
                exchange="binance",
                symbol="BTC/USDT",
                timeframe="15m",
            )
        """

        return self._repository.count_all(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
        )

    def count_all(self) -> int:
        """
        Return the total number of stored candles.

        This is used when no market filters are supplied.
        """

        return self._repository.count_all()