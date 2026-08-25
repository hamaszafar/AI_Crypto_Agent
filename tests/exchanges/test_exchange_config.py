import pytest

from app.exchanges.config import (
    BINANCE_CONFIG,
    EXCHANGE_CONFIGS,
    ExchangeCapabilities,
    ExchangeConfig,
    RateLimitConfig,
    available_exchange_configs,
    get_exchange_config,
)


def test_exchange_config_stores_basic_information():
    config = ExchangeConfig(
        name="test",
        rest_endpoint="https://example.com",
    )

    assert config.name == "test"
    assert config.rest_endpoint == "https://example.com"
    assert config.websocket_endpoint is None


def test_exchange_config_is_immutable():
    config = ExchangeConfig(
        name="test",
        rest_endpoint="https://example.com",
    )

    with pytest.raises(AttributeError):
        config.name = "changed"


def test_exchange_config_supports_symbol():
    config = ExchangeConfig(
        name="test",
        rest_endpoint="https://example.com",
        supported_symbols=frozenset({"BTC/USDT"}),
    )

    assert config.supports_symbol("BTC/USDT")
    assert not config.supports_symbol("ETH/USDT")


def test_exchange_config_supports_timeframe():
    config = ExchangeConfig(
        name="test",
        rest_endpoint="https://example.com",
        supported_timeframes=frozenset({"15m", "1h"}),
    )

    assert config.supports_timeframe("15m")
    assert config.supports_timeframe("1h")
    assert not config.supports_timeframe("1d")


def test_rate_limit_configuration():
    rate_limit = RateLimitConfig(
        requests_per_minute=1200,
        requests_per_second=20,
        retry_after_seconds=2.0,
    )

    assert rate_limit.requests_per_minute == 1200
    assert rate_limit.requests_per_second == 20
    assert rate_limit.retry_after_seconds == 2.0


def test_exchange_capabilities():
    capabilities = ExchangeCapabilities(
        supports_rest=True,
        supports_websocket=True,
        supports_historical_data=True,
        supports_incremental_data=True,
    )

    assert capabilities.supports_rest
    assert capabilities.supports_websocket
    assert capabilities.supports_historical_data
    assert capabilities.supports_incremental_data


def test_binance_configuration_exists():
    assert BINANCE_CONFIG.name == "binance"
    assert BINANCE_CONFIG.rest_endpoint == "https://api.binance.com"
    assert BINANCE_CONFIG.websocket_endpoint is not None


def test_all_exchange_configurations_exist():
    expected = {
        "binance",
        "bybit",
        "okx",
        "kraken",
        "coinbase",
    }

    assert set(EXCHANGE_CONFIGS.keys()) == expected


def test_get_exchange_config_is_case_insensitive():
    assert get_exchange_config("BINANCE") is BINANCE_CONFIG
    assert get_exchange_config(" Binance ") is BINANCE_CONFIG


def test_get_exchange_config_unknown_exchange():
    with pytest.raises(KeyError, match="Unsupported exchange configuration"):
        get_exchange_config("unknown")


def test_available_exchange_configs():
    assert available_exchange_configs() == [
        "binance",
        "bybit",
        "coinbase",
        "kraken",
        "okx",
    ]