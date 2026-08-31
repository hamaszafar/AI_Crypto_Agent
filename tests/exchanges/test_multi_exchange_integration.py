import pytest

from app.exchanges.factory import ExchangeFactory
from app.exchanges.base import BaseExchange
from app.exchanges.binance_exchange import BinanceExchange
from app.exchanges.bybit_exchange import BybitExchange
from app.exchanges.bitget_exchange import BitgetExchange
from app.exchanges.okx_exchange import OKXExchange
from app.exchanges.kraken_exchange import KrakenExchange
from app.exchanges.coinbase_exchange import CoinbaseExchange


EXPECTED_EXCHANGES = {
    "binance": BinanceExchange,
    "bybit": BybitExchange,
    "bitget": BitgetExchange,
    "okx": OKXExchange,
    "kraken": KrakenExchange,
    "coinbase": CoinbaseExchange,
}


def test_all_exchanges_are_registered():
    available = set(
        ExchangeFactory.available_exchanges()
    )

    for name in EXPECTED_EXCHANGES:
        assert name in available


@pytest.mark.parametrize(
    "exchange_name, expected_class",
    EXPECTED_EXCHANGES.items(),
)
def test_factory_creates_correct_exchange(
    exchange_name,
    expected_class,
):
    exchange = ExchangeFactory.create(
        exchange_name
    )

    assert isinstance(
        exchange,
        expected_class,
    )

    assert isinstance(
        exchange,
        BaseExchange,
    )


@pytest.mark.parametrize(
    "exchange_name",
    EXPECTED_EXCHANGES.keys(),
)
def test_exchange_name_matches_registry(
    exchange_name,
):
    exchange = ExchangeFactory.create(
        exchange_name
    )

    assert exchange.name == exchange_name


def test_factory_is_case_insensitive():
    assert isinstance(
        ExchangeFactory.create("BINANCE"),
        BinanceExchange,
    )

    assert isinstance(
        ExchangeFactory.create("ByBit"),
        BybitExchange,
    )

    assert isinstance(
        ExchangeFactory.create("OKX"),
        OKXExchange,
    )

    assert isinstance(
        ExchangeFactory.create("KrAkEn"),
        KrakenExchange,
    )

    assert isinstance(
        ExchangeFactory.create("CoInBaSe"),
        CoinbaseExchange,
    )


def test_factory_rejects_unknown_exchange():
    with pytest.raises(ValueError):
        ExchangeFactory.create(
            "unknown_exchange"
        )


@pytest.mark.parametrize(
    "exchange_name",
    EXPECTED_EXCHANGES.keys(),
)
def test_exchange_has_common_interface(
    exchange_name,
):
    exchange = ExchangeFactory.create(
        exchange_name
    )

    assert hasattr(exchange, "name")
    assert callable(exchange.get_symbols)
    assert callable(exchange.get_ohlcv)
    assert callable(exchange.get_latest_candle)
    assert callable(exchange.health_check)


@pytest.mark.parametrize(
    "exchange_name",
    EXPECTED_EXCHANGES.keys(),
)
def test_exchange_has_required_methods(
    exchange_name,
):
    exchange = ExchangeFactory.create(
        exchange_name
    )

    assert callable(exchange.get_symbols)
    assert callable(exchange.get_ohlcv)
    assert callable(exchange.get_latest_candle)
    assert callable(exchange.health_check)


def test_available_exchanges_are_unique():
    available = ExchangeFactory.available_exchanges()

    assert len(available) == len(
        set(available)
    )


def test_required_exchanges_are_present():
    available = set(
        ExchangeFactory.available_exchanges()
    )

    required = {
        "binance",
        "bybit",
        "bitget",
        "okx",
        "kraken",
        "coinbase",
    }

    assert required.issubset(available)