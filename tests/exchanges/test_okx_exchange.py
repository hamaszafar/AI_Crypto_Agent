from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import Mock

import pytest

from app.exchanges.okx_exchange import OKXExchange
from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe


def test_okx_exchange_name():
    exchange = OKXExchange()

    assert exchange.name == "okx"


def test_okx_symbol_conversion():
    exchange = OKXExchange()

    assert (
        exchange._convert_symbol(Symbol.BTC_USDT)
        == "BTC-USDT"
    )

    assert (
        exchange._convert_symbol(Symbol.ETH_USDT)
        == "ETH-USDT"
    )

    assert (
        exchange._convert_symbol(Symbol.SOL_USDT)
        == "SOL-USDT"
    )


def test_okx_timeframe_conversion():
    exchange = OKXExchange()

    assert (
        exchange._convert_timeframe(
            Timeframe.FIFTEEN_MINUTES
        )
        == "15m"
    )

    assert (
        exchange._convert_timeframe(
            Timeframe.ONE_HOUR
        )
        == "1H"
    )

    assert (
        exchange._convert_timeframe(
            Timeframe.FOUR_HOURS
        )
        == "4H"
    )

    assert (
        exchange._convert_timeframe(
            Timeframe.ONE_DAY
        )
        == "1D"
    )


def test_okx_timestamp_conversion():
    value = datetime(
        2026,
        8,
        22,
        0,
        0,
        tzinfo=timezone.utc,
    )

    timestamp = OKXExchange._to_timestamp_ms(value)

    assert timestamp == 1787356800000


def test_parse_okx_candle():
    exchange = OKXExchange()

    row = [
        "1787356800000",
        "77000.00",
        "77500.00",
        "76500.00",
        "77200.00",
        "123.456",
        "123.456",
        "9500000",
        "1",
    ]

    candle = exchange._parse_okx_candle(
        row=row,
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
    )

    assert isinstance(candle, Candle)

    assert candle.exchange == "okx"
    assert candle.symbol == Symbol.BTC_USDT
    assert candle.timeframe == Timeframe.FIFTEEN_MINUTES

    assert candle.open == Decimal("77000.00")
    assert candle.high == Decimal("77500.00")
    assert candle.low == Decimal("76500.00")
    assert candle.close == Decimal("77200.00")
    assert candle.volume == Decimal("123.456")


def test_get_ohlcv():
    exchange = OKXExchange()

    response = Mock()

    response.json.return_value = {
        "code": "0",
        "msg": "",
        "data": [
            [
                "1787357700000",
                "77200",
                "77600",
                "77100",
                "77400",
                "120",
                "120",
                "9288000",
                "1",
            ],
            [
                "1787356800000",
                "77000",
                "77500",
                "76500",
                "77200",
                "100",
                "100",
                "7720000",
                "1",
            ],
        ],
    }

    response.raise_for_status.return_value = None

    exchange.session.get = Mock(
        return_value=response
    )

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        limit=2,
    )

    assert len(candles) == 2

    assert candles[0].exchange == "okx"
    assert candles[0].symbol == Symbol.BTC_USDT

    assert candles[0].close == Decimal("77200")
    assert candles[1].close == Decimal("77400")

    assert (
        candles[0].timestamp
        < candles[1].timestamp
    )


def test_get_ohlcv_with_time_range():
    exchange = OKXExchange()

    response = Mock()

    response.json.return_value = {
        "code": "0",
        "msg": "",
        "data": [],
    }

    response.raise_for_status.return_value = None

    exchange.session.get = Mock(
        return_value=response
    )

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
        limit=50,
    )

    request_kwargs = (
        exchange.session.get.call_args.kwargs
    )

    params = request_kwargs["params"]

    assert params["instId"] == "BTC-USDT"
    assert params["bar"] == "15m"
    assert params["limit"] == "50"
    assert params["after"] == str(
        OKXExchange._to_timestamp_ms(start_time)
    )
    assert params["before"] == str(
        OKXExchange._to_timestamp_ms(end_time)
    )


def test_get_ohlcv_rejects_invalid_limit():
    exchange = OKXExchange()

    with pytest.raises(ValueError):
        exchange.get_ohlcv(
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
            limit=101,
        )


def test_get_ohlcv_zero_limit_returns_empty():
    exchange = OKXExchange()

    candles = exchange.get_ohlcv(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        limit=0,
    )

    assert candles == []


def test_get_latest_candle():
    exchange = OKXExchange()

    candle = Candle(
        exchange="okx",
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.ONE_HOUR,
        timestamp=datetime(
            2026,
            8,
            22,
            tzinfo=timezone.utc,
        ),
        open=Decimal("77000"),
        high=Decimal("77500"),
        low=Decimal("76500"),
        close=Decimal("77200"),
        volume=Decimal("100"),
    )

    exchange.get_ohlcv = Mock(
        return_value=[candle]
    )

    latest = exchange.get_latest_candle(
        Symbol.BTC_USDT,
        Timeframe.ONE_HOUR,
    )

    assert latest is not None
    assert latest.exchange == "okx"
    assert latest.close == Decimal("77200")


def test_get_latest_candle_returns_none_when_empty():
    exchange = OKXExchange()

    exchange.get_ohlcv = Mock(
        return_value=[]
    )

    latest = exchange.get_latest_candle(
        Symbol.BTC_USDT,
        Timeframe.ONE_HOUR,
    )

    assert latest is None


def test_get_symbols():
    exchange = OKXExchange()

    assert exchange.get_symbols() == list(Symbol)


def test_health_check_success():
    exchange = OKXExchange()

    response = Mock()

    response.json.return_value = {
        "code": "0",
        "msg": "",
        "data": [
            {
                "ts": "1787356800000"
            }
        ],
    }

    response.raise_for_status.return_value = None

    exchange.session.get = Mock(
        return_value=response
    )

    assert exchange.health_check() is True


def test_health_check_failure():
    exchange = OKXExchange()

    exchange.session.get = Mock(
        side_effect=Exception("connection failed")
    )

    assert exchange.health_check() is False