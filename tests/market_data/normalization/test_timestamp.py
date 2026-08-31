from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest

from app.market_data.exceptions import InvalidTimestampError
from app.market_data.normalization.timestamp import normalize_timestamp


def test_normalize_timestamp_datetime():
    dt_utc = datetime(2026, 8, 26, 10, 0, 0, tzinfo=timezone.utc)
    assert normalize_timestamp(dt_utc) == dt_utc

    dt_offset = datetime(2026, 8, 26, 15, 0, 0, tzinfo=timezone(timedelta(hours=5)))
    assert normalize_timestamp(dt_offset) == dt_utc


def test_normalize_timestamp_iso_string():
    assert normalize_timestamp("2026-08-26T10:00:00Z") == datetime(2026, 8, 26, 10, 0, 0, tzinfo=timezone.utc)
    assert normalize_timestamp("2026-08-26T15:00:00+05:00") == datetime(2026, 8, 26, 10, 0, 0, tzinfo=timezone.utc)


def test_normalize_timestamp_epoch():
    ts_sec = 1787652000  # epoch sec
    ts_norm = normalize_timestamp(ts_sec)
    assert ts_norm.tzinfo == timezone.utc

    ts_ms = 1787652000000  # ms
    assert normalize_timestamp(ts_ms) == ts_norm

    ts_us = 1787652000000000  # us
    assert normalize_timestamp(ts_us) == ts_norm


def test_normalize_timestamp_invalid():
    # Naive datetime
    with pytest.raises(InvalidTimestampError):
        normalize_timestamp(datetime(2026, 8, 26, 10, 0, 0))

    # Negative epoch
    with pytest.raises(InvalidTimestampError):
        normalize_timestamp(-100)

    # NaN / Infinity
    with pytest.raises(InvalidTimestampError):
        normalize_timestamp(float("nan"))

    with pytest.raises(InvalidTimestampError):
        normalize_timestamp(float("inf"))

    # Invalid ISO string
    with pytest.raises(InvalidTimestampError):
        normalize_timestamp("invalid-date")

    # Unsupported type
    with pytest.raises(InvalidTimestampError):
        normalize_timestamp([2026, 8, 26])
