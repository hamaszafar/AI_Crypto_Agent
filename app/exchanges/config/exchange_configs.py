from app.exchanges.config.exchange_config import (
    ExchangeCapabilities,
    ExchangeConfig,
    RateLimitConfig,
)


COMMON_TIMEFRAMES = frozenset(
    {
        "15m",
        "1h",
        "4h",
        "1d",
    }
)


BINANCE_CONFIG = ExchangeConfig(
    name="binance",
    rest_endpoint="https://api.binance.com",
    websocket_endpoint="wss://stream.binance.com:9443/ws",
    supported_symbols=frozenset(
        {
            "BTC/USDT",
            "ETH/USDT",
        }
    ),
    supported_timeframes=COMMON_TIMEFRAMES,
    rate_limits=RateLimitConfig(
        requests_per_minute=1200,
        requests_per_second=20,
        retry_after_seconds=1.0,
    ),
    capabilities=ExchangeCapabilities(
        supports_rest=True,
        supports_websocket=True,
        supports_historical_data=True,
        supports_incremental_data=True,
    ),
)


BYBIT_CONFIG = ExchangeConfig(
    name="bybit",
    rest_endpoint="https://api.bybit.com",
    websocket_endpoint="wss://stream.bybit.com/v5/public/spot",
    supported_symbols=frozenset(),
    supported_timeframes=COMMON_TIMEFRAMES,
    rate_limits=RateLimitConfig(
        requests_per_minute=600,
        retry_after_seconds=1.0,
    ),
    capabilities=ExchangeCapabilities(
        supports_rest=True,
        supports_websocket=True,
        supports_historical_data=True,
        supports_incremental_data=True,
    ),
)


OKX_CONFIG = ExchangeConfig(
    name="okx",
    rest_endpoint="https://www.okx.com",
    websocket_endpoint="wss://ws.okx.com:8443/ws/v5/public",
    supported_symbols=frozenset(),
    supported_timeframes=COMMON_TIMEFRAMES,
    rate_limits=RateLimitConfig(
        requests_per_minute=600,
        retry_after_seconds=1.0,
    ),
    capabilities=ExchangeCapabilities(
        supports_rest=True,
        supports_websocket=True,
        supports_historical_data=True,
        supports_incremental_data=True,
    ),
)


KRAKEN_CONFIG = ExchangeConfig(
    name="kraken",
    rest_endpoint="https://api.kraken.com",
    websocket_endpoint="wss://ws.kraken.com",
    supported_symbols=frozenset(),
    supported_timeframes=COMMON_TIMEFRAMES,
    rate_limits=RateLimitConfig(
        requests_per_minute=60,
        retry_after_seconds=1.0,
    ),
    capabilities=ExchangeCapabilities(
        supports_rest=True,
        supports_websocket=True,
        supports_historical_data=True,
        supports_incremental_data=True,
    ),
)


COINBASE_CONFIG = ExchangeConfig(
    name="coinbase",
    rest_endpoint="https://api.exchange.coinbase.com",
    websocket_endpoint="wss://ws-feed.exchange.coinbase.com",
    supported_symbols=frozenset(),
    supported_timeframes=COMMON_TIMEFRAMES,
    rate_limits=RateLimitConfig(
        requests_per_minute=60,
        retry_after_seconds=1.0,
    ),
    capabilities=ExchangeCapabilities(
        supports_rest=True,
        supports_websocket=True,
        supports_historical_data=True,
        supports_incremental_data=True,
    ),
)


EXCHANGE_CONFIGS: dict[str, ExchangeConfig] = {
    "binance": BINANCE_CONFIG,
    "bybit": BYBIT_CONFIG,
    "okx": OKX_CONFIG,
    "kraken": KRAKEN_CONFIG,
    "coinbase": COINBASE_CONFIG,
}


def get_exchange_config(name: str) -> ExchangeConfig:
    """
    Return configuration for an exchange.

    Raises:
        KeyError: if the exchange is not configured.
    """

    normalized_name = name.strip().lower()

    try:
        return EXCHANGE_CONFIGS[normalized_name]
    except KeyError as exc:
        raise KeyError(
            f"Unsupported exchange configuration: {name}"
        ) from exc


def available_exchange_configs() -> list[str]:
    """
    Return all configured exchange names.
    """
    return sorted(EXCHANGE_CONFIGS.keys())