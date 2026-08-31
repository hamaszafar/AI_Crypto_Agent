from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
import requests

from app.exchanges.kraken_exchange import KrakenExchange
from app.exchanges.types import Symbol, Timeframe


# ================================================================
# HELPERS
# ================================================================


@pytest.fixture
def exchange() -> KrakenExchange:
    return KrakenExchange()


@pytest.fixture
def candle_data() -> list:
    return [
        "1725000000",
        "60000.00",
        "60500.00",
        "59500.00",
        "60200.00",
        "60050.00",
        "12.500",
        "100",
    ]


@pytest.fixture
def kraken_ohlc_response(candle_data) -> dict:
    return {
        "error": [],
        "result": {
            "XXBTZUSDT": [
                candle_data,
            ],
            "last": 1725000000,
        },
    }


# ================================================================
# BASIC PROPERTIES
# ================================================================


def test_name(exchange):
    assert exchange.name == "kraken"


def test_timeout_must_be_positive():
    exchange = KrakenExchange(timeout=5)

    assert exchange.timeout == 5


def test_zero_timeout_is_rejected():
    with pytest.raises(
        ValueError,
        match="timeout must be greater than zero",
    ):
        KrakenExchange(timeout=0)


def test_negative_timeout_is_rejected():
    with pytest.raises(
        ValueError,
        match="timeout must be greater than zero",
    ):
        KrakenExchange(timeout=-1)


# ================================================================
# SYMBOL MAPPING
# ================================================================


def test_symbol_mapping():
    assert (
        KrakenExchange._to_kraken_symbol(
            Symbol.BTC_USDT
        )
        == "XBTUSDT"
    )


def test_eth_symbol_mapping():
    assert (
        KrakenExchange._to_kraken_symbol(
            Symbol.ETH_USDT
        )
        == "ETHUSDT"
    )


# ================================================================
# TIMEFRAME MAPPING
# ================================================================


def test_fifteen_minute_timeframe_mapping():
    assert (
        KrakenExchange._to_kraken_timeframe(
            Timeframe.FIFTEEN_MINUTES
        )
        == 15
    )


def test_one_hour_timeframe_mapping():
    assert (
        KrakenExchange._to_kraken_timeframe(
            Timeframe.ONE_HOUR
        )
        == 60
    )


def test_four_hour_timeframe_mapping():
    assert (
        KrakenExchange._to_kraken_timeframe(
            Timeframe.FOUR_HOURS
        )
        == 240
    )


def test_one_day_timeframe_mapping():
    assert (
        KrakenExchange._to_kraken_timeframe(
            Timeframe.ONE_DAY
        )
        == 1440
    )


# ================================================================
# TIMESTAMP
# ================================================================


def test_timestamp_conversion():
    value = datetime(
        2024,
        8,
        30,
        12,
        0,
        tzinfo=timezone.utc,
    )

    timestamp = KrakenExchange._to_timestamp_seconds(
        value
    )

    assert timestamp == 1725019200


def test_naive_datetime_is_treated_as_utc():
    value = datetime(
        2024,
        8,
        30,
        12,
        0,
    )

    timestamp = KrakenExchange._to_timestamp_seconds(
        value
    )

    assert timestamp == 1725019200


# ================================================================
# CANDLE PARSING
# ================================================================


def test_parse_candle(candle_data):
    candle = KrakenExchange._parse_candle(
        data=candle_data,
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert candle.exchange == "kraken"
    assert candle.symbol == Symbol.BTC_USDT
    assert candle.timeframe == Timeframe.FIFTEEN_MINUTES

    assert candle.timestamp == datetime(
        2024,
        8,
        30,
        6,
        40,
        tzinfo=timezone.utc,
    )

    assert candle.open == Decimal("60000.00")
    assert candle.high == Decimal("60500.00")
    assert candle.low == Decimal("59500.00")
    assert candle.close == Decimal("60200.00")
    assert candle.volume == Decimal("12.500")


def test_parse_candle_requires_seven_fields():
    data = [
        "1725000000",
        "60000",
        "60500",
        "59500",
        "60200",
        "60050",
    ]

    with pytest.raises(
        ValueError,
        match="fewer than 7",
    ):
        KrakenExchange._parse_candle(
            data=data,
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )


def test_parse_candle_rejects_invalid_timestamp(
    candle_data,
):
    candle_data[0] = "invalid"

    with pytest.raises(
        ValueError,
        match="Invalid candle timestamp",
    ):
        KrakenExchange._parse_candle(
            data=candle_data,
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )


def test_parse_candle_rejects_boolean_timestamp():
    data = [
        True,
        "60000",
        "60500",
        "59500",
        "60200",
        "60050",
        "12",
    ]

    with pytest.raises(
        ValueError,
        match="Invalid candle timestamp",
    ):
        KrakenExchange._parse_candle(
            data=data,
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )


def test_parse_candle_rejects_invalid_values(
    candle_data,
):
    candle_data[1] = "invalid"

    with pytest.raises(
        ValueError,
        match="Invalid Kraken candle values",
    ):
        KrakenExchange._parse_candle(
            data=candle_data,
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )


def test_parse_candle_rejects_non_list():
    with pytest.raises(
        ValueError,
        match="must be a list",
    ):
        KrakenExchange._parse_candle(
            data={},
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )


# ================================================================
# OHLCV VALIDATION
# ================================================================


def test_invalid_negative_volume(candle_data):
    candle_data[6] = "-1"

    with pytest.raises(
        ValueError,
        match="Volume cannot be negative",
    ):
        KrakenExchange._parse_candle(
            data=candle_data,
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )


def test_zero_open_is_rejected(candle_data):
    candle_data[1] = "0"

    with pytest.raises(
        ValueError,
        match="Open price must be positive",
    ):
        KrakenExchange._parse_candle(
            data=candle_data,
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )


def test_high_cannot_be_below_open(candle_data):
    candle_data[2] = "59000"

    with pytest.raises(
        ValueError,
        match="High price cannot be below",
    ):
        KrakenExchange._parse_candle(
            data=candle_data,
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )


def test_low_cannot_be_above_close(candle_data):
    candle_data[3] = "60300"

    with pytest.raises(
        ValueError,
        match="Low price cannot be above",
    ):
        KrakenExchange._parse_candle(
            data=candle_data,
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )


# ================================================================
# HTTP / API
# ================================================================


@patch("app.exchanges.kraken_exchange.requests.request")
def test_get_rejects_kraken_api_error(
    mock_request,
    exchange,
):
    response = Mock()

    response.raise_for_status.return_value = None

    response.json.return_value = {
        "error": [
            "EGeneral:Invalid arguments",
        ],
        "result": {},
    }

    mock_request.return_value = response

    with pytest.raises(
        RuntimeError,
        match="Kraken API error",
    ):
        exchange._get(
            exchange.KLINE_ENDPOINT,
        )


@patch("app.exchanges.kraken_exchange.requests.request")
def test_get_rejects_invalid_json(
    mock_request,
    exchange,
):
    response = Mock()

    response.raise_for_status.return_value = None

    response.json.side_effect = ValueError(
        "invalid json"
    )

    mock_request.return_value = response

    with pytest.raises(
        RuntimeError,
        match="invalid JSON",
    ):
        exchange._get(
            exchange.KLINE_ENDPOINT,
        )


@patch("app.exchanges.kraken_exchange.requests.request")
def test_get_rejects_non_dict_response(
    mock_request,
    exchange,
):
    response = Mock()

    response.raise_for_status.return_value = None
    response.json.return_value = []

    mock_request.return_value = response

    with pytest.raises(
        RuntimeError,
        match="Invalid Kraken API response",
    ):
        exchange._get(
            exchange.KLINE_ENDPOINT,
        )


@patch("app.exchanges.kraken_exchange.requests.request")
def test_get_propagates_http_error(
    mock_request,
    exchange,
):
    mock_request.side_effect = requests.RequestException(
        "network error"
    )

    with pytest.raises(
        requests.RequestException,
    ):
        exchange._get(
            exchange.KLINE_ENDPOINT,
        )


# ================================================================
# GET SYMBOLS
# ================================================================


@patch.object(KrakenExchange, "_get")
def test_get_symbols_returns_supported_symbols(
    mock_get,
    exchange,
):
    mock_get.return_value = {
        "error": [],
        "result": {
            "XBTUSDT": {
                "altname": "XBTUSDT",
                "wsname": "XBT/USDT",
            },
            "ETHUSDT": {
                "altname": "ETHUSDT",
                "wsname": "ETH/USDT",
            },
        },
    }

    symbols = exchange.get_symbols()

    assert Symbol.BTC_USDT in symbols
    assert Symbol.ETH_USDT in symbols


@patch.object(KrakenExchange, "_get")
def test_get_symbols_ignores_non_trading_symbols(
    mock_get,
    exchange,
):
    mock_get.return_value = {
        "error": [],
        "result": {
            "UNKNOWN": {
                "altname": "UNKNOWN",
                "wsname": "UNKNOWN/PAIR",
            },
            "XBTUSDT": {
                "altname": "XBTUSDT",
                "wsname": "XBT/USDT",
            },
        },
    }

    symbols = exchange.get_symbols()

    assert Symbol.BTC_USDT in symbols
    assert len(symbols) == 1


@patch.object(KrakenExchange, "_get")
def test_get_symbols_rejects_invalid_result(
    mock_get,
    exchange,
):
    mock_get.return_value = {
        "error": [],
        "result": [],
    }

    with pytest.raises(
        RuntimeError,
        match="Invalid Kraken AssetPairs response",
    ):
        exchange.get_symbols()


# ================================================================
# GET OHLCV
# ================================================================


@patch.object(KrakenExchange, "_get")
def test_get_ohlcv_passes_correct_request(
    mock_get,
    exchange,
    candle_data,
):
    mock_get.return_value = {
        "error": [],
        "result": {
            "XXBTZUSDT": [
                candle_data,
            ],
            "last": 1725000000,
        },
    }

    result = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        limit=100,
    )

    assert len(result) == 1

    mock_get.assert_called_once()

    args, kwargs = mock_get.call_args

    assert args[0] == exchange.KLINE_ENDPOINT

    assert kwargs["params"]["pair"] == "XBTUSDT"
    assert kwargs["params"]["interval"] == 15


@patch.object(KrakenExchange, "_get")
def test_get_ohlcv_with_start_time(
    mock_get,
    exchange,
    candle_data,
):
    mock_get.return_value = {
        "error": [],
        "result": {
            "XXBTZUSDT": [
                candle_data,
            ],
            "last": 1725000000,
        },
    }

    start_time = datetime(
        2024,
        8,
        30,
        13,
        0,
        tzinfo=timezone.utc,
    )

    exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        start_time=start_time,
    )

    _, kwargs = mock_get.call_args

    assert kwargs["params"]["since"] == int(
    start_time.timestamp()
    )


@patch.object(KrakenExchange, "_get")
def test_get_ohlcv_returns_chronological_order(
    mock_get,
    exchange,
):
    mock_get.return_value = {
        "error": [],
        "result": {
            "XXBTZUSDT": [
                [
                    "1725000900",
                    "60000",
                    "60500",
                    "59500",
                    "60200",
                    "60050",
                    "12",
                    "100",
                ],
                [
                    "1725000000",
                    "59000",
                    "60000",
                    "58500",
                    "59800",
                    "59500",
                    "10",
                    "100",
                ],
            ],
            "last": 1725000900,
        },
    }

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert candles[0].timestamp < candles[1].timestamp


@patch.object(KrakenExchange, "_get")
def test_get_ohlcv_removes_duplicates(
    mock_get,
    exchange,
    candle_data,
):
    mock_get.return_value = {
        "error": [],
        "result": {
            "XXBTZUSDT": [
                candle_data,
                candle_data.copy(),
            ],
            "last": 1725000000,
        },
    }

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert len(candles) == 1


@patch.object(KrakenExchange, "_get")
def test_get_ohlcv_empty_response(
    mock_get,
    exchange,
):
    mock_get.return_value = {
        "error": [],
        "result": {
            "XXBTZUSDT": [],
            "last": 1725000000,
        },
    }

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert candles == []


@patch.object(KrakenExchange, "_get")
def test_get_ohlcv_missing_pair_returns_empty(
    mock_get,
    exchange,
):
    mock_get.return_value = {
        "error": [],
        "result": {
            "last": 1725000000,
        },
    }

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert candles == []


def test_get_ohlcv_rejects_invalid_limit(exchange):
    with pytest.raises(
        ValueError,
        match="limit must be between",
    ):
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
            limit=0,
        )


def test_get_ohlcv_rejects_limit_above_max(exchange):
    with pytest.raises(
        ValueError,
        match="limit must be between",
    ):
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
            limit=721,
        )


def test_get_ohlcv_rejects_invalid_time_range(
    exchange,
):
    start_time = datetime(
        2024,
        8,
        31,
        tzinfo=timezone.utc,
    )

    end_time = datetime(
        2024,
        8,
        30,
        tzinfo=timezone.utc,
    )

    with pytest.raises(
        ValueError,
        match="start_time cannot be later",
    ):
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
            start_time=start_time,
            end_time=end_time,
        )


@patch.object(KrakenExchange, "_get")
def test_get_ohlcv_rejects_malformed_candle(
    mock_get,
    exchange,
):
    mock_get.return_value = {
        "error": [],
        "result": {
            "XXBTZUSDT": [
                [
                    "invalid",
                    "60000",
                    "60500",
                    "59500",
                    "60200",
                    "60050",
                    "12",
                ],
            ],
            "last": 1725000000,
        },
    }

    with pytest.raises(
        RuntimeError,
        match="Malformed Kraken candle",
    ):
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )


# ================================================================
# LATEST CANDLE
# ================================================================


@patch.object(KrakenExchange, "get_ohlcv")
def test_get_latest_candle(
    mock_get_ohlcv,
    exchange,
):
    expected = Mock()

    mock_get_ohlcv.return_value = [
        expected,
    ]

    result = exchange.get_latest_candle(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert result is expected

    mock_get_ohlcv.assert_called_once_with(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        limit=1,
    )


@patch.object(KrakenExchange, "get_ohlcv")
def test_get_latest_candle_returns_none(
    mock_get_ohlcv,
    exchange,
):
    mock_get_ohlcv.return_value = []

    result = exchange.get_latest_candle(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert result is None


# ================================================================
# HEALTH CHECK
# ================================================================


@patch.object(KrakenExchange, "_get")
def test_health_check_success(
    mock_get,
    exchange,
):
    mock_get.return_value = {
        "error": [],
        "result": {
            "unixtime": 1725000000,
            "rfc1123": "Fri, 30 Aug 2024 13:20:00 GMT",
        },
    }

    assert exchange.health_check() is True

    mock_get.assert_called_once_with(
        exchange.SERVER_TIME_ENDPOINT,
    )


@patch.object(KrakenExchange, "_get")
def test_health_check_failure(
    mock_get,
    exchange,
):
    mock_get.side_effect = RuntimeError(
        "Kraken unavailable"
    )

    assert exchange.health_check() is False