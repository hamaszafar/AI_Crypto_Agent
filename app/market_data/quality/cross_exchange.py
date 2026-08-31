from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from app.market_data.models import MarketCandle


@dataclass(frozen=True, slots=True)
class ConsistencyComparison:
    """Metric summary comparing same market candle across exchanges."""
    symbol: str
    timeframe: str
    timestamp_iso: str
    exchanges: tuple[str, ...]
    min_close: Decimal
    max_close: Decimal
    price_difference: Decimal
    price_difference_pct: Decimal
    volume_difference: Decimal
    volume_difference_pct: Decimal
    is_deviated: bool


class CrossExchangeConsistency:
    """
    Evaluates market data consistency across multiple exchanges.
    """

    @staticmethod
    def compare_candles(
        candles: Sequence[MarketCandle],
        max_price_deviation_pct: Decimal = Decimal("5.0"),
    ) -> list[ConsistencyComparison]:
        """
        Group candles by (symbol, timeframe, timestamp) and calculate cross-exchange deviations.
        """
        grouped: dict[tuple[str, str, object], list[MarketCandle]] = {}
        for c in candles:
            key = (c.symbol, c.timeframe, c.timestamp)
            grouped.setdefault(key, []).append(c)

        comparisons: list[ConsistencyComparison] = []

        for (sym, tf, ts), group in grouped.items():
            if len(group) < 2:
                continue

            exchanges = tuple(c.exchange for c in group)
            closes = [c.close for c in group]
            volumes = [c.volume for c in group]

            min_close = min(closes)
            max_close = max(closes)
            price_diff = max_close - min_close
            price_diff_pct = (price_diff / min_close) * Decimal("100") if min_close > 0 else Decimal("0")

            min_vol = min(volumes)
            max_vol = max(volumes)
            vol_diff = max_vol - min_vol
            vol_diff_pct = (vol_diff / min_vol) * Decimal("100") if min_vol > 0 else Decimal("0")

            is_deviated = price_diff_pct > max_price_deviation_pct

            comparisons.append(
                ConsistencyComparison(
                    symbol=sym,
                    timeframe=tf,
                    timestamp_iso=ts.isoformat(),
                    exchanges=exchanges,
                    min_close=min_close,
                    max_close=max_close,
                    price_difference=price_diff,
                    price_difference_pct=price_diff_pct,
                    volume_difference=vol_diff,
                    volume_difference_pct=vol_diff_pct,
                    is_deviated=is_deviated,
                )
            )

        return comparisons
