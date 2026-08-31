from datetime import datetime, timezone
from decimal import Decimal

import requests

from app.exchanges.bybit_exchange import BybitExchange
from app.exchanges.factory import ExchangeFactory
from app.exchanges.types import Symbol, Timeframe


class FakeResponse:
    def __init__(
        self,
        payload,
        status_code=200,
    ):
        self._payload = payload
        self.status_code = status_code
        self.headers = {}
        self.ok = status_code < 400

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"HTTP {self.status_code}"
            )

    def json(self):
        return self._payload


def test_bybit_is_registered():
    available = ExchangeFactory.available_exchanges()

    assert "bybit" in available


def test_factory_creates_bybit():
    exchange = ExchangeFactory.create("bybit")

    assert isinstance(exchange, BybitExchange)
    assert exchange.name == "bybit"


def test_bybit_get_ohlcv_normalizes_response(monkeypatch):
    exchange = BybitExchange()

    response = FakeResponse(
        {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "category": "spot",
                "symbol": "BTCUSDT",
                "list": [
                    [
                        "1767229200000",
                        "105",
                        "110",
                        "100",
                        "108",
                        "50",
                        "5000",
                    ]
                ],
            },
        }
    )

    monkeypatch.setattr(
        exchange.http_client,
        "get",
        lambda *args, **kwargs: response,
    )

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.ONE_HOUR,
        limit=1,
    )

    assert len(candles) == 1

    candle = candles[0]

    assert candle.exchange == "bybit"
    assert candle.symbol == Symbol.BTC_USDT
    assert candle.timeframe == Timeframe.ONE_HOUR

    assert candle.open == Decimal("105")
    assert candle.high == Decimal("110")
    assert candle.low == Decimal("100")
    assert candle.close == Decimal("108")
    assert candle.volume == Decimal("50")

    assert candle.timestamp == datetime(
        2026,
        1,
        1,
        1,
        0,
        tzinfo=timezone.utc,
    )


def test_bybit_get_ohlcv_handles_api_error(monkeypatch):
    exchange = BybitExchange()

    response = FakeResponse(
        {
            "retCode": 10001,
            "retMsg": "Invalid symbol",
        }
    )

    monkeypatch.setattr(
        exchange.http_client,
        "get",
        lambda *args, **kwargs: response,
    )

    try:
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.ONE_HOUR,
        )
        assert False, "Expected RuntimeError"
    except RuntimeError as exc:
        assert "Invalid symbol" in str(exc)


def test_bybit_get_ohlcv_handles_empty_result(monkeypatch):
    exchange = BybitExchange()

    response = FakeResponse(
        {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "list": [],
            },
        }
    )

    monkeypatch.setattr(
        exchange.http_client,
        "get",
        lambda *args, **kwargs: response,
    )

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.ONE_HOUR,
    )

    assert candles == []


def test_bybit_latest_candle(monkeypatch):
    exchange = BybitExchange()

    response = FakeResponse(
        {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "list": [
                    [
                        "1767254400000",
                        "100",
                        "110",
                        "90",
                        "105",
                        "20",
                    ]
                ],
            },
        }
    )

    monkeypatch.setattr(
        exchange.http_client,
        "get",
        lambda *args, **kwargs: response,
    )

    candle = exchange.get_latest_candle(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.ONE_HOUR,
    )

    assert candle is not None
    assert candle.close == Decimal("105")


def test_bybit_latest_candle_empty(monkeypatch):
    exchange = BybitExchange()

    response = FakeResponse(
        {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "list": [],
            },
        }
    )

    monkeypatch.setattr(
        exchange.http_client,
        "get",
        lambda *args, **kwargs: response,
    )

    candle = exchange.get_latest_candle(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.ONE_HOUR,
    )

    assert candle is None


def test_bybit_health_check_success(monkeypatch):
    exchange = BybitExchange()

    response = FakeResponse(
        {
            "retCode": 0,
            "retMsg": "OK",
            "result": {},
        }
    )

    monkeypatch.setattr(
        exchange.http_client,
        "get",
        lambda *args, **kwargs: response,
    )

    assert exchange.health_check() is True


def test_bybit_health_check_failure(monkeypatch):
    exchange = BybitExchange()

    def failing_get(*args, **kwargs):
        raise requests.ConnectionError(
            "connection failed"
        )

    monkeypatch.setattr(
        exchange.http_client,
        "get",
        failing_get,
    )

    assert exchange.health_check() is False