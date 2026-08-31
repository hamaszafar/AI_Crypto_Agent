from dataclasses import dataclass, field
from typing import FrozenSet


@dataclass(frozen=True)
class ExchangeCapabilities:
    """
    Describes the market-data capabilities supported by an exchange.
    """

    supports_rest: bool = True
    supports_websocket: bool = False
    supports_historical_data: bool = True
    supports_incremental_data: bool = True


@dataclass(frozen=True)
class RateLimitConfig:
    """
    Exchange API rate-limit configuration.
    """

    requests_per_minute: int
    requests_per_second: int | None = None
    retry_after_seconds: float = 1.0


@dataclass(frozen=True)
class ExchangeConfig:
    """
    Immutable configuration for a single exchange.
    """

    name: str
    rest_endpoint: str
    websocket_endpoint: str | None = None

    supported_symbols: FrozenSet[str] = field(
        default_factory=frozenset
    )

    supported_timeframes: FrozenSet[str] = field(
        default_factory=frozenset
    )

    rate_limits: RateLimitConfig = field(
        default_factory=lambda: RateLimitConfig(
            requests_per_minute=60
        )
    )

    capabilities: ExchangeCapabilities = field(
        default_factory=ExchangeCapabilities
    )

    def supports_symbol(self, symbol: str) -> bool:
        return symbol in self.supported_symbols

    def supports_timeframe(self, timeframe: str) -> bool:
        return timeframe in self.supported_timeframes


EXCHANGE_CONFIGS: dict[str, ExchangeConfig] = {
    "binance": ExchangeConfig(
        name="binance",
        rest_endpoint="https://api.binance.com",
        supported_timeframes=frozenset(
            {"15m", "1h", "4h", "1d"}
        ),
        rate_limits=RateLimitConfig(
            requests_per_minute=1200
        ),
        capabilities=ExchangeCapabilities(
            supports_rest=True,
            supports_websocket=True,
            supports_historical_data=True,
            supports_incremental_data=True,
        ),
    ),

    "bybit": ExchangeConfig(
        name="bybit",
        rest_endpoint="https://api.bybit.com",
        supported_timeframes=frozenset(
            {"15m", "1h", "4h", "1d"}
        ),
        rate_limits=RateLimitConfig(
            requests_per_minute=600
        ),
        capabilities=ExchangeCapabilities(
            supports_rest=True,
            supports_websocket=True,
            supports_historical_data=True,
            supports_incremental_data=True,
        ),
    ),

    "bitget": ExchangeConfig(
        name="bitget",
        rest_endpoint="https://api.bitget.com",
        supported_timeframes=frozenset(
            {"15m", "1h", "4h", "1d"}
        ),
        rate_limits=RateLimitConfig(
            requests_per_minute=600
        ),
        capabilities=ExchangeCapabilities(
            supports_rest=True,
            supports_websocket=True,
            supports_historical_data=True,
            supports_incremental_data=True,
        ),
    ),

    "okx": ExchangeConfig(
        name="okx",
        rest_endpoint="https://www.okx.com",
        supported_timeframes=frozenset(
            {"15m", "1h", "4h", "1d"}
        ),
        rate_limits=RateLimitConfig(
            requests_per_minute=600
        ),
        capabilities=ExchangeCapabilities(
            supports_rest=True,
            supports_websocket=True,
            supports_historical_data=True,
            supports_incremental_data=True,
        ),
    ),

    "kraken": ExchangeConfig(
        name="kraken",
        rest_endpoint="https://api.kraken.com",
        supported_timeframes=frozenset(
            {"15m", "1h", "4h", "1d"}
        ),
        rate_limits=RateLimitConfig(
            requests_per_minute=60
        ),
        capabilities=ExchangeCapabilities(
            supports_rest=True,
            supports_websocket=True,
            supports_historical_data=True,
            supports_incremental_data=True,
        ),
    ),

    "coinbase": ExchangeConfig(
        name="coinbase",
        rest_endpoint="https://api.exchange.coinbase.com",
        supported_timeframes=frozenset(
            {"15m", "1h", "4h", "1d"}
        ),
        rate_limits=RateLimitConfig(
            requests_per_minute=600
        ),
        capabilities=ExchangeCapabilities(
            supports_rest=True,
            supports_websocket=True,
            supports_historical_data=True,
            supports_incremental_data=True,
        ),
    ),
}


def get_exchange_config(exchange_name: str) -> ExchangeConfig:
    """
    Return configuration for an exchange.

    Exchange names are case-insensitive.
    """

    if not isinstance(exchange_name, str):
        raise TypeError("exchange_name must be a string")

    name = exchange_name.strip().lower()

    try:
        return EXCHANGE_CONFIGS[name]
    except KeyError:
        raise ValueError(
            f"Unknown exchange: {exchange_name}"
        ) from None


def available_exchange_configs() -> list[str]:
    """
    Return configured exchange names.
    """

    return sorted(EXCHANGE_CONFIGS.keys())