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

    requests_per_minute:
        Maximum number of requests allowed per minute.

    requests_per_second:
        Optional per-second request limit.

    retry_after_seconds:
        Default delay when the exchange asks the client to retry.
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
        """
        Return True if the exchange supports the supplied symbol.
        """
        return symbol in self.supported_symbols

    def supports_timeframe(self, timeframe: str) -> bool:
        """
        Return True if the exchange supports the supplied timeframe.
        """
        return timeframe in self.supported_timeframes