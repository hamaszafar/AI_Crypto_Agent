import pytest

from app.market_data.jobs.collection_job import CollectionJob


def test_collection_job_stores_values():
    job = CollectionJob(
        exchange="Binance",
        symbol="BTC/USDT",
        timeframe="15m",
    )

    assert job.exchange == "binance"
    assert job.symbol == "BTC/USDT"
    assert job.timeframe == "15m"
    assert job.page_size == 100


def test_collection_job_is_immutable():
    job = CollectionJob(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
    )

    with pytest.raises(AttributeError):
        job.exchange = "bybit"


def test_exchange_must_not_be_empty():
    with pytest.raises(ValueError):
        CollectionJob(
            exchange="",
            symbol="BTC/USDT",
            timeframe="15m",
        )


def test_symbol_must_not_be_empty():
    with pytest.raises(ValueError):
        CollectionJob(
            exchange="binance",
            symbol="",
            timeframe="15m",
        )


def test_timeframe_must_not_be_empty():
    with pytest.raises(ValueError):
        CollectionJob(
            exchange="binance",
            symbol="BTC/USDT",
            timeframe="",
        )


def test_page_size_must_be_positive():
    with pytest.raises(ValueError):
        CollectionJob(
            exchange="binance",
            symbol="BTC/USDT",
            timeframe="15m",
            page_size=0,
        )


def test_job_key():
    job = CollectionJob(
        exchange="Binance",
        symbol="btc/usdt",
        timeframe="15M",
    )

    assert job.key == (
        "binance",
        "BTC/USDT",
        "15m",
    )
    assert job.key_str == "binance:BTC/USDT:15m"


def test_job_normalization_and_whitespace():
    job = CollectionJob(
        exchange="  ByBit  ",
        symbol=" eth/usdt ",
        timeframe=" 1H ",
    )
    assert job.exchange == "bybit"
    assert job.symbol == "ETH/USDT"
    assert job.timeframe == "1h"
    assert job.key_str == "bybit:ETH/USDT:1h"