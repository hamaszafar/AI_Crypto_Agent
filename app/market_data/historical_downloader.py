from datetime import datetime, timedelta

from app.exchanges.base import BaseExchange
from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe
from app.storage.models import StoredCandle
from app.market_data.historical import HistoricalMarketData


class HistoricalDownloader:
    """
    Downloads large historical market-data ranges from an exchange
    and persists them through HistoricalMarketData.

    The downloader is exchange-agnostic and works with any
    BaseExchange implementation.
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

    def download(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        start_time: datetime,
        end_time: datetime,
    ) -> list[StoredCandle]:
        """
        Download and store all candles within the requested range.

        The exchange API may limit the number of candles returned
        by a single request. This method automatically paginates
        until the requested range has been collected.

        Returns the StoredCandle objects that were downloaded.
        """

        self._validate_range(
            start_time=start_time,
            end_time=end_time,
        )

        all_candles: list[Candle] = []
        seen_timestamps: set[datetime] = set()

        current_start = start_time

        while current_start <= end_time:
            batch = self.exchange.get_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                start_time=current_start,
                end_time=end_time,
                limit=self.page_size,
            )

            if not batch:
                break

            new_candles = 0

            for candle in batch:
                if candle.timestamp < start_time:
                    continue

                if candle.timestamp > end_time:
                    continue

                if candle.timestamp in seen_timestamps:
                    continue

                seen_timestamps.add(candle.timestamp)
                all_candles.append(candle)
                new_candles += 1

            last_timestamp = max(
                candle.timestamp
                for candle in batch
            )

            if last_timestamp < current_start:
                break

            if len(batch) < self.page_size:
                break

            next_start = (
                last_timestamp
                + timedelta(milliseconds=1)
            )

            if next_start <= current_start:
                break

            current_start = next_start

            if new_candles == 0:
                break

        all_candles.sort(
            key=lambda candle: candle.timestamp
        )

        stored_candles = [
            StoredCandle.from_candle(candle)
            for candle in all_candles
        ]

        if stored_candles:
            self.historical_data.save_candles(
                stored_candles
            )

        return stored_candles

    @staticmethod
    def _validate_range(
        start_time: datetime,
        end_time: datetime,
    ) -> None:
        if start_time > end_time:
            raise ValueError(
                "start_time cannot be later than end_time"
            )