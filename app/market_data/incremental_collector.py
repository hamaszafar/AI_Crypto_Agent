from datetime import datetime, timedelta

from app.exchanges.base import BaseExchange
from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe
from app.market_data.historical import HistoricalMarketData
from app.storage.models import StoredCandle


class IncrementalCollector:
    """
    Collect only candles that are newer than the latest
    candle already stored for a symbol/timeframe/exchange.
    """

    def __init__(
        self,
        exchange: BaseExchange,
        historical_data: HistoricalMarketData,
        page_size: int = 1000,
    ) -> None:
        if page_size < 1:
            raise ValueError(
                "page_size must be greater than zero"
            )

        if page_size > 1000:
            raise ValueError(
                "page_size cannot exceed 1000"
            )

        self.exchange = exchange
        self.historical_data = historical_data
        self.page_size = page_size

    def collect(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        end_time: datetime | None = None,
    ) -> list[StoredCandle]:
        """
        Collect candles newer than the latest stored candle.

        If no historical candle exists, nothing is downloaded.
        Initial historical population is handled by
        HistoricalDownloader.
        """

        latest = self.historical_data.get_latest(
            exchange=self.exchange.name,
            symbol=symbol.value,
            timeframe=timeframe.value,
        )

        if latest is None:
            return []

        start_time = latest.timestamp + timedelta(
            milliseconds=1
        )

        if end_time is not None and start_time > end_time:
            return []

        candles = self.exchange.get_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            limit=self.page_size,
        )

        new_candles = self._filter_new_candles(
            candles=candles,
            latest_timestamp=latest.timestamp,
            end_time=end_time,
        )

        stored_candles = [
            StoredCandle.from_candle(candle)
            for candle in new_candles
        ]

        if stored_candles:
            self.historical_data.save_candles(
                stored_candles
            )

        return stored_candles

    @staticmethod
    def _filter_new_candles(
        candles: list[Candle],
        latest_timestamp: datetime,
        end_time: datetime | None,
    ) -> list[Candle]:
        """
        Remove candles that are already stored or outside
        the requested end boundary.
        """

        seen: set[datetime] = set()
        result: list[Candle] = []

        for candle in candles:
            if candle.timestamp <= latest_timestamp:
                continue

            if end_time is not None:
                if candle.timestamp > end_time:
                    continue

            if candle.timestamp in seen:
                continue

            seen.add(candle.timestamp)
            result.append(candle)

        result.sort(
            key=lambda candle: candle.timestamp
        )

        return result