import math
from decimal import Decimal, InvalidOperation
from app.market_data.exceptions import (
    CandleValidationError,
    InvalidOHLCError,
    InvalidVolumeError,
)


def _raise_field_error(field_name: str, message: str, cause: Exception | None = None) -> None:
    if field_name == "volume":
        exc = InvalidVolumeError(message)
    elif field_name in ("open", "high", "low", "close"):
        exc = InvalidOHLCError(message)
    else:
        exc = CandleValidationError(message)

    if cause:
        raise exc from cause
    raise exc


def normalize_decimal(
    value: object,
    field_name: str = "numeric_value",
    allow_zero: bool = False,
    allow_negative: bool = False,
) -> Decimal:
    """
    Safely convert numeric input to Decimal and validate.

    Inputs supported:
    - int
    - float (converted via str(value))
    - Decimal
    - numeric string

    Rejects:
    - NaN / Infinity
    - Empty or malformed strings
    - Negative values (unless allow_negative=True)
    - Zero values (unless allow_zero=True)
    """
    if value is None:
        _raise_field_error(field_name, f"{field_name} cannot be None")

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            _raise_field_error(field_name, f"{field_name} cannot be NaN or Infinity: {value!r}")
        dec_val = Decimal(str(value))

    elif isinstance(value, (int, str)):
        if isinstance(value, str):
            text = value.strip()
            if not text:
                _raise_field_error(field_name, f"{field_name} string cannot be empty")
            try:
                dec_val = Decimal(text)
            except InvalidOperation as exc:
                _raise_field_error(field_name, f"Invalid numeric string for {field_name}: {value!r}", cause=exc)
        else:
            dec_val = Decimal(value)

    elif isinstance(value, Decimal):
        dec_val = value

    else:
        _raise_field_error(
            field_name,
            f"Unsupported type for {field_name}: {type(value).__name__}"
        )

    if not dec_val.is_finite():
        _raise_field_error(field_name, f"{field_name} must be finite: {dec_val!r}")

    if not allow_negative and dec_val < Decimal("0"):
        _raise_field_error(field_name, f"{field_name} cannot be negative: {dec_val!r}")

    if not allow_zero and dec_val == Decimal("0"):
        _raise_field_error(field_name, f"{field_name} cannot be zero: {dec_val!r}")

    return dec_val
