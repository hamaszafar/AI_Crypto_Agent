from datetime import datetime, timezone

from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe
from app.market_data.collector import MarketDataCollector


def test_collector_with_mock_exchange():
    collector = MarketDataCollector.from_exchange("mock")

    assert collector.exchange_name == "mock"
    assert collector.health_check() is True


def test_collector_get_symbols():
    collector = MarketDataCollector.from_exchange("mock")

    symbols = collector.get_symbols()

    assert symbols == list(Symbol)


def test_collector_get_ohlcv():
    collector = MarketDataCollector.from_exchange("mock")

    candles = collector.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        limit=10,
    )

    assert len(candles) == 10

    for candle in candles:
        assert isinstance(candle, Candle)
        assert candle.exchange == "mock"
        assert candle.symbol == Symbol.BTC_USDT
        assert candle.timeframe == Timeframe.FIFTEEN_MINUTES


def test_collector_get_latest_candle():
    collector = MarketDataCollector.from_exchange("mock")

    candle = collector.get_latest_candle(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.ONE_HOUR,
    )

    assert candle is not None
    assert candle.exchange == "mock"
    assert candle.symbol == Symbol.BTC_USDT
    assert candle.timeframe == Timeframe.ONE_HOUR


def test_collector_with_binance():
    collector = MarketDataCollector.from_exchange("binance")

    assert collector.exchange_name == "binance"


def test_collector_accepts_existing_exchange():
    from app.exchanges.mock_exchange import MockExchange

    exchange = MockExchange()
    collector = MarketDataCollector(exchange)

    assert collector.exchange_name == "mock"


def test_collector_passes_time_range():
    collector = MarketDataCollector.from_exchange("mock")

    start_time = datetime(
        2026,
        8,
        22,
        0,
        0,
        tzinfo=timezone.utc,
    )

    end_time = datetime(
        2026,
        8,
        22,
        2,
        0,
        tzinfo=timezone.utc,
    )

    candles = collector.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        start_time=start_time,
        end_time=end_time,
        limit=500,
    )

    assert isinstance(candles, list)