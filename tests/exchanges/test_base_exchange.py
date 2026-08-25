from datetime import datetime, timezone
from decimal import Decimal

from app.exchanges.base import BaseExchange
from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe


class MockExchange(BaseExchange):

    @property
    def name(self) -> str:
        return "mock"

    def get_symbols(self) -> list[Symbol]:
        return [Symbol.BTC_USDT]

    def get_ohlcv(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
    ) -> list[Candle]:

        return [
            Candle(
                exchange=self.name,
                symbol=symbol,
                timeframe=timeframe,
                timestamp=datetime.now(timezone.utc),
                open=Decimal("117500"),
                high=Decimal("117800"),
                low=Decimal("117400"),
                close=Decimal("117700"),
                volume=Decimal("123.456"),
            )
        ]

    def get_latest_candle(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
    ) -> Candle | None:

        candles = self.get_ohlcv(symbol, timeframe)

        return candles[-1] if candles else None

    def health_check(self) -> bool:
        return True


def test_valid_exchange_implementation():
    exchange = MockExchange()

    assert exchange.name == "mock"
    assert exchange.health_check() is True

    symbols = exchange.get_symbols()

    assert Symbol.BTC_USDT in symbols

    candles = exchange.get_ohlcv(
        Symbol.BTC_USDT,
        Timeframe.FIFTEEN_MINUTES,
    )

    assert len(candles) == 1
    assert candles[0].exchange == "mock"
    assert candles[0].symbol == Symbol.BTC_USDT
    assert candles[0].timeframe == Timeframe.FIFTEEN_MINUTES