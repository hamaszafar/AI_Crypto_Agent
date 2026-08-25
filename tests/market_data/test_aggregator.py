from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.exchanges.types import Symbol, Timeframe
from app.market_data.aggregator import MarketDataAggregator
from app.market_data.models import MarketCandle
from app.market_data.service import MarketDataService


class FakeService:
    def __init__(
        self,
        name: str,
        *,
        healthy: bool = True,
    ) -> None:
        self.exchange_name = name
        self._healthy = healthy

    def health_check(self) -> bool:
        return self._healthy

    def get_candles(
        self,
        symbol,
        timeframe,
        start_time=None,
        end_time=None,
        limit=500,
    ):
        return [
            MarketCandle(
                exchange=self.exchange_name,
                symbol=symbol.value,
                timeframe=timeframe.value,
                timestamp=datetime(
                    2026,
                    8,
                    22,
                    12,
                    0,
                    tzinfo=timezone.utc,
                ),
                open=Decimal("100"),
                high=Decimal("110"),
                low=Decimal("90"),
                close=Decimal("105"),
                volume=Decimal("10"),
            )
        ]

    def get_latest_candle(
        self,
        symbol,
        timeframe,
    ):
        candles = self.get_candles(
            symbol,
            timeframe,
        )

        return candles[-1]


def make_aggregator() -> MarketDataAggregator:
    return MarketDataAggregator(
        {
            "binance": FakeService("binance"),
            "bybit": FakeService("bybit"),
            "okx": FakeService("okx"),
        }
    )


def test_aggregator_requires_service():
    with pytest.raises(ValueError):
        MarketDataAggregator({})


def test_aggregator_exchange_names():
    aggregator = make_aggregator()

    assert aggregator.exchange_names == [
        "binance",
        "bybit",
        "okx",
    ]


def test_aggregator_health_check():
    aggregator = make_aggregator()

    result = aggregator.health_check()

    assert result == {
        "binance": True,
        "bybit": True,
        "okx": True,
    }


def test_aggregator_get_candles():
    aggregator = make_aggregator()

    result = aggregator.get_candles(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert set(result.keys()) == {
        "binance",
        "bybit",
        "okx",
    }

    for exchange, candles in result.items():
        assert len(candles) == 1
        assert candles[0].exchange == exchange


def test_aggregator_get_latest_candles():
    aggregator = make_aggregator()

    result = aggregator.get_latest_candles(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.ONE_HOUR,
    )

    assert set(result.keys()) == {
        "binance",
        "bybit",
        "okx",
    }

    for candle in result.values():
        assert candle is not None
        assert isinstance(candle, MarketCandle)


def test_from_exchanges_requires_exchange():
    with pytest.raises(ValueError):
        MarketDataAggregator.from_exchanges([])


def test_from_exchanges_creates_services():
    aggregator = MarketDataAggregator.from_exchanges(
        ["mock"]
    )

    assert aggregator.exchange_names == ["mock"]


def test_aggregator_accepts_existing_services():
    services = {
        "binance": FakeService("binance"),
        "bybit": FakeService("bybit"),
    }

    aggregator = MarketDataAggregator(services)

    assert aggregator.exchange_names == [
        "binance",
        "bybit",
    ]