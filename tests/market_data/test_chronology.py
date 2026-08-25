from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.market_data.models import MarketCandle
from app.market_data.validator import (
    find_out_of_order_candles,
    is_chronological,
    is_strictly_chronological,
    sort_chronologically,
)


BASE_TIME = datetime(
    2026,
    8,
    22,
    12,
    0,
    tzinfo=timezone.utc,
)


def make_candle(minutes: int) -> MarketCandle:
    timestamp = BASE_TIME + timedelta(minutes=minutes)

    return MarketCandle(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
        timestamp=timestamp,
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
        volume=Decimal("100"),
    )


def test_already_chronological_candles_remain_in_order():
    candles = [
        make_candle(0),
        make_candle(15),
        make_candle(30),
    ]

    result = sort_chronologically(candles)

    assert result == candles


def test_out_of_order_candles_are_sorted_oldest_first():
    newest = make_candle(30)
    oldest = make_candle(0)
    middle = make_candle(15)

    result = sort_chronologically(
        [newest, oldest, middle]
    )

    assert result == [
        oldest,
        middle,
        newest,
    ]


def test_sort_does_not_modify_input_list():
    newest = make_candle(30)
    oldest = make_candle(0)

    candles = [newest, oldest]

    result = sort_chronologically(candles)

    assert candles == [newest, oldest]
    assert result == [oldest, newest]


def test_chronological_sequence_is_valid():
    candles = [
        make_candle(0),
        make_candle(15),
        make_candle(30),
    ]

    assert is_chronological(candles) is True


def test_out_of_order_sequence_is_not_chronological():
    candles = [
        make_candle(0),
        make_candle(30),
        make_candle(15),
    ]

    assert is_chronological(candles) is False


def test_equal_timestamps_are_allowed_by_non_strict_check():
    candles = [
        make_candle(0),
        make_candle(0),
        make_candle(15),
    ]

    assert is_chronological(candles) is True


def test_strict_chronological_sequence_is_valid():
    candles = [
        make_candle(0),
        make_candle(15),
        make_candle(30),
    ]

    assert is_strictly_chronological(candles) is True


def test_equal_timestamps_fail_strict_chronological_check():
    candles = [
        make_candle(0),
        make_candle(0),
        make_candle(15),
    ]

    assert is_strictly_chronological(candles) is False


def test_out_of_order_sequence_fails_strict_check():
    candles = [
        make_candle(0),
        make_candle(30),
        make_candle(15),
    ]

    assert is_strictly_chronological(candles) is False


def test_find_out_of_order_candles():
    first = make_candle(0)
    second = make_candle(30)
    third = make_candle(15)
    fourth = make_candle(45)

    result = find_out_of_order_candles(
        [first, second, third, fourth]
    )

    assert result == [third]


def test_multiple_out_of_order_candles_are_found():
    first = make_candle(30)
    second = make_candle(15)
    third = make_candle(45)
    fourth = make_candle(0)

    result = find_out_of_order_candles(
        [first, second, third, fourth]
    )

    assert result == [second, fourth]


def test_empty_collection_is_chronological():
    assert is_chronological([]) is True


def test_empty_collection_is_strictly_chronological():
    assert is_strictly_chronological([]) is True


def test_empty_collection_has_no_out_of_order_candles():
    assert find_out_of_order_candles([]) == []


def test_single_candle_is_chronological():
    candle = make_candle(0)

    assert is_chronological([candle]) is True
    assert is_strictly_chronological([candle]) is True


def test_sort_empty_collection():
    assert sort_chronologically([]) == []
