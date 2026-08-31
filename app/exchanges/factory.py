from typing import Type

from app.exchanges.base import BaseExchange
from app.exchanges.config.exchange_configs import get_exchange_config


class ExchangeFactory:
    """Registry-based factory for creating configured exchange implementations."""

    _registry: dict[str, Type[BaseExchange]] = {}

    @classmethod
    def register(
        cls,
        name: str,
        exchange_class: Type[BaseExchange],
    ) -> None:
        """Register an exchange implementation."""
        cls._registry[name.strip().lower()] = exchange_class

    @classmethod
    def _load_registry(cls) -> None:
        """Load built-in exchange registrations."""
        import app.exchanges.registry  # noqa: F401

    @classmethod
    def create(cls, name: str) -> BaseExchange:
        """
        Create an exchange instance.

        Production exchanges must have valid configuration.
        The mock exchange is a test-only implementation and does
        not require production configuration.
        """

        if not cls._registry:
            cls._load_registry()

        normalized_name = name.strip().lower()

        # ----------------------------------------------------------
        # Validate configuration for production exchanges
        # ----------------------------------------------------------
        if normalized_name != "mock":
            try:
                get_exchange_config(normalized_name)
            except KeyError as exc:
                raise ValueError(
                    f"Unsupported exchange: {name}"
                ) from exc

        # ----------------------------------------------------------
        # Find registered implementation
        # ----------------------------------------------------------
        try:
            exchange_class = cls._registry[normalized_name]
        except KeyError as exc:
            raise ValueError(
                f"Exchange is configured but not registered: {name}"
            ) from exc

        # ----------------------------------------------------------
        # Create exchange
        # ----------------------------------------------------------
        return exchange_class()

    @classmethod
    def available(cls) -> list[str]:
        """Return registered exchange names."""

        if not cls._registry:
            cls._load_registry()

        return sorted(cls._registry.keys())

    @classmethod
    def available_exchanges(cls) -> list[str]:
        """Backward-compatible alias for available()."""
        return cls.available()