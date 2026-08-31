from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from app.market_data.exceptions import CandleValidationError
from app.market_data.models import MarketCandle
from app.market_data.normalization.service import MarketDataNormalizer


CandleIdentity = tuple[str, str, str, object]


# ============================================================
# 2A.13.3 — OHLC VALIDATION
# ============================================================

def validate_ohlc(candle: MarketCandle) -> None:
    """Validate OHLC price relationships."""

    values = {
        "open": candle.open,
        "high": candle.high,
        "low": candle.low,
        "close": candle.close,
    }

    for name, value in values.items():
        _validate_price(name, value)

    if candle.high < candle.low:
        raise CandleValidationError(
            f"High price cannot be lower than low price: "
            f"high={candle.high}, low={candle.low}"
        )

    if candle.high < candle.open:
        raise CandleValidationError(
            f"High price cannot be lower than open price: "
            f"high={candle.high}, open={candle.open}"
        )

    if candle.high < candle.close:
        raise CandleValidationError(
            f"High price cannot be lower than close price: "
            f"high={candle.high}, close={candle.close}"
        )

    if candle.low > candle.open:
        raise CandleValidationError(
            f"Low price cannot be higher than open price: "
            f"low={candle.low}, open={candle.open}"
        )

    if candle.low > candle.close:
        raise CandleValidationError(
            f"Low price cannot be higher than close price: "
            f"low={candle.low}, close={candle.close}"
        )


def is_valid_ohlc(candle: MarketCandle) -> bool:
    """Return True when OHLC relationships are valid."""

    try:
        validate_ohlc(candle)
    except CandleValidationError:
        return False

    return True


def _validate_price(name: str, value: Decimal) -> None:
    """Validate an individual OHLC price."""

    if not isinstance(value, Decimal):
        raise CandleValidationError(
            f"{name} must be a Decimal, "
            f"got {type(value).__name__}"
        )

    if not value.is_finite():
        raise CandleValidationError(
            f"{name} must be finite: {value!r}"
        )

    if value <= Decimal("0"):
        raise CandleValidationError(
            f"{name} price must be positive: {value!r}"
        )


# ============================================================
# 2A.13.4 — VOLUME VALIDATION
# ============================================================

def validate_volume(candle: MarketCandle) -> None:
    """Validate candle volume."""

    volume = candle.volume

    if not isinstance(volume, Decimal):
        raise CandleValidationError(
            f"volume must be a Decimal, "
            f"got {type(volume).__name__}"
        )

    if not volume.is_finite():
        raise CandleValidationError(
            f"volume must be finite: {volume!r}"
        )

    if volume < Decimal("0"):
        raise CandleValidationError(
            f"volume cannot be negative: {volume!r}"
        )


def is_valid_volume(candle: MarketCandle) -> bool:
    """Return True when volume is valid."""

    try:
        validate_volume(candle)
    except CandleValidationError:
        return False

    return True


# ============================================================
# 2A.13.5 — DUPLICATE DETECTION
# ============================================================

def candle_identity(
    candle: MarketCandle,
) -> CandleIdentity:
    """
    Return the canonical identity of a candle.

    Candle identity is based on:
        exchange
        symbol
        timeframe
        timestamp
    """

    return (
        candle.exchange,
        candle.symbol,
        candle.timeframe,
        candle.timestamp,
    )


def find_duplicate_candles(
    candles: Iterable[MarketCandle],
) -> list[MarketCandle]:
    """
    Return duplicate candle occurrences.

    The first occurrence is considered canonical.
    Later occurrences are returned.
    """

    seen: set[CandleIdentity] = set()
    duplicates: list[MarketCandle] = []

    for candle in candles:
        identity = candle_identity(candle)

        if identity in seen:
            duplicates.append(candle)
        else:
            seen.add(identity)

    return duplicates


def has_duplicates(
    candles: Iterable[MarketCandle],
) -> bool:
    """Return True when duplicate candles exist."""

    seen: set[CandleIdentity] = set()

    for candle in candles:
        identity = candle_identity(candle)

        if identity in seen:
            return True

        seen.add(identity)

    return False


def remove_duplicate_candles(
    candles: Iterable[MarketCandle],
) -> list[MarketCandle]:
    """
    Remove duplicate candles while preserving
    the first occurrence.
    """

    seen: set[CandleIdentity] = set()
    unique: list[MarketCandle] = []

    for candle in candles:
        identity = candle_identity(candle)

        if identity in seen:
            continue

        seen.add(identity)
        unique.append(candle)

    return unique


# ============================================================
# 2A.13.6 — CHRONOLOGICAL ORDERING
# ============================================================

def sort_chronologically(
    candles: Iterable[MarketCandle],
) -> list[MarketCandle]:
    """
    Return candles ordered from oldest to newest.

    The input collection is not modified.
    """

    return sorted(
        candles,
        key=lambda candle: candle.timestamp,
    )


def is_chronological(
    candles: Iterable[MarketCandle],
) -> bool:
    """
    Return True when timestamps are in non-decreasing order.

    Equal timestamps are allowed here because duplicate
    detection is handled separately.
    """

    iterator = iter(candles)

    try:
        previous = next(iterator)
    except StopIteration:
        return True

    for current in iterator:
        if current.timestamp < previous.timestamp:
            return False

        previous = current

    return True


def is_strictly_chronological(
    candles: Iterable[MarketCandle],
) -> bool:
    """
    Return True when timestamps are strictly increasing.

    Equal timestamps are considered invalid.
    """

    iterator = iter(candles)

    try:
        previous = next(iterator)
    except StopIteration:
        return True

    for current in iterator:
        if current.timestamp <= previous.timestamp:
            return False

        previous = current

    return True


def find_out_of_order_candles(
    candles: Iterable[MarketCandle],
) -> list[MarketCandle]:
    """
    Return candles whose timestamp is earlier than
    the immediately preceding candle.
    """

    iterator = iter(candles)

    try:
        previous = next(iterator)
    except StopIteration:
        return []

    out_of_order: list[MarketCandle] = []

    for current in iterator:
        if current.timestamp < previous.timestamp:
            out_of_order.append(current)

        previous = current

    return out_of_order


# ============================================================
# 2A.13.7 — EXCHANGE / SYMBOL / TIMEFRAME CONSISTENCY
# ============================================================

def validate_consistency(
    candles: Iterable[MarketCandle],
) -> None:
    """
    Validate that all candles belong to the same
    exchange, symbol, and timeframe.
    """

    iterator = iter(candles)

    try:
        first = next(iterator)
    except StopIteration:
        return

    expected_exchange = first.exchange
    expected_symbol = first.symbol
    expected_timeframe = first.timeframe

    for index, candle in enumerate(iterator, start=1):

        if candle.exchange != expected_exchange:
            raise CandleValidationError(
                f"Inconsistent exchange at index {index}: "
                f"expected {expected_exchange!r}, "
                f"got {candle.exchange!r}"
            )

        if candle.symbol != expected_symbol:
            raise CandleValidationError(
                f"Inconsistent symbol at index {index}: "
                f"expected {expected_symbol!r}, "
                f"got {candle.symbol!r}"
            )

        if candle.timeframe != expected_timeframe:
            raise CandleValidationError(
                f"Inconsistent timeframe at index {index}: "
                f"expected {expected_timeframe!r}, "
                f"got {candle.timeframe!r}"
            )


def is_consistent(
    candles: Iterable[MarketCandle],
) -> bool:
    """Return True when all candles belong to one series."""

    try:
        validate_consistency(candles)
    except CandleValidationError:
        return False

    return True


# ============================================================
# 2A.13.8 — COMPLETE MARKET DATA VALIDATION PIPELINE
# ============================================================

def validate_market_data(
    candles: Iterable[object],
) -> list[MarketCandle]:
    """
    Run the complete market-data validation pipeline.

    Validation order:
        1. Convert inputs to canonical MarketCandle instances
        2. OHLC validation
        3. Volume validation
        4. Exchange/symbol/timeframe consistency
        5. Duplicate detection
        6. Chronological ordering

    Returns:
        A validated list of MarketCandle objects.

    Raises:
        CandleValidationError: If any candle or collection is invalid.
    """
    raw_list = list(candles)

    if not raw_list:
        return []

    # 1. Normalization / Conversion to MarketCandle
    validated: list[MarketCandle] = []
    for item in raw_list:
        if isinstance(item, MarketCandle):
            validated.append(item)
        elif hasattr(item, "exchange") and hasattr(item, "open"):
            validated.append(MarketDataNormalizer.from_exchange_candle(item))
        else:
            raise CandleValidationError(f"Invalid candle input: {item!r}")

    # 2. Individual candle validation
    for candle in validated:
        validate_ohlc(candle)
        validate_volume(candle)

    # 3. Series consistency
    validate_consistency(validated)

    # 4. Duplicate detection
    duplicates = find_duplicate_candles(validated)
    if duplicates:
        raise CandleValidationError(
            f"Duplicate candles detected: {len(duplicates)}"
        )

    # 5. Chronological ordering
    if not is_strictly_chronological(validated):
        raise CandleValidationError(
            "Candles must be strictly chronological"
        )

    return validated