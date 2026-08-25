from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock

import pytest

from app.exchanges.bitget_exchange import BitgetExchange
from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe


def make_response(data):
    response = Mock()
    response.json.return_value = data
    response.raise_for_status.return_value = None
    return response


def test_bitget_exchange_name():
    exchange = BitgetExchange()

    assert exchange.name == "bitget"


def test_bitget_symbol_conversion():
    assert (
        BitgetExchange._to_bitget_symbol(Symbol.BTC_USDT)
        == "BTCUSDT"
    )


def test_bitget_timeframe_conversion():
    assert (
        BitgetExchange._to_bitget_timeframe(
            Timeframe.FIFTEEN_MINUTES
        )
        == "15min"
    )

    assert (
        BitgetExchange._to_bitget_timeframe(
            Timeframe.ONE_HOUR
        )
        == "1h"
    )

    assert (
        BitgetExchange._to_bitget_timeframe(
            Timeframe.FOUR_HOURS
        )
        == "4h"
    )

    assert (
        BitgetExchange._to_bitget_timeframe(
            Timeframe.ONE_DAY
        )
        == "1day"
    )


def test_bitget_timestamp_conversion():
    timestamp = BitgetExchange._timestamp_to_datetime(
        "1787356800000"
    )

    assert timestamp == datetime(
        2026,
        8,
        22,
        0,
        0,
        tzinfo=timezone.utc,
    )


def test_parse_bitget_candle():
    row = [
        "1787356800000",
        "77000.00",
        "77500.00",
        "76500.00",
        "77200.00",
        "123.45",
        "9523456.78",
    ]

    candle = BitgetExchange._parse_bitget_candle(
        row=row,
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert isinstance(candle, Candle)
    assert candle.exchange == "bitget"
    assert candle.symbol == Symbol.BTC_USDT
    assert candle.timeframe == Timeframe.FIFTEEN_MINUTES

    assert candle.open == Decimal("77000.00")
    assert candle.high == Decimal("77500.00")
    assert candle.low == Decimal("76500.00")
    assert candle.close == Decimal("77200.00")
    assert candle.volume == Decimal("123.45")


def test_get_ohlcv():
    session = Mock()

    session.get.return_value = make_response(
        {
            "code": "00000",
            "data": [
                [
                    "1787356800000",
                    "77000",
                    "77500",
                    "76500",
                    "77200",
                    "123.45",
                    "9523456.78",
                ]
            ],
        }
    )

    exchange = BitgetExchange(session=session)

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        limit=10,
    )

    assert len(candles) == 1
    assert isinstance(candles[0], Candle)
    assert candles[0].symbol == Symbol.BTC_USDT


def test_get_ohlcv_with_time_range():
    session = Mock()

    session.get.return_value = make_response(
        {
            "code": "00000",
            "data": [],
        }
    )

    exchange = BitgetExchange(session=session)

    start_time = datetime(
        2026,
        8,
        22,
        0,
        0,
        tzinfo=timezone.utc,
    )

    end_time = datetime(
        2026,
        8,
        22,
        2,
        0,
        tzinfo=timezone.utc,
    )

    exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        start_time=start_time,
        end_time=end_time,
        limit=100,
    )

    kwargs = session.get.call_args.kwargs

    assert kwargs["params"]["startTime"] == int(
        start_time.timestamp() * 1000
    )

    assert kwargs["params"]["endTime"] == int(
        end_time.timestamp() * 1000
    )


def test_get_ohlcv_rejects_invalid_limit():
    exchange = BitgetExchange()

    with pytest.raises(ValueError):
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
            limit=1001,
        )


def test_get_ohlcv_zero_limit():
    exchange = BitgetExchange()

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        limit=0,
    )

    assert candles == []


def test_get_latest_candle():
    session = Mock()

    session.get.return_value = make_response(
        {
            "code": "00000",
            "data": [
                [
                    "1787356800000",
                    "77000",
                    "77500",
                    "76500",
                    "77200",
                    "123.45",
                    "9523456.78",
                ]
            ],
        }
    )

    exchange = BitgetExchange(session=session)

    candle = exchange.get_latest_candle(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert candle is not None
    assert candle.exchange == "bitget"


def test_get_latest_candle_returns_none_when_empty():
    session = Mock()

    session.get.return_value = make_response(
        {
            "code": "00000",
            "data": [],
        }
    )

    exchange = BitgetExchange(session=session)

    candle = exchange.get_latest_candle(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert candle is None


def test_get_symbols():
    exchange = BitgetExchange()

    symbols = exchange.get_symbols()

    assert symbols == list(Symbol)


def test_health_check_success():
    session = Mock()

    session.get.return_value = make_response(
        {
            "code": "00000",
            "data": {
                "serverTime": "1787356800000"
            },
        }
    )

    exchange = BitgetExchange(session=session)

    assert exchange.health_check() is True


def test_health_check_failure():
    session = Mock()

    session.get.side_effect = Exception(
        "connection failed"
    )

    exchange = BitgetExchange(session=session)

    assert exchange.health_check() is False


def test_get_ohlcv_passes_correct_request():
    session = Mock()

    session.get.return_value = make_response(
        {
            "code": "00000",
            "data": [],
        }
    )

    exchange = BitgetExchange(session=session)

    exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        limit=50,
    )

    session.get.assert_called_once()

    args, kwargs = session.get.call_args

    assert (
        args[0]
        == "https://api.bitget.com/api/v2/mix/market/candles"
    )

    assert kwargs["params"]["symbol"] == "BTCUSDT"
    assert kwargs["params"]["productType"] == "USDT-FUTURES"
    assert kwargs["params"]["granularity"] == "15min"
    assert kwargs["params"]["limit"] == 50
    assert kwargs["timeout"] == 10