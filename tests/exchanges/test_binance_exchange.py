from datetime import datetime, timezone
from decimal import Decimal

import pytest
import requests

from app.exchanges.binance_exchange import BinanceExchange
from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe


class FakeResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


# ---------------------------------------------------------------------------
# Basic Binance adapter tests
# ---------------------------------------------------------------------------


def test_binance_exchange_name():
    exchange = BinanceExchange()

    assert exchange.name == "binance"


def test_binance_symbol_conversion():
    assert (
        BinanceExchange._to_binance_symbol(
            Symbol.BTC_USDT
        )
        == "BTCUSDT"
    )

    assert (
        BinanceExchange._to_binance_symbol(
            Symbol.ETH_USDT
        )
        == "ETHUSDT"
    )


def test_binance_timeframe_conversion():
    assert (
        BinanceExchange._to_binance_timeframe(
            Timeframe.FIFTEEN_MINUTES
        )
        == "15m"
    )

    assert (
        BinanceExchange._to_binance_timeframe(
            Timeframe.ONE_HOUR
        )
        == "1h"
    )

    assert (
        BinanceExchange._to_binance_timeframe(
            Timeframe.FOUR_HOURS
        )
        == "4h"
    )

    assert (
        BinanceExchange._to_binance_timeframe(
            Timeframe.ONE_DAY
        )
        == "1d"
    )


def test_binance_timestamp_conversion():
    timestamp = datetime(
        2026,
        8,
        22,
        10,
        0,
        tzinfo=timezone.utc,
    )

    result = BinanceExchange._to_timestamp_ms(
        timestamp
    )

    assert result == 1787392800000


def test_parse_binance_candle():
    raw_candle = [
        1787392800000,
        "114000.00",
        "115000.00",
        "113500.00",
        "114500.00",
        "123.45",
        1787393699999,
        "14000000.00",
        1000,
        "60.00",
        "7000000.00",
        "0",
    ]

    candle = BinanceExchange._parse_candle(
        data=raw_candle,
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert isinstance(candle, Candle)
    assert candle.exchange == "binance"
    assert candle.symbol == Symbol.BTC_USDT
    assert (
        candle.timeframe
        == Timeframe.FIFTEEN_MINUTES
    )
    assert candle.open == Decimal("114000.00")
    assert candle.high == Decimal("115000.00")
    assert candle.low == Decimal("113500.00")
    assert candle.close == Decimal("114500.00")
    assert candle.volume == Decimal("123.45")
    assert candle.timestamp.tzinfo == timezone.utc


# ---------------------------------------------------------------------------
# OHLCV retrieval
# ---------------------------------------------------------------------------


def test_get_ohlcv(monkeypatch):
    exchange = BinanceExchange()

    raw_candles = [
        [
            1787392800000,
            "114000.00",
            "115000.00",
            "113500.00",
            "114500.00",
            "123.45",
            1787393699999,
            "14000000.00",
            1000,
            "60.00",
            "7000000.00",
            "0",
        ],
        [
            1787393700000,
            "114500.00",
            "115500.00",
            "114000.00",
            "115000.00",
            "150.25",
            1787394599999,
            "15000000.00",
            1200,
            "70.00",
            "7500000.00",
            "0",
        ],
    ]

    def fake_get(endpoint, params=None):
        assert endpoint == "/api/v3/klines"
        assert params["symbol"] == "BTCUSDT"
        assert params["interval"] == "15m"
        assert params["limit"] == 2

        return raw_candles

    monkeypatch.setattr(
        exchange,
        "_get",
        fake_get,
    )

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        limit=2,
    )

    assert len(candles) == 2
    assert candles[0].close == Decimal("114500.00")
    assert candles[1].close == Decimal("115000.00")
    assert candles[0].exchange == "binance"
    assert candles[1].exchange == "binance"


def test_get_ohlcv_with_time_range(monkeypatch):
    exchange = BinanceExchange()

    start_time = datetime(
        2026,
        8,
        22,
        10,
        0,
        tzinfo=timezone.utc,
    )

    end_time = datetime(
        2026,
        8,
        22,
        12,
        0,
        tzinfo=timezone.utc,
    )

    captured_params = {}

    def fake_get(endpoint, params=None):
        captured_params.update(params)
        return []

    monkeypatch.setattr(
        exchange,
        "_get",
        fake_get,
    )

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.ONE_HOUR,
        start_time=start_time,
        end_time=end_time,
        limit=100,
    )

    assert candles == []
    assert captured_params["symbol"] == "BTCUSDT"
    assert captured_params["interval"] == "1h"
    assert captured_params["limit"] == 100
    assert captured_params["startTime"] == 1787392800000
    assert captured_params["endTime"] == 1787400000000


def test_get_ohlcv_rejects_invalid_limit():
    exchange = BinanceExchange()

    with pytest.raises(ValueError):
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
            limit=0,
        )

    with pytest.raises(ValueError):
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
            limit=1001,
        )


def test_get_ohlcv_returns_empty_list_for_empty_response(
    monkeypatch,
):
    exchange = BinanceExchange()

    monkeypatch.setattr(
        exchange,
        "_get",
        lambda endpoint, params=None: [],
    )

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert candles == []


def test_get_ohlcv_rejects_malformed_response(
    monkeypatch,
):
    exchange = BinanceExchange()

    monkeypatch.setattr(
        exchange,
        "_get",
        lambda endpoint, params=None: {
            "unexpected": "response"
        },
    )

    with pytest.raises(
        RuntimeError,
        match="kline response must be a list",
    ):
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )


def test_get_ohlcv_rejects_incomplete_candle(
    monkeypatch,
):
    exchange = BinanceExchange()

    malformed_candle = [
        1787392800000,
        "114000.00",
        "115000.00",
    ]

    monkeypatch.setattr(
        exchange,
        "_get",
        lambda endpoint, params=None: [
            malformed_candle
        ],
    )

    with pytest.raises(
        RuntimeError,
        match="Malformed Binance candle",
    ):
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )


def test_get_ohlcv_rejects_invalid_ohlcv(
    monkeypatch,
):
    exchange = BinanceExchange()

    invalid_candle = [
        1787392800000,
        "100.00",
        "90.00",
        "95.00",
        "105.00",
        "500.00",
    ]

    monkeypatch.setattr(
        exchange,
        "_get",
        lambda endpoint, params=None: [
            invalid_candle
        ],
    )

    with pytest.raises(
        RuntimeError,
        match="Malformed Binance candle",
    ):
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )


def test_get_ohlcv_removes_duplicate_candles(
    monkeypatch,
):
    exchange = BinanceExchange()

    candle = [
        1787392800000,
        "114000.00",
        "115000.00",
        "113500.00",
        "114500.00",
        "123.45",
    ]

    monkeypatch.setattr(
        exchange,
        "_get",
        lambda endpoint, params=None: [
            candle,
            candle,
        ],
    )

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert len(candles) == 1


def test_get_ohlcv_sorts_candles_chronologically(
    monkeypatch,
):
    exchange = BinanceExchange()

    later_candle = [
        1787393700000,
        "114500.00",
        "115500.00",
        "114000.00",
        "115000.00",
        "150.25",
    ]

    earlier_candle = [
        1787392800000,
        "114000.00",
        "115000.00",
        "113500.00",
        "114500.00",
        "123.45",
    ]

    monkeypatch.setattr(
        exchange,
        "_get",
        lambda endpoint, params=None: [
            later_candle,
            earlier_candle,
        ],
    )

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert len(candles) == 2

    assert (
        candles[0].timestamp
        < candles[1].timestamp
    )

    assert candles[0].close == Decimal(
        "114500.00"
    )

    assert candles[1].close == Decimal(
        "115000.00"
    )


def test_get_ohlcv_rejects_reversed_time_range():
    exchange = BinanceExchange()

    start_time = datetime(
        2026,
        8,
        22,
        12,
        0,
        tzinfo=timezone.utc,
    )

    end_time = datetime(
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
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.ONE_HOUR,
            start_time=start_time,
            end_time=end_time,
        )


# ---------------------------------------------------------------------------
# Latest candle
# ---------------------------------------------------------------------------


def test_get_latest_candle(monkeypatch):
    exchange = BinanceExchange()

    expected_candle = Candle(
        exchange="binance",
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        timestamp=datetime(
            2026,
            8,
            22,
            10,
            0,
            tzinfo=timezone.utc,
        ),
        open=Decimal("114000.00"),
        high=Decimal("115000.00"),
        low=Decimal("113500.00"),
        close=Decimal("114500.00"),
        volume=Decimal("123.45"),
    )

    def fake_get_ohlcv(*args, **kwargs):
        return [expected_candle]

    monkeypatch.setattr(
        exchange,
        "get_ohlcv",
        fake_get_ohlcv,
    )

    candle = exchange.get_latest_candle(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert candle == expected_candle


def test_get_latest_candle_returns_none_when_empty(
    monkeypatch,
):
    exchange = BinanceExchange()

    monkeypatch.setattr(
        exchange,
        "get_ohlcv",
        lambda *args, **kwargs: [],
    )

    candle = exchange.get_latest_candle(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert candle is None


# ---------------------------------------------------------------------------
# Symbols
# ---------------------------------------------------------------------------


def test_get_symbols(monkeypatch):
    exchange = BinanceExchange()

    exchange_info = {
        "symbols": [
            {
                "symbol": "BTCUSDT",
                "status": "TRADING",
                "baseAsset": "BTC",
                "quoteAsset": "USDT",
            },
            {
                "symbol": "ETHUSDT",
                "status": "TRADING",
                "baseAsset": "ETH",
                "quoteAsset": "USDT",
            },
            {
                "symbol": "XRPUSDT",
                "status": "BREAK",
                "baseAsset": "XRP",
                "quoteAsset": "USDT",
            },
            {
                "symbol": "DOGEUSDT",
                "status": "TRADING",
                "baseAsset": "DOGE",
                "quoteAsset": "USDT",
            },
        ]
    }

    monkeypatch.setattr(
        exchange,
        "_get",
        lambda endpoint, params=None: exchange_info,
    )

    symbols = exchange.get_symbols()

    assert symbols == [
        Symbol.BTC_USDT,
        Symbol.ETH_USDT,
    ]


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health_check_success(monkeypatch):
    exchange = BinanceExchange()

    def fake_get(endpoint, params=None):
        assert endpoint == "/api/v3/ping"
        return {}

    monkeypatch.setattr(
        exchange,
        "_get",
        fake_get,
    )

    assert exchange.health_check() is True


def test_health_check_failure(monkeypatch):
    exchange = BinanceExchange()

    def fake_get(endpoint, params=None):
        raise requests.RequestException(
            "Network error"
        )

    monkeypatch.setattr(
        exchange,
        "_get",
        fake_get,
    )

    assert exchange.health_check() is False


# ---------------------------------------------------------------------------
# Request construction
# ---------------------------------------------------------------------------


def test_get_ohlcv_passes_correct_request(monkeypatch):
    exchange = BinanceExchange()

    captured = {}

    def fake_get(endpoint, params=None):
        captured["endpoint"] = endpoint
        captured["params"] = params
        return []

    monkeypatch.setattr(
        exchange,
        "_get",
        fake_get,
    )

    exchange.get_ohlcv(
        symbol=Symbol.SOL_USDT,
        timeframe=Timeframe.FOUR_HOURS,
        limit=50,
    )

    assert captured["endpoint"] == "/api/v3/klines"

    assert captured["params"] == {
        "symbol": "SOLUSDT",
        "interval": "4h",
        "limit": 50,
    }


# ---------------------------------------------------------------------------
# HTTP / API error handling
# ---------------------------------------------------------------------------


def test_get_rejects_binance_api_error(monkeypatch):
    exchange = BinanceExchange()

    response = FakeResponse(
        {
            "code": -1121,
            "msg": "Invalid symbol.",
        }
    )

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: response,
    )

    with pytest.raises(
        RuntimeError,
        match="Invalid symbol",
    ):
        exchange._get(
            "/api/v3/klines",
            params={
                "symbol": "INVALID",
                "interval": "15m",
                "limit": 1,
            },
        )


def test_get_rejects_invalid_json(monkeypatch):
    exchange = BinanceExchange()

    class InvalidJsonResponse:
        def raise_for_status(self):
            pass

        def json(self):
            raise ValueError("invalid json")

    monkeypatch.setattr(
        requests,
        "get",
        lambda *args, **kwargs: InvalidJsonResponse(),
    )

    with pytest.raises(
        RuntimeError,
        match="invalid JSON",
    ):
        exchange._get("/api/v3/ping")


# ---------------------------------------------------------------------------
# Configuration validation
# ---------------------------------------------------------------------------


def test_binance_timeout_must_be_positive():
    with pytest.raises(
        ValueError,
        match="timeout must be greater than zero",
    ):
        BinanceExchange(timeout=0)


def test_binance_negative_timeout_is_rejected():
    with pytest.raises(
        ValueError,
        match="timeout must be greater than zero",
    ):
        BinanceExchange(timeout=-1)