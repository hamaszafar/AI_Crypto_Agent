from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from numbers import Integral, Real


class TimestampNormalizationError(ValueError):
    """Raised when a timestamp cannot be normalized to UTC."""


def normalize_timestamp(value: object) -> datetime:
    """
    Normalize a supported timestamp representation to a UTC-aware datetime.

    Supported inputs:
        - timezone-aware datetime
        - Unix timestamp in seconds
        - Unix timestamp in milliseconds
        - Unix timestamp in microseconds
        - Unix timestamp in nanoseconds
        - ISO-8601 datetime string

    Naive datetime values are rejected because their timezone is ambiguous.
    """

    if isinstance(value, datetime):
        return _normalize_datetime(value)

    if isinstance(value, str):
        return _normalize_string(value)

    if isinstance(value, Integral):
        return _normalize_epoch(Decimal(value))

    if isinstance(value, Real):
        return _normalize_epoch(Decimal(str(value)))

    if isinstance(value, Decimal):
        return _normalize_epoch(value)

    raise TimestampNormalizationError(
        f"Unsupported timestamp type: {type(value).__name__}"
    )


def _normalize_datetime(value: datetime) -> datetime:
    """Convert an aware datetime to UTC."""

    if value.tzinfo is None:
        raise TimestampNormalizationError(
            "Naive datetime is not allowed; timezone information is required"
        )

    try:
        return value.astimezone(timezone.utc)
    except (OverflowError, ValueError) as exc:
        raise TimestampNormalizationError(
            f"Invalid datetime value: {value!r}"
        ) from exc


def _normalize_string(value: str) -> datetime:
    """Parse an ISO-8601 timestamp string."""

    text = value.strip()

    if not text:
        raise TimestampNormalizationError("Timestamp string cannot be empty")

    # ISO-8601 commonly uses "Z" for UTC.
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise TimestampNormalizationError(
            f"Invalid ISO-8601 timestamp: {value!r}"
        ) from exc

    return _normalize_datetime(parsed)


def _normalize_epoch(value: Decimal) -> datetime:
    """
    Convert a Unix epoch value to UTC.

    The unit is inferred from the magnitude:
        seconds      < 1e11
        milliseconds < 1e14
        microseconds < 1e17
        nanoseconds  otherwise
    """

    if not value.is_finite():
        raise TimestampNormalizationError(
            f"Epoch timestamp must be finite: {value!r}"
        )

    if value < 0:
        raise TimestampNormalizationError(
            f"Epoch timestamp cannot be negative: {value!r}"
        )

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
        return datetime.fromtimestamp(
            float(seconds),
            tz=timezone.utc,
        )
    except (OverflowError, OSError, ValueError) as exc:
        raise TimestampNormalizationError(
            f"Epoch timestamp is outside the supported datetime range: {value!r}"
        ) from exc
