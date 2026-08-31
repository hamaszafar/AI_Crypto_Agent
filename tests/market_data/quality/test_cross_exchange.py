from datetime import datetime, timezone
from decimal import Decimal

from app.market_data.models import MarketCandle
from app.market_data.quality.cross_exchange import CrossExchangeConsistency


def test_cross_exchange_consistency():
    ts = datetime(2026, 8, 26, 10, 0, tzinfo=timezone.utc)
    c_binance = MarketCandle(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
        timestamp=ts,
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50000"),
        volume=Decimal("10"),
    )

    c_bybit = MarketCandle(
        exchange="bybit",
        symbol="BTC/USDT",
        timeframe="15m",
        timestamp=ts,
        open=Decimal("50000"),
        high=Decimal("51000"),
        low=Decimal("49000"),
        close=Decimal("50100"),  # 0.2% price difference
        volume=Decimal("12"),
    )

    c_okx_deviated = MarketCandle(
        exchange="okx",
        symbol="BTC/USDT",
        timeframe="15m",
        timestamp=ts,
        open=Decimal("50000"),
        high=Decimal("56000"),
        low=Decimal("49000"),
        close=Decimal("55000"),  # 10% price difference from binance
        volume=Decimal("15"),
    )

    comparisons = CrossExchangeConsistency.compare_candles([c_binance, c_bybit], max_price_deviation_pct=Decimal("5.0"))
    assert len(comparisons) == 1
    assert not comparisons[0].is_deviated

    comparisons_dev = CrossExchangeConsistency.compare_candles([c_binance, c_bybit, c_okx_deviated], max_price_deviation_pct=Decimal("5.0"))
    assert len(comparisons_dev) == 1
    assert comparisons_dev[0].is_deviated
