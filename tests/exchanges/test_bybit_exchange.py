from datetime import datetime, timezone
from decimal import Decimal

import pytest
import requests

from app.exchanges.bybit_exchange import BybitExchange
from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe


class FakeResponse:
    def __init__(self, data, status_code=200):
        self._data = data
        self.status_code = status_code
        self.headers = {}

    @property
    def ok(self):
        return 200 <= self.status_code < 400

    def json(self):
        return self._data

    def raise_for_status(self):
        if not self.ok:
            raise requests.HTTPError(
                f"{self.status_code} error"
            )


# ----------------------------------------------------------------------
# Construction
# ----------------------------------------------------------------------


def test_name():
    exchange = BybitExchange()

    assert exchange.name == "bybit"


def test_timeout_must_be_positive():
    with pytest.raises(
        ValueError,
        match="timeout must be greater than zero",
    ):
        BybitExchange(timeout=0)


def test_negative_timeout_is_rejected():
    with pytest.raises(
        ValueError,
        match="timeout must be greater than zero",
    ):
        BybitExchange(timeout=-1)


# ----------------------------------------------------------------------
# Symbol mapping
# ----------------------------------------------------------------------


def test_symbol_mapping():
    assert (
        BybitExchange._to_bybit_symbol(
            Symbol.BTC_USDT
        )
        == "BTCUSDT"
    )


# ----------------------------------------------------------------------
# Timeframe mapping
# ----------------------------------------------------------------------


def test_fifteen_minute_timeframe_mapping():
    assert (
        BybitExchange._to_bybit_timeframe(
            Timeframe.FIFTEEN_MINUTES
        )
        == "15"
    )


def test_one_hour_timeframe_mapping():
    assert (
        BybitExchange._to_bybit_timeframe(
            Timeframe.ONE_HOUR
        )
        == "60"
    )


def test_four_hour_timeframe_mapping():
    assert (
        BybitExchange._to_bybit_timeframe(
            Timeframe.FOUR_HOURS
        )
        == "240"
    )


def test_one_day_timeframe_mapping():
    assert (
        BybitExchange._to_bybit_timeframe(
            Timeframe.ONE_DAY
        )
        == "D"
    )


# ----------------------------------------------------------------------
# Timestamp
# ----------------------------------------------------------------------


def test_timestamp_conversion():
    value = datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )

    timestamp = BybitExchange._to_timestamp_ms(value)

    assert timestamp == 1767225600000


def test_naive_datetime_is_treated_as_utc():
    value = datetime(
        2026,
        1,
        1,
    )

    timestamp = BybitExchange._to_timestamp_ms(value)

    assert timestamp == 1767225600000


# ----------------------------------------------------------------------
# Candle parsing
# ----------------------------------------------------------------------


def test_parse_candle():
    data = [
        1767225600000,
        "100.00",
        "110.00",
        "95.00",
        "105.00",
        "123.45",
        "9999.99",
    ]

    candle = BybitExchange._parse_candle(
        data=data,
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.ONE_HOUR,
    )

    assert isinstance(candle, Candle)
    assert candle.exchange == "bybit"
    assert candle.symbol == Symbol.BTC_USDT
    assert candle.timeframe == Timeframe.ONE_HOUR

    assert candle.timestamp == datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )

    assert candle.open == Decimal("100.00")
    assert candle.high == Decimal("110.00")
    assert candle.low == Decimal("95.00")
    assert candle.close == Decimal("105.00")
    assert candle.volume == Decimal("123.45")


def test_parse_candle_accepts_string_timestamp():
    data = [
        "1767225600000",
        "100",
        "110",
        "95",
        "105",
        "10",
    ]

    candle = BybitExchange._parse_candle(
        data=data,
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.ONE_HOUR,
    )

    assert candle.timestamp == datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )


def test_parse_candle_requires_six_fields():
    with pytest.raises(
        ValueError,
        match="fewer than 6",
    ):
        BybitExchange._parse_candle(
            data=[1, 2, 3],
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.ONE_HOUR,
        )


def test_parse_candle_rejects_invalid_timestamp():
    with pytest.raises(
        ValueError,
        match="Invalid candle timestamp",
    ):
        BybitExchange._parse_candle(
            data=[
                "not-a-timestamp",
                "100",
                "110",
                "95",
                "105",
                "10",
            ],
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.ONE_HOUR,
        )


# ----------------------------------------------------------------------
# OHLCV validation
# ----------------------------------------------------------------------


def test_invalid_negative_volume():
    with pytest.raises(
        ValueError,
        match="Volume cannot be negative",
    ):
        BybitExchange._validate_ohlcv(
            open_price=Decimal("100"),
            high_price=Decimal("110"),
            low_price=Decimal("90"),
            close_price=Decimal("105"),
            volume=Decimal("-1"),
        )


def test_high_cannot_be_below_open():
    with pytest.raises(
        ValueError,
        match="High price cannot be below",
    ):
        BybitExchange._validate_ohlcv(
            open_price=Decimal("110"),
            high_price=Decimal("100"),
            low_price=Decimal("90"),
            close_price=Decimal("105"),
            volume=Decimal("10"),
        )


def test_low_cannot_be_above_close():
    with pytest.raises(
        ValueError,
        match="Low price cannot be above",
    ):
        BybitExchange._validate_ohlcv(
            open_price=Decimal("100"),
            high_price=Decimal("110"),
            low_price=Decimal("106"),
            close_price=Decimal("105"),
            volume=Decimal("10"),
        )


# ----------------------------------------------------------------------
# API envelope
# ----------------------------------------------------------------------


def test_get_rejects_bybit_api_error(monkeypatch):
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

    with pytest.raises(
        RuntimeError,
        match="Invalid symbol",
    ):
        exchange._get(
            "/v5/market/kline",
            params={
                "category": "spot",
                "symbol": "INVALID",
                "interval": "15",
            },
        )


def test_get_rejects_invalid_json(monkeypatch):
    exchange = BybitExchange()

    class InvalidJsonResponse:
        status_code = 200
        headers = {}
        ok = True

        def raise_for_status(self):
            pass

        def json(self):
            raise ValueError("invalid json")

    monkeypatch.setattr(
        exchange.http_client,
        "get",
        lambda *args, **kwargs: InvalidJsonResponse(),
    )

    with pytest.raises(
        RuntimeError,
        match="invalid JSON",
    ):
        exchange._get(
            "/v5/market/kline"
        )


def test_get_rejects_non_dict_response(monkeypatch):
    exchange = BybitExchange()

    response = FakeResponse(
        ["unexpected"]
    )

    monkeypatch.setattr(
        exchange.http_client,
        "get",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(
        RuntimeError,
        match="Invalid Bybit API response",
    ):
        exchange._get(
            "/v5/market/kline"
        )


def test_get_propagates_http_error(monkeypatch):
    exchange = BybitExchange()

    def failing_get(*args, **kwargs):
        raise requests.HTTPError(
            "500 server error"
        )

    monkeypatch.setattr(
        exchange.http_client,
        "get",
        failing_get,
    )

    with pytest.raises(
        requests.HTTPError,
        match="500 server error",
    ):
        exchange._get(
            "/v5/market/kline"
        )


# ----------------------------------------------------------------------
# Symbols
# ----------------------------------------------------------------------


def test_get_symbols_returns_supported_symbols(monkeypatch):
    exchange = BybitExchange()

    response = {
        "retCode": 0,
        "retMsg": "OK",
        "result": {
            "list": [
                {
                    "status": "Trading",
                    "baseCoin": "BTC",
                    "quoteCoin": "USDT",
                },
                {
                    "status": "Trading",
                    "baseCoin": "ETH",
                    "quoteCoin": "USDT",
                },
                {
                    "status": "Trading",
                    "baseCoin": "UNKNOWN",
                    "quoteCoin": "USDT",
                },
            ]
        },
    }

    monkeypatch.setattr(
        exchange.http_client,
        "get",
        lambda *args, **kwargs: FakeResponse(response),
    )

    symbols = exchange.get_symbols()

    assert Symbol.BTC_USDT in symbols


def test_get_symbols_ignores_non_trading_symbols(monkeypatch):
    exchange = BybitExchange()

    response = {
        "retCode": 0,
        "retMsg": "OK",
        "result": {
            "list": [
                {
                    "status": "Offline",
                    "baseCoin": "BTC",
                    "quoteCoin": "USDT",
                }
            ]
        },
    }

    monkeypatch.setattr(
        exchange.http_client,
        "get",
        lambda *args, **kwargs: FakeResponse(response),
    )

    symbols = exchange.get_symbols()

    assert Symbol.BTC_USDT not in symbols


def test_get_symbols_rejects_invalid_result(monkeypatch):
    exchange = BybitExchange()

    response = {
        "retCode": 0,
        "retMsg": "OK",
        "result": [],
    }

    monkeypatch.setattr(
        exchange.http_client,
        "get",
        lambda *args, **kwargs: FakeResponse(response),
    )

    with pytest.raises(
        RuntimeError,
        match="Invalid Bybit instruments response",
    ):
        exchange.get_symbols()


# ----------------------------------------------------------------------
# OHLCV
# ----------------------------------------------------------------------


def test_get_ohlcv_passes_correct_request(monkeypatch):
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

    captured = {}

    def fake_get(
        url,
        params=None,
    ):
        captured["url"] = url
        captured["params"] = params
        return response

    monkeypatch.setattr(
        exchange.http_client,
        "get",
        fake_get,
    )

    start = datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )

    end = datetime(
        2026,
        1,
        2,
        tzinfo=timezone.utc,
    )

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.ONE_HOUR,
        start_time=start,
        end_time=end,
        limit=100,
    )

    assert captured["url"] == (
        "https://api.bybit.com/v5/market/kline"
    )

    assert captured["params"] == {
        "category": "spot",
        "symbol": "BTCUSDT",
        "interval": "60",
        "limit": 100,
        "start": 1767225600000,
        "end": 1767312000000,
    }

    assert len(candles) == 1


def test_get_ohlcv_returns_chronological_order(
    monkeypatch,
):
    exchange = BybitExchange()

    response = FakeResponse(
        {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "list": [
                    [
                        "1767312000000",
                        "200",
                        "210",
                        "190",
                        "205",
                        "10",
                    ],
                    [
                        "1767225600000",
                        "100",
                        "110",
                        "90",
                        "105",
                        "20",
                    ],
                ]
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

    assert len(candles) == 2

    assert (
        candles[0].timestamp
        < candles[1].timestamp
    )


def test_get_ohlcv_removes_duplicates(
    monkeypatch,
):
    exchange = BybitExchange()

    duplicate = [
        "1767225600000",
        "100",
        "110",
        "90",
        "105",
        "20",
    ]

    response = FakeResponse(
        {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "list": [
                    duplicate,
                    duplicate,
                ]
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

    assert len(candles) == 1


def test_get_ohlcv_empty_response(monkeypatch):
    exchange = BybitExchange()

    response = FakeResponse(
        {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "list": []
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


def test_get_ohlcv_missing_list_returns_empty(
    monkeypatch,
):
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

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.ONE_HOUR,
    )

    assert candles == []


def test_get_ohlcv_rejects_invalid_limit():
    exchange = BybitExchange()

    with pytest.raises(ValueError):
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.ONE_HOUR,
            limit=0,
        )

    with pytest.raises(ValueError):
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.ONE_HOUR,
            limit=1001,
        )


def test_get_ohlcv_rejects_invalid_time_range():
    exchange = BybitExchange()

    start = datetime(
        2026,
        1,
        2,
        tzinfo=timezone.utc,
    )

    end = datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )

    with pytest.raises(
        ValueError,
        match="start_time cannot be later",
    ):
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.ONE_HOUR,
            start_time=start,
            end_time=end,
        )


def test_get_ohlcv_rejects_malformed_candle(
    monkeypatch,
):
    exchange = BybitExchange()

    response = FakeResponse(
        {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "list": [
                    [
                        "invalid",
                        "100",
                        "110",
                        "90",
                        "105",
                        "20",
                    ]
                ]
            },
        }
    )

    monkeypatch.setattr(
        exchange.http_client,
        "get",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(
        RuntimeError,
        match="Malformed Bybit candle",
    ):
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.ONE_HOUR,
        )


# ----------------------------------------------------------------------
# Latest candle
# ----------------------------------------------------------------------


def test_get_latest_candle(monkeypatch):
    exchange = BybitExchange()

    response = FakeResponse(
        {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "list": [
                    [
                        "1767225600000",
                        "100",
                        "110",
                        "90",
                        "105",
                        "20",
                    ]
                ]
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
    assert candle.exchange == "bybit"
    assert candle.close == Decimal("105")


def test_get_latest_candle_returns_none(
    monkeypatch,
):
    exchange = BybitExchange()

    response = FakeResponse(
        {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "list": []
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


# ----------------------------------------------------------------------
# Health
# ----------------------------------------------------------------------


def test_health_check_success(monkeypatch):
    exchange = BybitExchange()

    response = FakeResponse(
        {
            "retCode": 0,
            "retMsg": "OK",
            "result": {
                "timeSecond": "1767225600",
            },
        }
    )

    monkeypatch.setattr(
        exchange.http_client,
        "get",
        lambda *args, **kwargs: response,
    )

    assert exchange.health_check() is True


def test_health_check_failure(monkeypatch):
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