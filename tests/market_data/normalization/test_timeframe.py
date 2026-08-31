import pytest
from app.market_data.exceptions import InvalidTimeframeError
from app.market_data.normalization.timeframe import normalize_timeframe


def test_normalize_timeframe_valid():
    assert normalize_timeframe("15m") == "15m"
    assert normalize_timeframe("15") == "15m"
    assert normalize_timeframe("15min") == "15m"

    assert normalize_timeframe("1h") == "1h"
    assert normalize_timeframe("60") == "1h"
    assert normalize_timeframe("1H") == "1h"

    assert normalize_timeframe("4h") == "4h"
    assert normalize_timeframe("240") == "4h"
    assert normalize_timeframe("4H") == "4h"

    assert normalize_timeframe("1d") == "1d"
    assert normalize_timeframe("1440") == "1d"
    assert normalize_timeframe("1D") == "1d"
    assert normalize_timeframe("1day") == "1d"

    assert normalize_timeframe(15) == "15m"
    assert normalize_timeframe(60) == "1h"
    assert normalize_timeframe(240) == "4h"
    assert normalize_timeframe(1440) == "1d"


def test_normalize_timeframe_invalid():
    with pytest.raises(InvalidTimeframeError):
        normalize_timeframe("5m")

    with pytest.raises(InvalidTimeframeError):
        normalize_timeframe("30m")

    with pytest.raises(InvalidTimeframeError):
        normalize_timeframe("")

    with pytest.raises(InvalidTimeframeError):
        normalize_timeframe(None)
