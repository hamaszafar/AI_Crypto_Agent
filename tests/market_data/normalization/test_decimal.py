from decimal import Decimal
import pytest

from app.market_data.exceptions import CandleValidationError
from app.market_data.normalization.decimal import normalize_decimal


def test_normalize_decimal_valid():
    assert normalize_decimal(100) == Decimal("100")
    assert normalize_decimal(100.5) == Decimal("100.5")
    assert normalize_decimal("100.5") == Decimal("100.5")
    assert normalize_decimal(Decimal("100.5")) == Decimal("100.5")


def test_normalize_decimal_options():
    assert normalize_decimal(0, allow_zero=True) == Decimal("0")
    assert normalize_decimal(-5, allow_negative=True) == Decimal("-5")


def test_normalize_decimal_invalid():
    with pytest.raises(CandleValidationError):
        normalize_decimal(float("nan"))

    with pytest.raises(CandleValidationError):
        normalize_decimal(float("inf"))

    with pytest.raises(CandleValidationError):
        normalize_decimal("")

    with pytest.raises(CandleValidationError):
        normalize_decimal("abc")

    with pytest.raises(CandleValidationError):
        normalize_decimal(-10)

    with pytest.raises(CandleValidationError):
        normalize_decimal(0)
