from datetime import datetime

from app.exchanges.models import Candle
from app.storage.models import StoredCandle
from app.storage.service import StorageService


class MarketDataStorage:
    """
    Application-level storage interface for market data.

    Keeps market-data consumers independent from the
    underlying repository implementation.
    """

    def __init__(self, storage_service: StorageService) -> None:
        self.storage_service = storage_service

    def save_candle(self, candle: Candle) -> StoredCandle:
        """Store a single market candle."""

        return self.storage_service.save_candle(candle)

    def save_candles(
        self,
        candles: list[Candle],
    ) -> list[StoredCandle]:
        """Store multiple market candles."""

        return self.storage_service.save_candles(candles)

    def get_candles(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> list[StoredCandle]:
        """Retrieve stored market candles."""

        return self.storage_service.get_candles(
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
        """Retrieve the latest stored candle."""

        return self.storage_service.get_latest_candle(
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

        When all market identifiers are provided, return the
        count for that market.

        When no identifiers are provided, return the total count.
        """

        if (
            exchange is None
            and symbol is None
            and timeframe is None
        ):
            return self.storage_service.count_all()

        if (
            exchange is None
            or symbol is None
            or timeframe is None
        ):
            raise ValueError(
                "exchange, symbol and timeframe must "
                "all be provided together"
            )

        return self.storage_service.count(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
        )