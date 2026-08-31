from datetime import datetime, timezone
from decimal import Decimal

import pytest
import requests

from app.exchanges.okx_exchange import OKXExchange
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


# =====================================================================
# BASIC
# =====================================================================


def test_name():
    exchange = OKXExchange()

    assert exchange.name == "okx"


def test_timeout_must_be_positive():
    with pytest.raises(
        ValueError,
        match="timeout must be greater than zero",
    ):
        OKXExchange(timeout=0)


def test_negative_timeout_is_rejected():
    with pytest.raises(
        ValueError,
        match="timeout must be greater than zero",
    ):
        OKXExchange(timeout=-1)


# =====================================================================
# SYMBOL
# =====================================================================


def test_symbol_mapping():
    assert (
        OKXExchange._to_okx_symbol(
            Symbol.BTC_USDT
        )
        == "BTC-USDT"
    )


# =====================================================================
# TIMEFRAMES
# =====================================================================


def test_fifteen_minute_timeframe_mapping():
    assert (
        OKXExchange._to_okx_timeframe(
            Timeframe.FIFTEEN_MINUTES
        )
        == "15m"
    )


def test_one_hour_timeframe_mapping():
    assert (
        OKXExchange._to_okx_timeframe(
            Timeframe.ONE_HOUR
        )
        == "1H"
    )


def test_four_hour_timeframe_mapping():
    assert (
        OKXExchange._to_okx_timeframe(
            Timeframe.FOUR_HOURS
        )
        == "4H"
    )


def test_one_day_timeframe_mapping():
    assert (
        OKXExchange._to_okx_timeframe(
            Timeframe.ONE_DAY
        )
        == "1D"
    )


# =====================================================================
# TIMESTAMP
# =====================================================================


def test_timestamp_conversion():
    value = datetime(
        2026,
        1,
        1,
        tzinfo=timezone.utc,
    )

    assert (
        OKXExchange._to_timestamp_ms(value)
        == 1767225600000
    )


def test_naive_datetime_is_treated_as_utc():
    value = datetime(
        2026,
        1,
        1,
    )

    assert (
        OKXExchange._to_timestamp_ms(value)
        == 1767225600000
    )


# =====================================================================
# CANDLE PARSING
# =====================================================================


def test_parse_candle():
    candle = OKXExchange._parse_candle(
        data=[
            "1767225600000",
            "100",
            "110",
            "90",
            "105",
            "20",
            "2000",
            "2000",
            "1",
        ],
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.ONE_HOUR,
    )

    assert candle.exchange == "okx"
    assert candle.symbol == Symbol.BTC_USDT
    assert candle.timeframe == Timeframe.ONE_HOUR
    assert candle.open == Decimal("100")
    assert candle.high == Decimal("110")
    assert candle.low == Decimal("90")
    assert candle.close == Decimal("105")
    assert candle.volume == Decimal("20")


def test_parse_candle_accepts_string_timestamp():
    candle = OKXExchange._parse_candle(
        data=[
            "1767225600000",
            "100",
            "110",
            "90",
            "105",
            "20",
        ],
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
        match="fewer than 6 required fields",
    ):
        OKXExchange._parse_candle(
            data=[
                "1767225600000",
                "100",
                "110",
                "90",
                "105",
            ],
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.ONE_HOUR,
        )


def test_parse_candle_rejects_invalid_timestamp():
    with pytest.raises(
        ValueError,
        match="Invalid candle timestamp",
    ):
        OKXExchange._parse_candle(
            data=[
                "not-a-timestamp",
                "100",
                "110",
                "90",
                "105",
                "20",
            ],
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.ONE_HOUR,
        )


# =====================================================================
# VALIDATION
# =====================================================================


def test_invalid_negative_volume():
    with pytest.raises(
        ValueError,
        match="Volume cannot be negative",
    ):
        OKXExchange._validate_ohlcv(
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
        OKXExchange._validate_ohlcv(
            open_price=Decimal("110"),
            high_price=Decimal("105"),
            low_price=Decimal("90"),
            close_price=Decimal("100"),
            volume=Decimal("20"),
        )


def test_low_cannot_be_above_close():
    with pytest.raises(
        ValueError,
        match="Low price cannot be above",
    ):
        OKXExchange._validate_ohlcv(
            open_price=Decimal("100"),
            high_price=Decimal("110"),
            low_price=Decimal("106"),
            close_price=Decimal("105"),
            volume=Decimal("20"),
        )


# =====================================================================
# API ERRORS
# =====================================================================


def test_get_rejects_okx_api_error(
    monkeypatch,
):
    exchange = OKXExchange()

    response = FakeResponse(
        {
            "code": "51000",
            "msg": "Invalid instrument",
            "data": [],
        }
    )

    monkeypatch.setattr(
        requests,
        "request",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(
        RuntimeError,
        match="Invalid instrument",
    ):
        exchange._get(
            "/api/v5/market/candles"
        )


def test_get_rejects_invalid_json(
    monkeypatch,
):
    exchange = OKXExchange()

    class InvalidJsonResponse:
        status_code = 200
        headers = {}
        ok = True

        def raise_for_status(self):
            pass

        def json(self):
            raise ValueError("invalid json")

    monkeypatch.setattr(
        requests,
        "request",
        lambda *args, **kwargs: InvalidJsonResponse(),
    )

    with pytest.raises(
        RuntimeError,
        match="invalid JSON",
    ):
        exchange._get(
            "/api/v5/market/candles"
        )


def test_get_rejects_non_dict_response(
    monkeypatch,
):
    exchange = OKXExchange()

    response = FakeResponse(
        ["unexpected"]
    )

    monkeypatch.setattr(
        requests,
        "request",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(
        RuntimeError,
        match="Invalid OKX API response",
    ):
        exchange._get(
            "/api/v5/market/candles"
        )


# =====================================================================
# OHLCV REQUEST
# =====================================================================


def test_get_ohlcv_passes_correct_request(
    monkeypatch,
):
    exchange = OKXExchange()

    response = FakeResponse(
        {
            "code": "0",
            "msg": "",
            "data": [
                [
                    "1767229200000",
                    "105",
                    "110",
                    "100",
                    "108",
                    "50",
                    "5000",
                    "5000",
                    "1",
                ]
            ],
        }
    )

    captured = {}

    def fake_request(
        method,
        url,
        params=None,
        headers=None,
        timeout=None,
    ):
        captured["method"] = method
        captured["url"] = url
        captured["params"] = params
        captured["timeout"] = timeout

        return response

    monkeypatch.setattr(
        requests,
        "request",
        fake_request,
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

    assert len(candles) == 1

    assert captured["method"] == "GET"

    assert (
        captured["url"]
        == "https://www.okx.com/api/v5/market/candles"
    )

    assert captured["params"] == {
        "instId": "BTC-USDT",
        "bar": "1H",
        "limit": 100,
        "after": 1767225600000,
        "before": 1767312000000,
    }

    assert captured["timeout"] == 10.0


# =====================================================================
# OHLCV ORDER
# =====================================================================


def test_get_ohlcv_returns_chronological_order(
    monkeypatch,
):
    exchange = OKXExchange()

    response = FakeResponse(
        {
            "code": "0",
            "msg": "",
            "data": [
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
            ],
        }
    )

    monkeypatch.setattr(
        requests,
        "request",
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

    assert candles[0].close == Decimal("105")
    assert candles[1].close == Decimal("205")


# =====================================================================
# DUPLICATES
# =====================================================================


def test_get_ohlcv_removes_duplicates(
    monkeypatch,
):
    exchange = OKXExchange()

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
            "code": "0",
            "msg": "",
            "data": [
                duplicate,
                duplicate,
            ],
        }
    )

    monkeypatch.setattr(
        requests,
        "request",
        lambda *args, **kwargs: response,
    )

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.ONE_HOUR,
    )

    assert len(candles) == 1


# =====================================================================
# EMPTY
# =====================================================================


def test_get_ohlcv_empty_response(
    monkeypatch,
):
    exchange = OKXExchange()

    response = FakeResponse(
        {
            "code": "0",
            "msg": "",
            "data": [],
        }
    )

    monkeypatch.setattr(
        requests,
        "request",
        lambda *args, **kwargs: response,
    )

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.ONE_HOUR,
    )

    assert candles == []


# =====================================================================
# LIMIT / RANGE
# =====================================================================


def test_get_ohlcv_rejects_invalid_limit():
    exchange = OKXExchange()

    with pytest.raises(
        ValueError,
        match="limit must be between",
    ):
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.ONE_HOUR,
            limit=0,
        )

    with pytest.raises(
        ValueError,
        match="limit must be between",
    ):
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.ONE_HOUR,
            limit=301,
        )


def test_get_ohlcv_rejects_invalid_time_range():
    exchange = OKXExchange()

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


# =====================================================================
# LATEST CANDLE
# =====================================================================


def test_get_latest_candle(
    monkeypatch,
):
    exchange = OKXExchange()

    response = FakeResponse(
        {
            "code": "0",
            "msg": "",
            "data": [
                [
                    "1767225600000",
                    "100",
                    "110",
                    "90",
                    "105",
                    "20",
                ]
            ],
        }
    )

    monkeypatch.setattr(
        requests,
        "request",
        lambda *args, **kwargs: response,
    )

    candle = exchange.get_latest_candle(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.ONE_HOUR,
    )

    assert candle is not None
    assert candle.exchange == "okx"
    assert candle.close == Decimal("105")


def test_get_latest_candle_returns_none(
    monkeypatch,
):
    exchange = OKXExchange()

    response = FakeResponse(
        {
            "code": "0",
            "msg": "",
            "data": [],
        }
    )

    monkeypatch.setattr(
        requests,
        "request",
        lambda *args, **kwargs: response,
    )

    candle = exchange.get_latest_candle(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.ONE_HOUR,
    )

    assert candle is None


# =====================================================================
# HEALTH CHECK
# =====================================================================


def test_health_check_success(
    monkeypatch,
):
    exchange = OKXExchange()

    response = FakeResponse(
        {
            "code": "0",
            "msg": "",
            "data": [
                {
                    "ts": "1767225600000"
                }
            ],
        }
    )

    monkeypatch.setattr(
        requests,
        "request",
        lambda *args, **kwargs: response,
    )

    assert exchange.health_check() is True


def test_health_check_failure(
    monkeypatch,
):
    exchange = OKXExchange()

    def failing_request(*args, **kwargs):
        raise requests.ConnectionError(
            "connection failed"
        )

    monkeypatch.setattr(
        requests,
        "request",
        failing_request,
    )

    assert exchange.health_check() is False