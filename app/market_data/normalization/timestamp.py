import math
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from numbers import Integral, Real

from app.market_data.exceptions import InvalidTimestampError


def normalize_timestamp(value: object) -> datetime:
    """
    Normalize supported timestamp inputs to a timezone-aware UTC datetime.

    Supported inputs:
        - timezone-aware datetime
        - Unix epoch seconds, milliseconds, microseconds, nanoseconds
        - ISO-8601 string (e.g. "2026-08-26T10:00:00+05:00", "2026-08-26T05:00:00Z")

    Rejects:
        - naive datetime
        - negative timestamp
        - NaN / Infinity
        - malformed ISO-8601
        - unsupported types
    """
    if isinstance(value, datetime):
        return _normalize_datetime(value)

    if isinstance(value, str):
        return _normalize_string(value)

    if isinstance(value, Integral):
        return _normalize_epoch(Decimal(value))

    if isinstance(value, Real):
        if math.isnan(value) or math.isinf(value):
            raise InvalidTimestampError(f"Epoch timestamp cannot be NaN or Infinity: {value!r}")
        return _normalize_epoch(Decimal(str(value)))

    if isinstance(value, Decimal):
        return _normalize_epoch(value)

    raise InvalidTimestampError(
        f"Unsupported timestamp type: {type(value).__name__}"
    )


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise InvalidTimestampError(
            "Naive datetime is not allowed; timezone information is required"
        )
    try:
        return value.astimezone(timezone.utc)
    except (OverflowError, ValueError) as exc:
        raise InvalidTimestampError(f"Invalid datetime value: {value!r}") from exc


def _normalize_string(value: str) -> datetime:
    text = value.strip()
    if not text:
        raise InvalidTimestampError("Timestamp string cannot be empty")

    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise InvalidTimestampError(
            f"Invalid ISO-8601 timestamp string: {value!r}"
        ) from exc

    return _normalize_datetime(parsed)


def _normalize_epoch(value: Decimal) -> datetime:
    try:
        if not value.is_finite():
            raise InvalidTimestampError(f"Epoch timestamp must be finite: {value!r}")
    except (AttributeError, InvalidOperation) as exc:
        raise InvalidTimestampError(f"Invalid decimal epoch value: {value!r}") from exc

    if value < 0:
        raise InvalidTimestampError(f"Epoch timestamp cannot be negative: {value!r}")

    absolute = abs(value)

    if absolute < Decimal("1e11"):
        seconds = value
    elif absolute < Decimal("1e14"):
        seconds = value / Decimal("1e3")
    elif absolute < Decimal("1e17"):
        seconds = value / Decimal("1e6")
    else:
        seconds = value / Decimal("1e9")

    try:
        return datetime.fromtimestamp(float(seconds), tz=timezone.utc)
    except (OverflowError, OSError, ValueError) as exc:
        raise InvalidTimestampError(
            f"Epoch timestamp outside supported datetime range: {value!r}"
        ) from exc
