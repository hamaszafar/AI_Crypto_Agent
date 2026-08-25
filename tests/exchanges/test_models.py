from datetime import datetime, timezone
from decimal import Decimal

from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe


def test_candle_creation():
    candle = Candle(
        exchange="binance",
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        timestamp=datetime.now(timezone.utc),
        open=Decimal("117500.00"),
        high=Decimal("117800.00"),
        low=Decimal("117400.00"),
        close=Decimal("117700.00"),
        volume=Decimal("123.456"),
    )

    assert candle.exchange == "binance"
    assert candle.symbol == Symbol.BTC_USDT
    assert candle.timeframe == Timeframe.FIFTEEN_MINUTES
    assert candle.close == Decimal("117700.00")