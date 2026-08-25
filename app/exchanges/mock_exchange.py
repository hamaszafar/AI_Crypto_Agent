from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.exchanges.base import BaseExchange
from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe


class MockExchange(BaseExchange):
    """Deterministic mock exchange for development and testing."""

    @property
    def name(self) -> str:
        return "mock"

    def get_symbols(self) -> list[Symbol]:
        return list(Symbol)

    def get_ohlcv(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
    ) -> list[Candle]:

        if limit <= 0:
            return []

        if end_time is None:
            end_time = datetime.now(timezone.utc)

        interval = self._timeframe_delta(timeframe)

        candles: list[Candle] = []

        for i in range(limit):
            timestamp = end_time - interval * (limit - 1 - i)

            base_price = Decimal("100") + Decimal(i)

            candles.append(
                Candle(
                    exchange=self.name,
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=timestamp,
                    open=base_price,
                    high=base_price + Decimal("2"),
                    low=base_price - Decimal("1"),
                    close=base_price + Decimal("1"),
                    volume=Decimal("1000") + Decimal(i * 10),
                )
            )

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

        return candles

    def get_latest_candle(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
    ) -> Candle | None:

        candles = self.get_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            limit=1,
        )

        return candles[-1] if candles else None

    def health_check(self) -> bool:
        return True

    @staticmethod
    def _timeframe_delta(timeframe: Timeframe) -> timedelta:
        mapping = {
            Timeframe.FIFTEEN_MINUTES: timedelta(minutes=15),
            Timeframe.ONE_HOUR: timedelta(hours=1),
            Timeframe.FOUR_HOURS: timedelta(hours=4),
            Timeframe.ONE_DAY: timedelta(days=1),
        }

        return mapping[timeframe]