from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.market_data.normalizer import (
    TimestampNormalizationError,
    normalize_timestamp,
)


def test_timezone_aware_datetime_is_normalized_to_utc():
    value = datetime(
        2026,
        8,
        22,
        17,
        0,
        tzinfo=timezone(timedelta(hours=5)),
    )

    result = normalize_timestamp(value)

    assert result == datetime(
        2026,
        8,
        22,
        12,
        0,
        tzinfo=timezone.utc,
    )


def test_naive_datetime_is_rejected():
    value = datetime(2026, 8, 22, 12, 0)

    with pytest.raises(TimestampNormalizationError):
        normalize_timestamp(value)


def test_unix_seconds_are_normalized():
    result = normalize_timestamp(1787400000)

    assert result.tzinfo == timezone.utc
    assert result == datetime.fromtimestamp(
        1787400000,
        tz=timezone.utc,
    )


def test_unix_milliseconds_are_normalized():
    value = 1787400000000

    result = normalize_timestamp(value)

    assert result.tzinfo == timezone.utc
    assert result == datetime.fromtimestamp(
        value / 1000,
        tz=timezone.utc,
    )


def test_unix_microseconds_are_normalized():
    value = 1787400000000000

    result = normalize_timestamp(value)

    assert result.tzinfo == timezone.utc
    assert result == datetime.fromtimestamp(
        value / 1_000_000,
        tz=timezone.utc,
    )


def test_unix_nanoseconds_are_normalized():
    value = 1787400000000000000

    result = normalize_timestamp(value)

    assert result.tzinfo == timezone.utc
    assert result == datetime.fromtimestamp(
        value / 1_000_000_000,
        tz=timezone.utc,
    )


def test_decimal_epoch_is_supported():
    value = Decimal("1787400000.500")

    result = normalize_timestamp(value)

    assert result.tzinfo == timezone.utc
    assert result == datetime.fromtimestamp(
        1787400000.5,
        tz=timezone.utc,
    )


def test_iso8601_utc_string_is_supported():
    value = "2026-08-22T12:00:00Z"

    result = normalize_timestamp(value)

    assert result == datetime(
        2026,
        8,
        22,
        12,
        0,
        tzinfo=timezone.utc,
    )


def test_iso8601_offset_string_is_converted_to_utc():
    value = "2026-08-22T17:00:00+05:00"

    result = normalize_timestamp(value)

    assert result == datetime(
        2026,
        8,
        22,
        12,
        0,
        tzinfo=timezone.utc,
    )


def test_invalid_string_is_rejected():
    with pytest.raises(TimestampNormalizationError):
        normalize_timestamp("not-a-timestamp")


def test_empty_string_is_rejected():
    with pytest.raises(TimestampNormalizationError):
        normalize_timestamp("")


def test_unsupported_type_is_rejected():
    with pytest.raises(TimestampNormalizationError):
        normalize_timestamp(object())


def test_negative_epoch_is_rejected():
    with pytest.raises(TimestampNormalizationError):
        normalize_timestamp(-1)


def test_nan_epoch_is_rejected():
    with pytest.raises(TimestampNormalizationError):
        normalize_timestamp(float("nan"))


def test_infinity_epoch_is_rejected():
    with pytest.raises(TimestampNormalizationError):
        normalize_timestamp(float("inf"))
