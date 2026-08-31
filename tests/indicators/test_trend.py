import pytest
from decimal import Decimal
from datetime import datetime, timezone
from app.indicators.input import IndicatorInput, IndicatorCandle
from app.indicators.trend.ma import SMAIndicator, EMAIndicator
from app.indicators.trend.macd import MACDIndicator

def make_candles(prices):
    candles = []
    for p in prices:
        candles.append(IndicatorCandle(
            timestamp=datetime(2026,1,1,tzinfo=timezone.utc),
            open=Decimal(p), high=Decimal(p), low=Decimal(p), close=Decimal(p), volume=Decimal("10")
        ))
    return IndicatorInput("ex", "sym", "1h", tuple(candles))

def test_sma():
    prices = ["10", "20", "30"]
    data = make_candles(prices)
    sma = SMAIndicator(3)
    res = sma.calculate(data)
    assert res.get("sma") == Decimal("20")

def test_ema():
    prices = ["10", "10", "10", "20"]
    data = make_candles(prices)
    ema = EMAIndicator(3)
    res = ema.calculate(data)
    # initial SMA of first 3 is 10.
    # next price is 20. multiplier = 2/(3+1) = 0.5
    # ema = (20 - 10) * 0.5 + 10 = 15
    assert res.get("ema") == Decimal("15")

def test_macd():
    # Provide exactly enough for MACD 2, 3, 2 -> min period = 3 + 2 = 5
    prices = ["10", "12", "14", "16", "18"]
    data = make_candles(prices)
    macd = MACDIndicator(2, 3, 2)
    res = macd.calculate(data)
    assert "macd" in res.values
    assert "signal" in res.values
    assert "histogram" in res.values
