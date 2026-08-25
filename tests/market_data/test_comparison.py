from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.market_data.comparison import (
    CrossExchangeComparator,
    ComparisonResult,
    ExchangePrice,
    ExchangeVolume,
)
from app.market_data.models import MarketCandle


TIMESTAMP = datetime(
    2026,
    8,
    22,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_candle(
    exchange: str,
    close: str = "100",
    volume: str = "10",
    symbol: str = "BTC/USDT",
    timeframe: str = "15m",
) -> MarketCandle:
    return MarketCandle(
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        timestamp=TIMESTAMP,
        open=Decimal("99"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal(close),
        volume=Decimal(volume),
    )


def make_candles() -> dict[str, MarketCandle]:
    return {
        "binance": make_candle(
            "binance",
            close="100",
            volume="1000",
        ),
        "bybit": make_candle(
            "bybit",
            close="102",
            volume="1200",
        ),
        "okx": make_candle(
            "okx",
            close="101",
            volume="1100",
        ),
    }


def test_compare_returns_comparison_result():
    comparator = CrossExchangeComparator()

    result = comparator.compare(make_candles())

    assert isinstance(result, ComparisonResult)


def test_symbol_is_preserved():
    comparator = CrossExchangeComparator()

    result = comparator.compare(make_candles())

    assert result.symbol == "BTC/USDT"


def test_timeframe_is_preserved():
    comparator = CrossExchangeComparator()

    result = comparator.compare(make_candles())

    assert result.timeframe == "15m"


def test_timestamp_is_preserved():
    comparator = CrossExchangeComparator()

    result = comparator.compare(make_candles())

    assert result.timestamp == TIMESTAMP


def test_exchange_count():
    comparator = CrossExchangeComparator()

    result = comparator.compare(make_candles())

    assert result.exchange_count == 3


def test_prices_are_collected():
    comparator = CrossExchangeComparator()

    result = comparator.compare(make_candles())

    assert result.prices == (
        ExchangePrice(
            exchange="binance",
            price=Decimal("100"),
        ),
        ExchangePrice(
            exchange="bybit",
            price=Decimal("102"),
        ),
        ExchangePrice(
            exchange="okx",
            price=Decimal("101"),
        ),
    )


def test_volumes_are_collected():
    comparator = CrossExchangeComparator()

    result = comparator.compare(make_candles())

    assert result.volumes == (
        ExchangeVolume(
            exchange="binance",
            volume=Decimal("1000"),
        ),
        ExchangeVolume(
            exchange="bybit",
            volume=Decimal("1200"),
        ),
        ExchangeVolume(
            exchange="okx",
            volume=Decimal("1100"),
        ),
    )


def test_highest_price():
    comparator = CrossExchangeComparator()

    result = comparator.compare(make_candles())

    assert result.highest_price == Decimal("102")


def test_lowest_price():
    comparator = CrossExchangeComparator()

    result = comparator.compare(make_candles())

    assert result.lowest_price == Decimal("100")


def test_price_difference():
    comparator = CrossExchangeComparator()

    result = comparator.compare(make_candles())

    assert result.price_difference == Decimal("2")


def test_price_difference_percent():
    comparator = CrossExchangeComparator()

    result = comparator.compare(make_candles())

    assert result.price_difference_percent == Decimal("2")


def test_spread_matches_price_difference():
    comparator = CrossExchangeComparator()

    result = comparator.compare(make_candles())

    assert result.spread == Decimal("2")


def test_spread_percent_matches_price_difference_percent():
    comparator = CrossExchangeComparator()

    result = comparator.compare(make_candles())

    assert result.spread_percent == Decimal("2")


def test_highest_volume():
    comparator = CrossExchangeComparator()

    result = comparator.compare(make_candles())

    assert result.highest_volume == Decimal("1200")


def test_lowest_volume():
    comparator = CrossExchangeComparator()

    result = comparator.compare(make_candles())

    assert result.lowest_volume == Decimal("1000")


def test_volume_difference():
    comparator = CrossExchangeComparator()

    result = comparator.compare(make_candles())

    assert result.volume_difference == Decimal("200")


def test_volume_difference_percent():
    comparator = CrossExchangeComparator()

    result = comparator.compare(make_candles())

    assert result.volume_difference_percent == Decimal("20")


def test_empty_candles_are_rejected():
    comparator = CrossExchangeComparator()

    with pytest.raises(ValueError):
        comparator.compare({})


def test_different_symbols_are_rejected():
    candles = make_candles()

    candles["bybit"] = make_candle(
        "bybit",
        symbol="ETH/USDT",
    )

    comparator = CrossExchangeComparator()

    with pytest.raises(ValueError):
        comparator.compare(candles)


def test_different_timeframes_are_rejected():
    candles = make_candles()

    candles["bybit"] = make_candle(
        "bybit",
        timeframe="1h",
    )

    comparator = CrossExchangeComparator()

    with pytest.raises(ValueError):
        comparator.compare(candles)


def test_different_timestamps_are_rejected():
    candles = make_candles()

    candles["bybit"] = MarketCandle(
        exchange="bybit",
        symbol="BTC/USDT",
        timeframe="15m",
        timestamp=datetime(
            2026,
            8,
            22,
            12,
            15,
            tzinfo=timezone.utc,
        ),
        open=Decimal("99"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("102"),
        volume=Decimal("1200"),
    )

    comparator = CrossExchangeComparator()

    with pytest.raises(ValueError):
        comparator.compare(candles)


def test_duplicate_exchange_is_rejected():
    candles = {
        "binance": make_candle(
            "binance",
            close="100",
        ),
        "other": make_candle(
            "binance",
            close="101",
        ),
    }

    comparator = CrossExchangeComparator()

    with pytest.raises(ValueError):
        comparator.compare(candles)