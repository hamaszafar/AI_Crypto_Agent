from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe
from app.market_data.incremental_collector import (
    IncrementalCollector,
)
from app.storage.models import StoredCandle


class FakeExchange:
    def __init__(self, candles=None):
        self.candles = candles or []
        self.calls = []

    @property
    def name(self):
        return "binance"

    def get_ohlcv(
        self,
        symbol,
        timeframe,
        start_time=None,
        end_time=None,
        limit=500,
    ):
        self.calls.append(
            {
                "symbol": symbol,
                "timeframe": timeframe,
                "start_time": start_time,
                "end_time": end_time,
                "limit": limit,
            }
        )

        return self.candles


class FakeHistoricalMarketData:
    def __init__(self, latest=None):
        self.latest = latest
        self.saved = []

    def get_latest(
        self,
        exchange,
        symbol,
        timeframe,
    ):
        return self.latest

    def save_candles(self, candles):
        self.saved.extend(candles)


def make_candle(timestamp):
    return Candle(
        exchange="binance",
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        timestamp=timestamp,
        open=Decimal("114000"),
        high=Decimal("115000"),
        low=Decimal("113500"),
        close=Decimal("114500"),
        volume=Decimal("100"),
    )


def make_stored(timestamp):
    return StoredCandle.from_candle(
        make_candle(timestamp)
    )


def test_invalid_page_size():
    exchange = FakeExchange()
    historical = FakeHistoricalMarketData()

    with pytest.raises(ValueError):
        IncrementalCollector(
            exchange,
            historical,
            page_size=0,
        )

    with pytest.raises(ValueError):
        IncrementalCollector(
            exchange,
            historical,
            page_size=1001,
        )


def test_no_latest_candle_returns_empty():
    exchange = FakeExchange()
    historical = FakeHistoricalMarketData(
        latest=None
    )

    collector = IncrementalCollector(
        exchange,
        historical,
    )

    result = collector.collect(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert result == []
    assert exchange.calls == []
    assert historical.saved == []


def test_collects_only_new_candles():
    latest_time = datetime(
        2026,
        8,
        24,
        10,
        0,
        tzinfo=timezone.utc,
    )

    new_time = datetime(
        2026,
        8,
        24,
        10,
        15,
        tzinfo=timezone.utc,
    )

    exchange = FakeExchange(
        [
            make_candle(new_time)
        ]
    )

    historical = FakeHistoricalMarketData(
        latest=make_stored(latest_time)
    )

    collector = IncrementalCollector(
        exchange,
        historical,
        page_size=100,
    )

    result = collector.collect(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert len(result) == 1
    assert result[0].timestamp == new_time

    assert len(historical.saved) == 1


def test_starts_after_latest_timestamp():
    latest_time = datetime(
        2026,
        8,
        24,
        10,
        0,
        tzinfo=timezone.utc,
    )

    exchange = FakeExchange([])

    historical = FakeHistoricalMarketData(
        latest=make_stored(latest_time)
    )

    collector = IncrementalCollector(
        exchange,
        historical,
    )

    collector.collect(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert len(exchange.calls) == 1

    assert exchange.calls[0]["start_time"] == (
        latest_time.replace(
            microsecond=1000
        )
    )


def test_duplicate_candles_are_removed():
    latest_time = datetime(
        2026,
        8,
        24,
        10,
        0,
        tzinfo=timezone.utc,
    )

    new_time = datetime(
        2026,
        8,
        24,
        10,
        15,
        tzinfo=timezone.utc,
    )

    exchange = FakeExchange(
        [
            make_candle(new_time),
            make_candle(new_time),
        ]
    )

    historical = FakeHistoricalMarketData(
        latest=make_stored(latest_time)
    )

    collector = IncrementalCollector(
        exchange,
        historical,
    )

    result = collector.collect(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert len(result) == 1
    assert len(historical.saved) == 1


def test_old_candles_are_ignored():
    latest_time = datetime(
        2026,
        8,
        24,
        10,
        0,
        tzinfo=timezone.utc,
    )

    old_time = datetime(
        2026,
        8,
        24,
        9,
        45,
        tzinfo=timezone.utc,
    )

    exchange = FakeExchange(
        [
            make_candle(old_time)
        ]
    )

    historical = FakeHistoricalMarketData(
        latest=make_stored(latest_time)
    )

    collector = IncrementalCollector(
        exchange,
        historical,
    )

    result = collector.collect(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert result == []
    assert historical.saved == []


def test_end_time_is_respected():
    latest_time = datetime(
        2026,
        8,
        24,
        10,
        0,
        tzinfo=timezone.utc,
    )

    first_new = datetime(
        2026,
        8,
        24,
        10,
        15,
        tzinfo=timezone.utc,
    )

    second_new = datetime(
        2026,
        8,
        24,
        10,
        30,
        tzinfo=timezone.utc,
    )

    end_time = datetime(
        2026,
        8,
        24,
        10,
        20,
        tzinfo=timezone.utc,
    )

    exchange = FakeExchange(
        [
            make_candle(first_new),
            make_candle(second_new),
        ]
    )

    historical = FakeHistoricalMarketData(
        latest=make_stored(latest_time)
    )

    collector = IncrementalCollector(
        exchange,
        historical,
    )

    result = collector.collect(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        end_time=end_time,
    )

    assert len(result) == 1
    assert result[0].timestamp == first_new


def test_end_time_before_next_candle_returns_empty():
    latest_time = datetime(
        2026,
        8,
        24,
        10,
        0,
        tzinfo=timezone.utc,
    )

    end_time = datetime(
        2026,
        8,
        24,
        9,
        59,
        tzinfo=timezone.utc,
    )

    exchange = FakeExchange()

    historical = FakeHistoricalMarketData(
        latest=make_stored(latest_time)
    )

    collector = IncrementalCollector(
        exchange,
        historical,
    )

    result = collector.collect(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        end_time=end_time,
    )

    assert result == []
    assert exchange.calls == []


def test_results_are_sorted():
    latest_time = datetime(
        2026,
        8,
        24,
        10,
        0,
        tzinfo=timezone.utc,
    )

    first = datetime(
        2026,
        8,
        24,
        10,
        15,
        tzinfo=timezone.utc,
    )

    second = datetime(
        2026,
        8,
        24,
        10,
        30,
        tzinfo=timezone.utc,
    )

    exchange = FakeExchange(
        [
            make_candle(second),
            make_candle(first),
        ]
    )

    historical = FakeHistoricalMarketData(
        latest=make_stored(latest_time)
    )

    collector = IncrementalCollector(
        exchange,
        historical,
    )

    result = collector.collect(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert [
        candle.timestamp
        for candle in result
    ] == [first, second]


def test_exchange_parameters():
    latest_time = datetime(
        2026,
        8,
        24,
        10,
        0,
        tzinfo=timezone.utc,
    )

    exchange = FakeExchange([])

    historical = FakeHistoricalMarketData(
        latest=make_stored(latest_time)
    )

    collector = IncrementalCollector(
        exchange,
        historical,
        page_size=250,
    )

    collector.collect(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.ONE_HOUR,
    )

    call = exchange.calls[0]

    assert call["symbol"] == Symbol.BTC_USDT
    assert call["timeframe"] == Timeframe.ONE_HOUR
    assert call["limit"] == 250