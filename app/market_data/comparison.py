from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.market_data.models import MarketCandle


@dataclass(frozen=True)
class ExchangePrice:
    """Price observation from one exchange."""

    exchange: str
    price: Decimal


@dataclass(frozen=True)
class ExchangeVolume:
    """Volume observation from one exchange."""

    exchange: str
    volume: Decimal


@dataclass(frozen=True)
class ComparisonResult:
    """
    Cross-exchange comparison for the same market candle.

    This model contains observations only.
    It does not make trading decisions.
    """

    symbol: str
    timeframe: str
    timestamp: object

    prices: tuple[ExchangePrice, ...]
    volumes: tuple[ExchangeVolume, ...]

    highest_price: Decimal
    lowest_price: Decimal

    price_difference: Decimal
    price_difference_percent: Decimal

    highest_volume: Decimal
    lowest_volume: Decimal

    volume_difference: Decimal
    volume_difference_percent: Decimal

    @property
    def exchange_count(self) -> int:
        """Return the number of exchanges being compared."""

        return len(self.prices)

    @property
    def spread(self) -> Decimal:
        """
        Return the absolute price spread.

        Spread is:

            highest price - lowest price
        """

        return self.price_difference

    @property
    def spread_percent(self) -> Decimal:
        """
        Return spread percentage relative to the lowest price.
        """

        return self.price_difference_percent


class CrossExchangeComparator:
    """
    Compare validated market candles from multiple exchanges.

    The comparator expects candles representing the same:
        - symbol
        - timeframe
        - timestamp
    """

    def compare(
        self,
        candles: dict[str, MarketCandle],
    ) -> ComparisonResult:
        """
        Compare one candle from each exchange.

        Args:
            candles:
                Mapping of exchange name to MarketCandle.

        Returns:
            ComparisonResult containing price, volume and spread data.
        """

        if not candles:
            raise ValueError(
                "At least one exchange candle is required."
            )

        candle_list = list(candles.values())

        self._validate_consistency(candle_list)

        prices = tuple(
            ExchangePrice(
                exchange=candle.exchange,
                price=candle.close,
            )
            for candle in candle_list
        )

        volumes = tuple(
            ExchangeVolume(
                exchange=candle.exchange,
                volume=candle.volume,
            )
            for candle in candle_list
        )

        price_values = [item.price for item in prices]
        volume_values = [item.volume for item in volumes]

        highest_price = max(price_values)
        lowest_price = min(price_values)

        highest_volume = max(volume_values)
        lowest_volume = min(volume_values)

        price_difference = (
            highest_price - lowest_price
        )

        volume_difference = (
            highest_volume - lowest_volume
        )

        price_difference_percent = (
            self._percentage_difference(
                price_difference,
                lowest_price,
            )
        )

        volume_difference_percent = (
            self._percentage_difference(
                volume_difference,
                lowest_volume,
            )
        )

        reference = candle_list[0]

        return ComparisonResult(
            symbol=reference.symbol,
            timeframe=reference.timeframe,
            timestamp=reference.timestamp,
            prices=prices,
            volumes=volumes,
            highest_price=highest_price,
            lowest_price=lowest_price,
            price_difference=price_difference,
            price_difference_percent=price_difference_percent,
            highest_volume=highest_volume,
            lowest_volume=lowest_volume,
            volume_difference=volume_difference,
            volume_difference_percent=volume_difference_percent,
        )

    @staticmethod
    def _percentage_difference(
        difference: Decimal,
        reference: Decimal,
    ) -> Decimal:
        """
        Calculate:

            difference / reference * 100
        """

        if reference == Decimal("0"):
            return Decimal("0")

        return (
            difference / reference
        ) * Decimal("100")

    @staticmethod
    def _validate_consistency(
        candles: list[MarketCandle],
    ) -> None:
        """Ensure all candles represent the same market point."""

        reference = candles[0]

        for candle in candles[1:]:

            if candle.symbol != reference.symbol:
                raise ValueError(
                    "All candles must have the same symbol."
                )

            if candle.timeframe != reference.timeframe:
                raise ValueError(
                    "All candles must have the same timeframe."
                )

            if candle.timestamp != reference.timestamp:
                raise ValueError(
                    "All candles must have the same timestamp."
                )

            if candle.exchange == reference.exchange:
                raise ValueError(
                    "Duplicate exchange detected."
                )