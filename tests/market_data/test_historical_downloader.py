from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe
from app.market_data.historical_downloader import (
    HistoricalDownloader,
)


class FakeExchange:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

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

        if not self.responses:
            return []

        return self.responses.pop(0)


class FakeHistoricalMarketData:
    def __init__(self):
        self.saved_candles = []

    def save_candles(self, candles):
        self.saved_candles.extend(candles)


def make_candle(
    timestamp: datetime,
    close: str = "114500.00",
) -> Candle:
    return Candle(
        exchange="binance",
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        timestamp=timestamp,
        open=Decimal("114000.00"),
        high=Decimal("115000.00"),
        low=Decimal("113500.00"),
        close=Decimal(close),
        volume=Decimal("123.45"),
    )


def test_invalid_page_size_zero():
    exchange = FakeExchange([])
    historical = FakeHistoricalMarketData()

    with pytest.raises(ValueError):
        HistoricalDownloader(
            exchange,
            historical,
            page_size=0,
        )


def test_invalid_page_size_above_exchange_limit():
    exchange = FakeExchange([])
    historical = FakeHistoricalMarketData()

    with pytest.raises(ValueError):
        HistoricalDownloader(
            exchange,
            historical,
            page_size=1001,
        )


def test_invalid_time_range():
    exchange = FakeExchange([])
    historical = FakeHistoricalMarketData()

    downloader = HistoricalDownloader(
        exchange,
        historical,
    )

    start = datetime(
        2026,
        8,
        22,
        12,
        0,
        tzinfo=timezone.utc,
    )

    end = datetime(
        2026,
        8,
        22,
        10,
        0,
        tzinfo=timezone.utc,
    )

    with pytest.raises(
        ValueError,
        match="start_time cannot be later",
    ):
        downloader.download(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
            start_time=start,
            end_time=end,
        )


def test_empty_exchange_response():
    exchange = FakeExchange([[]])
    historical = FakeHistoricalMarketData()

    downloader = HistoricalDownloader(
        exchange,
        historical,
        page_size=100,
    )

    start = datetime(
        2026,
        8,
        22,
        10,
        0,
        tzinfo=timezone.utc,
    )

    end = datetime(
        2026,
        8,
        22,
        12,
        0,
        tzinfo=timezone.utc,
    )

    result = downloader.download(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        start_time=start,
        end_time=end,
    )

    assert result == []
    assert historical.saved_candles == []
    assert len(exchange.calls) == 1


def test_download_single_page():
    first = datetime(
        2026,
        8,
        22,
        10,
        0,
        tzinfo=timezone.utc,
    )

    second = datetime(
        2026,
        8,
        22,
        10,
        15,
        tzinfo=timezone.utc,
    )

    exchange = FakeExchange(
        [
            [
                make_candle(first),
                make_candle(
                    second,
                    close="115000.00",
                ),
            ]
        ]
    )

    historical = FakeHistoricalMarketData()

    downloader = HistoricalDownloader(
        exchange,
        historical,
        page_size=100,
    )

    result = downloader.download(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        start_time=first,
        end_time=second,
    )

    assert len(result) == 2

    assert result[0].timestamp == first
    assert result[1].timestamp == second

    assert len(historical.saved_candles) == 2


def test_download_paginates():
    first = datetime(
        2026,
        8,
        22,
        10,
        0,
        tzinfo=timezone.utc,
    )

    second = datetime(
        2026,
        8,
        22,
        10,
        15,
        tzinfo=timezone.utc,
    )

    third = datetime(
        2026,
        8,
        22,
        10,
        30,
        tzinfo=timezone.utc,
    )

    exchange = FakeExchange(
        [
            [make_candle(first)],
            [make_candle(second)],
            [make_candle(third)],
        ]
    )

    historical = FakeHistoricalMarketData()

    downloader = HistoricalDownloader(
        exchange,
        historical,
        page_size=1,
    )

    result = downloader.download(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        start_time=first,
        end_time=third,
    )

    assert len(result) == 3

    assert result[0].timestamp == first
    assert result[1].timestamp == second
    assert result[2].timestamp == third

    assert len(exchange.calls) == 3
    assert len(historical.saved_candles) == 3


def test_duplicate_candles_are_removed():
    first = datetime(
        2026,
        8,
        22,
        10,
        0,
        tzinfo=timezone.utc,
    )

    second = datetime(
        2026,
        8,
        22,
        10,
        15,
        tzinfo=timezone.utc,
    )

    exchange = FakeExchange(
        [
            [
                make_candle(first),
                make_candle(second),
            ],
            [
                make_candle(second),
            ],
        ]
    )

    historical = FakeHistoricalMarketData()

    downloader = HistoricalDownloader(
        exchange,
        historical,
        page_size=2,
    )

    result = downloader.download(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        start_time=first,
        end_time=second,
    )

    timestamps = [
        candle.timestamp
        for candle in result
    ]

    assert timestamps == [
        first,
        second,
    ]


def test_results_are_chronological():
    first = datetime(
        2026,
        8,
        22,
        10,
        0,
        tzinfo=timezone.utc,
    )

    second = datetime(
        2026,
        8,
        22,
        10,
        15,
        tzinfo=timezone.utc,
    )

    exchange = FakeExchange(
        [
            [
                make_candle(second),
                make_candle(first),
            ]
        ]
    )

    historical = FakeHistoricalMarketData()

    downloader = HistoricalDownloader(
        exchange,
        historical,
    )

    result = downloader.download(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        start_time=first,
        end_time=second,
    )

    assert result[0].timestamp == first
    assert result[1].timestamp == second


def test_out_of_range_candles_are_removed():
    before = datetime(
        2026,
        8,
        22,
        9,
        45,
        tzinfo=timezone.utc,
    )

    start = datetime(
        2026,
        8,
        22,
        10,
        0,
        tzinfo=timezone.utc,
    )

    end = datetime(
        2026,
        8,
        22,
        10,
        15,
        tzinfo=timezone.utc,
    )

    after = datetime(
        2026,
        8,
        22,
        10,
        30,
        tzinfo=timezone.utc,
    )

    exchange = FakeExchange(
        [
            [
                make_candle(before),
                make_candle(start),
                make_candle(end),
                make_candle(after),
            ]
        ]
    )

    historical = FakeHistoricalMarketData()

    downloader = HistoricalDownloader(
        exchange,
        historical,
    )

    result = downloader.download(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        start_time=start,
        end_time=end,
    )

    assert [
        candle.timestamp
        for candle in result
    ] == [start, end]


def test_exchange_parameters_are_correct():
    start = datetime(
        2026,
        8,
        22,
        10,
        0,
        tzinfo=timezone.utc,
    )

    end = datetime(
        2026,
        8,
        22,
        11,
        0,
        tzinfo=timezone.utc,
    )

    exchange = FakeExchange([[]])
    historical = FakeHistoricalMarketData()

    downloader = HistoricalDownloader(
        exchange,
        historical,
        page_size=250,
    )

    downloader.download(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.ONE_HOUR,
        start_time=start,
        end_time=end,
    )

    call = exchange.calls[0]

    assert call["symbol"] == Symbol.BTC_USDT
    assert call["timeframe"] == Timeframe.ONE_HOUR
    assert call["start_time"] == start
    assert call["end_time"] == end
    assert call["limit"] == 250


def test_candles_are_converted_to_stored_candles():
    timestamp = datetime(
        2026,
        8,
        22,
        10,
        0,
        tzinfo=timezone.utc,
    )

    exchange = FakeExchange(
        [
            [
                make_candle(timestamp),
            ]
        ]
    )

    historical = FakeHistoricalMarketData()

    downloader = HistoricalDownloader(
        exchange,
        historical,
    )

    result = downloader.download(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        start_time=timestamp,
        end_time=timestamp,
    )

    stored = result[0]

    assert stored.exchange == "binance"
    assert stored.symbol == Symbol.BTC_USDT
    assert stored.timeframe == Timeframe.FIFTEEN_MINUTES
    assert stored.timestamp == timestamp
    assert stored.close == Decimal("114500.00")