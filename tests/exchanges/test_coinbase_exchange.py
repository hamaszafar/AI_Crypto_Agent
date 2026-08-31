from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.exchanges.coinbase_exchange import CoinbaseExchange
from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe


# ====================================================================
# FIXTURES
# ====================================================================


@pytest.fixture
def exchange():
    return CoinbaseExchange()


@pytest.fixture
def candle_data():
    return [
        1725024000,
        "59500.00",
        "60500.00",
        "60000.00",
        "60200.00",
        "12.500",
    ]


@pytest.fixture
def second_candle_data():
    return [
        1725024900,
        "60200.00",
        "61000.00",
        "60200.00",
        "60800.00",
        "10.250",
    ]


# ====================================================================
# BASIC PROPERTIES
# ====================================================================


def test_name(exchange):
    assert exchange.name == "coinbase"


def test_default_timeout(exchange):
    assert exchange.timeout == 10.0


def test_custom_timeout():
    exchange = CoinbaseExchange(timeout=25.0)

    assert exchange.timeout == 25.0


def test_timeout_must_be_positive():
    with pytest.raises(ValueError):
        CoinbaseExchange(timeout=0)


def test_zero_timeout_is_rejected():
    with pytest.raises(ValueError):
        CoinbaseExchange(timeout=0.0)


def test_negative_timeout_is_rejected():
    with pytest.raises(ValueError):
        CoinbaseExchange(timeout=-1)


# ====================================================================
# SYMBOL MAPPING
# ====================================================================


def test_symbol_mapping():
    assert (
        CoinbaseExchange._to_coinbase_symbol(
            Symbol.BTC_USDT
        )
        == "BTC-USDT"
    )


def test_eth_symbol_mapping():
    assert (
        CoinbaseExchange._to_coinbase_symbol(
            Symbol.ETH_USDT
        )
        == "ETH-USDT"
    )


# ====================================================================
# TIMEFRAME MAPPING
# ====================================================================


def test_fifteen_minute_timeframe_mapping():
    assert (
        CoinbaseExchange._to_coinbase_timeframe(
            Timeframe.FIFTEEN_MINUTES
        )
        == 900
    )


def test_one_hour_timeframe_mapping():
    assert (
        CoinbaseExchange._to_coinbase_timeframe(
            Timeframe.ONE_HOUR
        )
        == 3600
    )


def test_four_hour_timeframe_mapping():
    assert (
        CoinbaseExchange._to_coinbase_timeframe(
            Timeframe.FOUR_HOURS
        )
        == 14400
    )


def test_one_day_timeframe_mapping():
    assert (
        CoinbaseExchange._to_coinbase_timeframe(
            Timeframe.ONE_DAY
        )
        == 86400
    )


# ====================================================================
# TIMESTAMP
# ====================================================================


def test_timestamp_conversion():
    value = datetime(
        2024,
        8,
        30,
        13,
        20,
        tzinfo=timezone.utc,
    )

    result = CoinbaseExchange._to_iso_timestamp(
        value
    )

    assert result == "2024-08-30T13:20:00Z"


def test_naive_datetime_is_treated_as_utc():
    value = datetime(
        2024,
        8,
        30,
        13,
        20,
    )

    result = CoinbaseExchange._to_iso_timestamp(
        value
    )

    assert result == "2024-08-30T13:20:00Z"


def test_timezone_aware_datetime_is_converted_to_utc():
    value = datetime(
        2024,
        8,
        30,
        18,
        20,
        tzinfo=timezone.utc,
    )

    result = CoinbaseExchange._to_iso_timestamp(
        value
    )

    assert result == "2024-08-30T18:20:00Z"


# ====================================================================
# CANDLE PARSING
# ====================================================================


def test_parse_candle(candle_data):
    candle = CoinbaseExchange._parse_candle(
        data=candle_data,
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert isinstance(candle, Candle)

    assert candle.exchange == "coinbase"
    assert candle.symbol == Symbol.BTC_USDT
    assert candle.timeframe == Timeframe.FIFTEEN_MINUTES

    assert candle.timestamp == datetime(
        2024,
        8,
        30,
        13,
        20,
        tzinfo=timezone.utc,
    )

    assert candle.open == Decimal("60000.00")
    assert candle.high == Decimal("60500.00")
    assert candle.low == Decimal("59500.00")
    assert candle.close == Decimal("60200.00")
    assert candle.volume == Decimal("12.500")


def test_parse_candle_requires_six_fields():
    data = [
        1725024000,
        "59500.00",
        "60500.00",
        "60000.00",
        "60200.00",
    ]

    with pytest.raises(ValueError):
        CoinbaseExchange._parse_candle(
            data=data,
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )


def test_parse_candle_rejects_invalid_timestamp():
    data = [
        "invalid",
        "59500.00",
        "60500.00",
        "60000.00",
        "60200.00",
        "12.500",
    ]

    with pytest.raises(ValueError):
        CoinbaseExchange._parse_candle(
            data=data,
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )


def test_parse_candle_rejects_boolean_timestamp():
    data = [
        True,
        "59500.00",
        "60500.00",
        "60000.00",
        "60200.00",
        "12.500",
    ]

    with pytest.raises(ValueError):
        CoinbaseExchange._parse_candle(
            data=data,
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )


def test_parse_candle_rejects_invalid_values():
    data = [
        1725024000,
        "invalid",
        "60500.00",
        "60000.00",
        "60200.00",
        "12.500",
    ]

    with pytest.raises(ValueError):
        CoinbaseExchange._parse_candle(
            data=data,
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )


def test_parse_candle_rejects_non_list():
    with pytest.raises(ValueError):
        CoinbaseExchange._parse_candle(
            data="invalid",
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )


# ====================================================================
# OHLCV VALIDATION
# ====================================================================


def test_invalid_negative_volume():
    with pytest.raises(ValueError):
        CoinbaseExchange._validate_ohlcv(
            open_price=Decimal("100"),
            high_price=Decimal("110"),
            low_price=Decimal("90"),
            close_price=Decimal("105"),
            volume=Decimal("-1"),
        )


def test_zero_open_is_rejected():
    with pytest.raises(ValueError):
        CoinbaseExchange._validate_ohlcv(
            open_price=Decimal("0"),
            high_price=Decimal("110"),
            low_price=Decimal("90"),
            close_price=Decimal("105"),
            volume=Decimal("10"),
        )


def test_high_cannot_be_below_open():
    with pytest.raises(ValueError):
        CoinbaseExchange._validate_ohlcv(
            open_price=Decimal("110"),
            high_price=Decimal("100"),
            low_price=Decimal("90"),
            close_price=Decimal("105"),
            volume=Decimal("10"),
        )


def test_low_cannot_be_above_close():
    with pytest.raises(ValueError):
        CoinbaseExchange._validate_ohlcv(
            open_price=Decimal("100"),
            high_price=Decimal("120"),
            low_price=Decimal("110"),
            close_price=Decimal("105"),
            volume=Decimal("10"),
        )


def test_nan_value_is_rejected():
    with pytest.raises(ValueError):
        CoinbaseExchange._validate_ohlcv(
            open_price=Decimal("NaN"),
            high_price=Decimal("110"),
            low_price=Decimal("90"),
            close_price=Decimal("105"),
            volume=Decimal("10"),
        )


def test_infinite_value_is_rejected():
    with pytest.raises(ValueError):
        CoinbaseExchange._validate_ohlcv(
            open_price=Decimal("Infinity"),
            high_price=Decimal("110"),
            low_price=Decimal("90"),
            close_price=Decimal("105"),
            volume=Decimal("10"),
        )


def test_valid_ohlcv_is_accepted():
    CoinbaseExchange._validate_ohlcv(
        open_price=Decimal("100"),
        high_price=Decimal("120"),
        low_price=Decimal("90"),
        close_price=Decimal("110"),
        volume=Decimal("25"),
    )


# ====================================================================
# HTTP / _GET
# ====================================================================


@patch("app.exchanges.coinbase_exchange.requests.request")
def test_get_success(mock_request, exchange):
    response = MagicMock()

    response.raise_for_status.return_value = None

    response.json.return_value = {
        "server_time": "2024-08-30T13:20:00Z"
    }

    mock_request.return_value = response

    result = exchange._get(
        "/time"
    )

    assert result == {
        "server_time": "2024-08-30T13:20:00Z"
    }

    mock_request.assert_called_once()


@patch("app.exchanges.coinbase_exchange.requests.request")
def test_get_invalid_json(mock_request, exchange):
    response = MagicMock()

    response.raise_for_status.return_value = None

    response.json.side_effect = ValueError(
        "invalid json"
    )

    mock_request.return_value = response

    with pytest.raises(
        RuntimeError,
        match="Coinbase returned invalid JSON",
    ):
        exchange._get("/time")


@patch("app.exchanges.coinbase_exchange.requests.request")
def test_get_propagates_http_error(
    mock_request,
    exchange,
):
    response = MagicMock()

    response.raise_for_status.side_effect = (
        requests.HTTPError("500")
    )

    mock_request.return_value = response

    with pytest.raises(requests.HTTPError):
        exchange._get("/time")


@patch("app.exchanges.coinbase_exchange.requests.request")
def test_get_propagates_request_exception(
    mock_request,
    exchange,
):
    mock_request.side_effect = (
        requests.ConnectionError("connection failed")
    )

    with pytest.raises(requests.ConnectionError):
        exchange._get("/time")


# ====================================================================
# GET SYMBOLS
# ====================================================================


@patch.object(CoinbaseExchange, "_get")
def test_get_symbols_returns_supported_symbols(
    mock_get,
    exchange,
):
    mock_get.return_value = [
        {
            "id": "BTC-USDT",
            "base_currency": "BTC",
            "quote_currency": "USDT",
        },
        {
            "id": "ETH-USDT",
            "base_currency": "ETH",
            "quote_currency": "USDT",
        },
        {
            "id": "DOGE-USDT",
            "base_currency": "DOGE",
            "quote_currency": "USDT",
        },
    ]

    result = exchange.get_symbols()

    assert Symbol.BTC_USDT in result
    assert Symbol.ETH_USDT in result


@patch.object(CoinbaseExchange, "_get")
def test_get_symbols_ignores_unsupported_symbols(
    mock_get,
    exchange,
):
    mock_get.return_value = [
        {
            "id": "DOGE-USDT",
        },
        {
            "id": "UNKNOWN-PAIR",
        },
    ]

    result = exchange.get_symbols()

    assert result == []


@patch.object(CoinbaseExchange, "_get")
def test_get_symbols_ignores_malformed_items(
    mock_get,
    exchange,
):
    mock_get.return_value = [
        "invalid",
        None,
        {},
        {
            "id": "BTC-USDT",
        },
    ]

    result = exchange.get_symbols()

    assert Symbol.BTC_USDT in result


@patch.object(CoinbaseExchange, "_get")
def test_get_symbols_rejects_invalid_response(
    mock_get,
    exchange,
):
    mock_get.return_value = {
        "data": []
    }

    with pytest.raises(
        RuntimeError,
        match="Invalid Coinbase products response",
    ):
        exchange.get_symbols()


# ====================================================================
# GET OHLCV
# ====================================================================


@patch.object(CoinbaseExchange, "_get")
def test_get_ohlcv_passes_correct_request(
    mock_get,
    exchange,
    candle_data,
):
    mock_get.return_value = [
        candle_data
    ]

    exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        limit=100,
    )

    mock_get.assert_called_once()

    args, kwargs = mock_get.call_args

    assert (
        args[0]
        == "/products/BTC-USDT/candles"
    )

    assert kwargs["params"]["granularity"] == 900


@patch.object(CoinbaseExchange, "_get")
def test_get_ohlcv_with_start_time(
    mock_get,
    exchange,
    candle_data,
):
    mock_get.return_value = [
        candle_data
    ]

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

    assert (
        kwargs["params"]["start"]
        == "2024-08-30T13:00:00Z"
    )


@patch.object(CoinbaseExchange, "_get")
def test_get_ohlcv_with_end_time(
    mock_get,
    exchange,
    candle_data,
):
    mock_get.return_value = [
        candle_data
    ]

    end_time = datetime(
        2024,
        8,
        30,
        14,
        0,
        tzinfo=timezone.utc,
    )

    exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        end_time=end_time,
    )

    _, kwargs = mock_get.call_args

    assert (
        kwargs["params"]["end"]
        == "2024-08-30T14:00:00Z"
    )


@patch.object(CoinbaseExchange, "_get")
def test_get_ohlcv_with_start_and_end_time(
    mock_get,
    exchange,
    candle_data,
):
    mock_get.return_value = [
        candle_data
    ]

    start_time = datetime(
        2024,
        8,
        30,
        13,
        0,
        tzinfo=timezone.utc,
    )

    end_time = datetime(
        2024,
        8,
        30,
        15,
        0,
        tzinfo=timezone.utc,
    )

    exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        start_time=start_time,
        end_time=end_time,
    )

    _, kwargs = mock_get.call_args

    assert (
        kwargs["params"]["start"]
        == "2024-08-30T13:00:00Z"
    )

    assert (
        kwargs["params"]["end"]
        == "2024-08-30T15:00:00Z"
    )


@patch.object(CoinbaseExchange, "_get")
def test_get_ohlcv_returns_chronological_order(
    mock_get,
    exchange,
    candle_data,
    second_candle_data,
):
    mock_get.return_value = [
        second_candle_data,
        candle_data,
    ]

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert len(candles) == 2

    assert (
        candles[0].timestamp
        < candles[1].timestamp
    )


@patch.object(CoinbaseExchange, "_get")
def test_get_ohlcv_removes_duplicates(
    mock_get,
    exchange,
    candle_data,
):
    mock_get.return_value = [
        candle_data,
        candle_data,
    ]

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert len(candles) == 1


@patch.object(CoinbaseExchange, "_get")
def test_get_ohlcv_empty_response(
    mock_get,
    exchange,
):
    mock_get.return_value = []

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert candles == []


@patch.object(CoinbaseExchange, "_get")
def test_get_ohlcv_none_response(
    mock_get,
    exchange,
):
    mock_get.return_value = None

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert candles == []


@patch.object(CoinbaseExchange, "_get")
def test_get_ohlcv_rejects_invalid_response(
    mock_get,
    exchange,
):
    mock_get.return_value = {
        "error": "invalid"
    }

    with pytest.raises(
        RuntimeError,
        match="Coinbase candle response must be a list",
    ):
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )


@patch.object(CoinbaseExchange, "_get")
def test_get_ohlcv_rejects_malformed_candle(
    mock_get,
    exchange,
):
    mock_get.return_value = [
        [
            1725024000,
            "59500.00",
        ]
    ]

    with pytest.raises(
        RuntimeError,
        match="Malformed Coinbase candle",
    ):
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
        )


# ====================================================================
# LIMIT VALIDATION
# ====================================================================


def test_get_ohlcv_rejects_invalid_limit(
    exchange,
):
    with pytest.raises(ValueError):
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
            limit=0,
        )


def test_get_ohlcv_rejects_limit_above_max(
    exchange,
):
    with pytest.raises(ValueError):
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
            limit=301,
        )


def test_get_ohlcv_accepts_max_limit(
    exchange,
):
    with patch.object(
        CoinbaseExchange,
        "_get",
        return_value=[],
    ):
        result = exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
            limit=300,
        )

    assert result == []


# ====================================================================
# TIME RANGE VALIDATION
# ====================================================================


def test_get_ohlcv_rejects_invalid_time_range(
    exchange,
):
    start_time = datetime(
        2024,
        8,
        30,
        15,
        0,
        tzinfo=timezone.utc,
    )

    end_time = datetime(
        2024,
        8,
        30,
        13,
        0,
        tzinfo=timezone.utc,
    )

    with pytest.raises(
        ValueError,
        match="start_time cannot be later than end_time",
    ):
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
            start_time=start_time,
            end_time=end_time,
        )


# ====================================================================
# GET LATEST CANDLE
# ====================================================================


@patch.object(CoinbaseExchange, "get_ohlcv")
def test_get_latest_candle(
    mock_get_ohlcv,
    exchange,
):
    candle = Candle(
        exchange="coinbase",
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        timestamp=datetime(
            2024,
            8,
            30,
            14,
            40,
            tzinfo=timezone.utc,
        ),
        open=Decimal("60000"),
        high=Decimal("60500"),
        low=Decimal("59500"),
        close=Decimal("60200"),
        volume=Decimal("12.5"),
    )

    mock_get_ohlcv.return_value = [
        candle
    ]

    result = exchange.get_latest_candle(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert result == candle

    mock_get_ohlcv.assert_called_once_with(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        limit=1,
    )


@patch.object(CoinbaseExchange, "get_ohlcv")
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


# ====================================================================
# HEALTH CHECK
# ====================================================================


@patch.object(CoinbaseExchange, "_get")
def test_health_check_success(
    mock_get,
    exchange,
):
    mock_get.return_value = {
        "iso": "2024-08-30T13:20:00Z",
        "epoch": 1725024000,
    }

    assert exchange.health_check() is True

    mock_get.assert_called_once_with(
        "/time"
    )


@patch.object(CoinbaseExchange, "_get")
def test_health_check_failure(
    mock_get,
    exchange,
):
    mock_get.side_effect = RuntimeError(
        "Coinbase unavailable"
    )

    assert exchange.health_check() is False


@patch.object(CoinbaseExchange, "_get")
def test_health_check_request_failure(
    mock_get,
    exchange,
):
    mock_get.side_effect = requests.RequestException(
        "connection failed"
    )

    assert exchange.health_check() is False