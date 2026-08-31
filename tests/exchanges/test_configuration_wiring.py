import pytest

from app.exchanges.config import (
    EXCHANGE_CONFIGS,
    get_exchange_config,
)

from app.exchanges.factory import ExchangeFactory


EXPECTED_EXCHANGES = {
    "binance",
    "bybit",
    "bitget",
    "okx",
    "kraken",
    "coinbase",
}


def test_all_production_exchanges_are_configured():
    assert set(EXCHANGE_CONFIGS.keys()) == EXPECTED_EXCHANGES


def test_all_configured_exchanges_are_registered():

    registered = set(
        ExchangeFactory.available_exchanges()
    )

    assert EXPECTED_EXCHANGES.issubset(registered)


@pytest.mark.parametrize(
    "exchange_name",
    sorted(EXPECTED_EXCHANGES),
)
def test_factory_uses_configuration(exchange_name):

    config = get_exchange_config(exchange_name)

    exchange = ExchangeFactory.create(exchange_name)

    assert exchange.name == config.name


@pytest.mark.parametrize(
    "exchange_name",
    sorted(EXPECTED_EXCHANGES),
)
def test_factory_is_case_insensitive(exchange_name):

    lower = ExchangeFactory.create(exchange_name)
    upper = ExchangeFactory.create(exchange_name.upper())

    assert lower.name == upper.name


def test_unknown_exchange_configuration_is_rejected():

    with pytest.raises(ValueError):
        ExchangeFactory.create("unknown_exchange")


def test_configuration_names_match_registered_implementations():

    configured = set(EXCHANGE_CONFIGS.keys())

    registered = set(
        ExchangeFactory.available_exchanges()
    )

    assert configured.issubset(registered)