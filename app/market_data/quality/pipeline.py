import logging
from datetime import datetime, timezone
from typing import Callable, Iterable

from app.market_data.exceptions import (
    CandleGapError,
    CandleValidationError,
    DuplicateCandleError,
)
from app.market_data.models import MarketCandle
from app.market_data.normalization.candle import validate_candle_fields
from app.market_data.quality.cross_exchange import CrossExchangeConsistency
from app.market_data.quality.gap import find_candle_gaps
from app.market_data.quality.models import (
    DataQualityResult,
    DataQualityStatus,
    NormalizationConfig,
)

logger = logging.getLogger(__name__)


class DataQualityPipeline:
    """
    Production-quality Data Quality & Normalization Pipeline.

    Steps:
    1. Normalize / Validate candle fields
    2. Deduplicate
    3. Sort chronologically
    4. Detect gaps
    5. Detect future timestamps
    6. Detect stale data
    7. Cross-exchange consistency checks
    """

    def __init__(
        self,
        config: NormalizationConfig | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.config = config or NormalizationConfig()
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def process(
        self,
        candles: Iterable[MarketCandle],
    ) -> tuple[list[MarketCandle], DataQualityResult]:
        """
        Process an iterable of MarketCandle objects through the data quality pipeline.

        Returns:
            Tuple of (clean_sorted_candles, DataQualityResult)
        """
        raw_list = list(candles)
        result = DataQualityResult(candle_count=len(raw_list))

        if not raw_list:
            result.status = DataQualityStatus.VALID
            return [], result

        now = self.clock()

        # --------------------------------------------------
        # 1. Validation & Field Sanity
        # --------------------------------------------------
        validated: list[MarketCandle] = []
        for index, candle in enumerate(raw_list):
            try:
                validate_candle_fields(
                    exchange=candle.exchange,
                    symbol=candle.symbol,
                    timeframe=candle.timeframe,
                    timestamp=candle.timestamp,
                    open_price=candle.open,
                    high_price=candle.high,
                    low_price=candle.low,
                    close_price=candle.close,
                    volume=candle.volume,
                )
                validated.append(candle)
            except CandleValidationError as exc:
                err_msg = f"Candle at index {index} rejected: {exc}"
                logger.error(err_msg)
                result.errors.append(err_msg)

        if result.errors:
            result.is_valid = False
            result.status = DataQualityStatus.INVALID

        # --------------------------------------------------
        # 2. Duplicate Detection
        # --------------------------------------------------
        seen: set[tuple[str, str, str, datetime]] = set()
        deduped: list[MarketCandle] = []

        for candle in validated:
            identity = (candle.exchange, candle.symbol, candle.timeframe, candle.timestamp)
            if identity in seen:
                result.duplicate_count += 1
                if self.config.duplicate_policy == "strict":
                    raise DuplicateCandleError(
                        f"Duplicate candle detected: {candle.exchange} {candle.symbol} {candle.timeframe} {candle.timestamp}"
                    )
            else:
                seen.add(identity)
                deduped.append(candle)

        if result.duplicate_count > 0:
            msg = f"Detected and removed {result.duplicate_count} duplicate candle(s)."
            logger.warning(msg)
            result.warnings.append(msg)

        # --------------------------------------------------
        # 3. Chronological Ordering
        # --------------------------------------------------
        clean_candles = sorted(deduped, key=lambda c: c.timestamp)

        # --------------------------------------------------
        # 4. Gap Detection
        # --------------------------------------------------
        gaps = find_candle_gaps(clean_candles)
        result.gap_count = len(gaps)

        if gaps:
            msg = f"Detected {len(gaps)} gap(s) in candle data."
            logger.warning(msg)
            result.warnings.append(msg)

            if self.config.gap_policy == "reject":
                raise CandleGapError(msg)

        # --------------------------------------------------
        # 5. Future Timestamp & Stale Data Detection
        # --------------------------------------------------
        tolerance_sec = self.config.future_timestamp_tolerance_seconds
        stale_sec = self.config.stale_data_threshold_seconds

        for candle in clean_candles:
            diff = (candle.timestamp - now).total_seconds()
            if diff > tolerance_sec:
                result.future_timestamp_detected = True
                msg = (
                    f"Future timestamp detected beyond tolerance ({diff:.2f}s > {tolerance_sec}s): "
                    f"{candle.timestamp.isoformat()}"
                )
                logger.warning(msg)
                result.warnings.append(msg)
                result.is_valid = False
                result.status = DataQualityStatus.INVALID

        if clean_candles:
            latest_ts = clean_candles[-1].timestamp
            age = (now - latest_ts).total_seconds()
            if age > stale_sec:
                result.stale = True
                msg = f"Stale market data detected: latest candle age is {age:.1f}s (threshold: {stale_sec}s)."
                logger.warning(msg)
                result.warnings.append(msg)

        # --------------------------------------------------
        # 6. Cross-Exchange Consistency
        # --------------------------------------------------
        comparisons = CrossExchangeConsistency.compare_candles(
            clean_candles,
            max_price_deviation_pct=self.config.max_price_deviation_percent,
        )
        for comp in comparisons:
            if comp.is_deviated:
                msg = (
                    f"Cross-exchange price deviation exceeded threshold ({comp.price_difference_pct:.2f}% > "
                    f"{self.config.max_price_deviation_percent}%): symbol={comp.symbol} timeframe={comp.timeframe} "
                    f"exchanges={comp.exchanges}"
                )
                logger.warning(msg)
                result.consistency_issues.append(msg)
                result.warnings.append(msg)

        # Final Status determination
        if not result.is_valid:
            result.status = DataQualityStatus.INVALID
        elif result.warnings or result.consistency_issues:
            result.status = DataQualityStatus.WARNING
        else:
            result.status = DataQualityStatus.VALID

        return clean_candles, result
