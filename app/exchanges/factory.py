from typing import Type

from app.exchanges.base import BaseExchange


class ExchangeFactory:
    """Registry-based factory for creating exchange implementations."""

    _registry: dict[str, Type[BaseExchange]] = {}

    @classmethod
    def register(
        cls,
        name: str,
        exchange_class: Type[BaseExchange],
    ) -> None:
        """Register an exchange implementation."""
        cls._registry[name.lower()] = exchange_class

    @classmethod
    def create(cls, name: str) -> BaseExchange:
        """Create an exchange instance by name."""

        # Load built-in registrations on first use.
        if not cls._registry:
            import app.exchanges.registry  # noqa: F401

        key = name.lower()

        try:
            exchange_class = cls._registry[key]
        except KeyError:
            raise ValueError(f"Unsupported exchange: {name}") from None

        return exchange_class()

    @classmethod
    def available(cls) -> list[str]:
        """Return registered exchange names."""

        if not cls._registry:
            import app.exchanges.registry  # noqa: F401

        return list(cls._registry.keys())
