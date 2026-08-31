import pytest

from app.exchanges.factory import ExchangeFactory
from app.exchanges.config import (
    EXCHANGE_CONFIGS,
    available_exchange_configs,
    get_exchange_config,
)


EXPECTED_EXCHANGES = {
    "binance",
    "bybit",
    "bitget",
    "okx",
    "kraken",
    "coinbase",
}


def test_all_expected_exchanges_are_configured():
    configured = set(available_exchange_configs())

    assert EXPECTED_EXCHANGES.issubset(configured)


@pytest.mark.parametrize(
    "exchange_name",
    sorted(EXPECTED_EXCHANGES),
)
def test_factory_creates_every_exchange(exchange_name):
    exchange = ExchangeFactory.create(exchange_name)

    assert exchange is not None


@pytest.mark.parametrize(
    "exchange_name",
    sorted(EXPECTED_EXCHANGES),
)
def test_exchange_name_matches_factory_name(exchange_name):
    exchange = ExchangeFactory.create(exchange_name)

    assert exchange.name == exchange_name


@pytest.mark.parametrize(
    "exchange_name",
    sorted(EXPECTED_EXCHANGES),
)
def test_rest_capability_is_enabled(exchange_name):
    config = get_exchange_config(exchange_name)

    assert config.capabilities.supports_rest is True


@pytest.mark.parametrize(
    "exchange_name",
    sorted(EXPECTED_EXCHANGES),
)
def test_historical_data_capability_is_enabled(exchange_name):
    config = get_exchange_config(exchange_name)

    assert config.capabilities.supports_historical_data is True


@pytest.mark.parametrize(
    "exchange_name",
    sorted(EXPECTED_EXCHANGES),
)
def test_incremental_data_capability_is_enabled(exchange_name):
    config = get_exchange_config(exchange_name)

    assert config.capabilities.supports_incremental_data is True


@pytest.mark.parametrize(
    "exchange_name",
    sorted(EXPECTED_EXCHANGES),
)
def test_supported_timeframes_are_present(exchange_name):
    config = get_exchange_config(exchange_name)

    assert "15m" in config.supported_timeframes
    assert "1h" in config.supported_timeframes
    assert "4h" in config.supported_timeframes
    assert "1d" in config.supported_timeframes


@pytest.mark.parametrize(
    "exchange_name",
    sorted(EXPECTED_EXCHANGES),
)
def test_exchange_config_has_valid_name(exchange_name):
    config = get_exchange_config(exchange_name)

    assert config.name == exchange_name


@pytest.mark.parametrize(
    "exchange_name",
    sorted(EXPECTED_EXCHANGES),
)
def test_exchange_config_has_rest_endpoint(exchange_name):
    config = get_exchange_config(exchange_name)

    assert config.rest_endpoint
    assert config.rest_endpoint.startswith("https://")


@pytest.mark.parametrize(
    "exchange_name",
    sorted(EXPECTED_EXCHANGES),
)
def test_exchange_config_has_positive_rate_limit(exchange_name):
    config = get_exchange_config(exchange_name)

    assert config.rate_limits.requests_per_minute > 0


def test_unknown_exchange_config_is_rejected():
    with pytest.raises(KeyError):
        get_exchange_config("unknown_exchange")


@pytest.mark.parametrize(
    "invalid_name",
    [
        "",
        "unknown",
        "does_not_exist",
        "BINANCE_UNKNOWN",
    ],
)
def test_invalid_exchange_config_names_are_rejected(invalid_name):
    with pytest.raises(KeyError):
        get_exchange_config(invalid_name)


def test_factory_and_configurations_have_common_exchanges():
    factory_exchanges = set(
        ExchangeFactory.available_exchanges()
    )

    configured_exchanges = set(
        available_exchange_configs()
    )

    assert EXPECTED_EXCHANGES.issubset(factory_exchanges)
    assert EXPECTED_EXCHANGES.issubset(configured_exchanges)


def test_factory_and_config_names_match():
    factory_exchanges = set(
        ExchangeFactory.available_exchanges()
    )

    configured_exchanges = set(
        available_exchange_configs()
    )

    common = EXPECTED_EXCHANGES

    assert common.issubset(factory_exchanges)
    assert common.issubset(configured_exchanges)


@pytest.mark.parametrize(
    "exchange_name",
    sorted(EXPECTED_EXCHANGES),
)
def test_factory_exchange_matches_configuration(exchange_name):
    exchange = ExchangeFactory.create(exchange_name)
    config = get_exchange_config(exchange_name)

    assert exchange.name == config.name