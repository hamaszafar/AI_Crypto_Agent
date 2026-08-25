from datetime import datetime, timezone
from decimal import Decimal

import requests

from app.exchanges.bybit_exchange import BybitExchange
from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe


def test_bybit_exchange_name():
    exchange = BybitExchange()

    assert exchange.name == "bybit"


def test_bybit_symbol_conversion():
    exchange = BybitExchange()

    assert (
        exchange._symbol_to_bybit(Symbol.BTC_USDT)
        == "BTCUSDT"
    )

    assert (
        exchange._symbol_to_bybit(Symbol.ETH_USDT)
        == "ETHUSDT"
    )


def test_bybit_timeframe_conversion():
    exchange = BybitExchange()

    assert (
        exchange._timeframe_to_bybit(
            Timeframe.FIFTEEN_MINUTES
        )
        == "15"
    )

    assert (
        exchange._timeframe_to_bybit(
            Timeframe.ONE_HOUR
        )
        == "60"
    )

    assert (
        exchange._timeframe_to_bybit(
            Timeframe.FOUR_HOURS
        )
        == "240"
    )

    assert (
        exchange._timeframe_to_bybit(
            Timeframe.ONE_DAY
        )
        == "D"
    )


def test_bybit_timestamp_conversion():
    timestamp = datetime(
        2026,
        8,
        22,
        0,
        0,
        tzinfo=timezone.utc,
    )

    milliseconds = BybitExchange._timestamp_to_milliseconds(
        timestamp
    )

    converted = BybitExchange._milliseconds_to_datetime(
        milliseconds
    )

    assert converted == timestamp


def test_parse_bybit_candle():
    row = [
        "1755820800000",
        "77181.07",
        "77399.51",
        "77181.07",
        "77258.13",
        "204.87434",
        "15800000",
    ]

    candle = BybitExchange._parse_bybit_candle(
        row,
        Symbol.BTC_USDT,
        Timeframe.FIFTEEN_MINUTES,
    )

    assert isinstance(candle, Candle)
    assert candle.exchange == "bybit"
    assert candle.symbol == Symbol.BTC_USDT
    assert candle.timeframe == Timeframe.FIFTEEN_MINUTES

    assert candle.open == Decimal("77181.07")
    assert candle.high == Decimal("77399.51")
    assert candle.low == Decimal("77181.07")
    assert candle.close == Decimal("77258.13")
    assert candle.volume == Decimal("204.87434")


def test_get_ohlcv(monkeypatch):
    exchange = BybitExchange()

    response_data = {
        "retCode": 0,
        "retMsg": "OK",
        "result": {
            "list": [
                [
                    "1755820800000",
                    "100",
                    "102",
                    "99",
                    "101",
                    "1000",
                    "100000",
                ],
                [
                    "1755821700000",
                    "101",
                    "103",
                    "100",
                    "102",
                    "1100",
                    "110000",
                ],
            ]
        },
    }

    monkeypatch.setattr(
        exchange,
        "_get",
        lambda path, params: response_data,
    )

    candles = exchange.get_ohlcv(
        Symbol.BTC_USDT,
        Timeframe.FIFTEEN_MINUTES,
        limit=2,
    )

    assert len(candles) == 2
    assert candles[0].close == Decimal("101")
    assert candles[1].close == Decimal("102")


def test_get_ohlcv_sorted_chronologically(monkeypatch):
    exchange = BybitExchange()

    response_data = {
        "retCode": 0,
        "result": {
            "list": [
                [
                    "1755821700000",
                    "101",
                    "103",
                    "100",
                    "102",
                    "1100",
                    "110000",
                ],
                [
                    "1755820800000",
                    "100",
                    "102",
                    "99",
                    "101",
                    "1000",
                    "100000",
                ],
            ]
        },
    }

    monkeypatch.setattr(
        exchange,
        "_get",
        lambda path, params: response_data,
    )

    candles = exchange.get_ohlcv(
        Symbol.BTC_USDT,
        Timeframe.FIFTEEN_MINUTES,
        limit=2,
    )

    assert candles[0].timestamp < candles[1].timestamp


def test_get_ohlcv_rejects_invalid_limit():
    exchange = BybitExchange()

    try:
        exchange.get_ohlcv(
            Symbol.BTC_USDT,
            Timeframe.FIFTEEN_MINUTES,
            limit=1001,
        )
        assert False
    except ValueError:
        assert True


def test_get_ohlcv_zero_limit():
    exchange = BybitExchange()

    candles = exchange.get_ohlcv(
        Symbol.BTC_USDT,
        Timeframe.FIFTEEN_MINUTES,
        limit=0,
    )

    assert candles == []


def test_get_latest_candle(monkeypatch):
    exchange = BybitExchange()

    response_data = {
        "retCode": 0,
        "result": {
            "list": [
                [
                    "1755820800000",
                    "100",
                    "102",
                    "99",
                    "101",
                    "1000",
                    "100000",
                ]
            ]
        },
    }

    monkeypatch.setattr(
        exchange,
        "_get",
        lambda path, params: response_data,
    )

    candle = exchange.get_latest_candle(
        Symbol.BTC_USDT,
        Timeframe.ONE_HOUR,
    )

    assert candle is not None
    assert candle.exchange == "bybit"


def test_get_latest_candle_returns_none(monkeypatch):
    exchange = BybitExchange()

    response_data = {
        "retCode": 0,
        "result": {
            "list": []
        },
    }

    monkeypatch.setattr(
        exchange,
        "_get",
        lambda path, params: response_data,
    )

    candle = exchange.get_latest_candle(
        Symbol.BTC_USDT,
        Timeframe.ONE_HOUR,
    )

    assert candle is None


def test_get_symbols():
    exchange = BybitExchange()

    assert exchange.get_symbols() == list(Symbol)


def test_health_check_success(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "retCode": 0,
                "retMsg": "OK",
            }

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: FakeResponse(),
    )

    exchange = BybitExchange()

    assert exchange.health_check() is True


def test_health_check_failure(monkeypatch):
    def raise_error(*args, **kwargs):
        raise requests.RequestException()

    monkeypatch.setattr(
        requests,
        "get",
        raise_error,
    )

    exchange = BybitExchange()

    assert exchange.health_check() is False


def test_get_ohlcv_passes_correct_request(monkeypatch):
    exchange = BybitExchange()

    captured = {}

    def fake_get(path, params):
        captured["path"] = path
        captured["params"] = params

        return {
            "retCode": 0,
            "result": {
                "list": []
            },
        }

    monkeypatch.setattr(
        exchange,
        "_get",
        fake_get,
    )

    start = datetime(
        2026,
        8,
        22,
        0,
        0,
        tzinfo=timezone.utc,
    )

    end = datetime(
        2026,
        8,
        22,
        2,
        0,
        tzinfo=timezone.utc,
    )

    exchange.get_ohlcv(
        Symbol.BTC_USDT,
        Timeframe.FIFTEEN_MINUTES,
        start_time=start,
        end_time=end,
        limit=100,
    )

    assert captured["path"] == "/v5/market/kline"

    assert captured["params"]["category"] == "spot"
    assert captured["params"]["symbol"] == "BTCUSDT"
    assert captured["params"]["interval"] == "15"
    assert captured["params"]["limit"] == 100
    assert captured["params"]["start"] == int(
        start.timestamp() * 1000
    )
    assert captured["params"]["end"] == int(
        end.timestamp() * 1000
    )