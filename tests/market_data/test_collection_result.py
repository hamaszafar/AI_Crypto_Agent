import pytest

from app.market_data.jobs.collection_job import CollectionJob
from app.market_data.jobs.collection_result import CollectionResult


@pytest.fixture
def job():
    return CollectionJob(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
    )


def test_successful_result(job):
    result = CollectionResult(
        job=job,
        candles_collected=10,
        success=True,
    )

    assert result.success is True
    assert result.candles_collected == 10
    assert result.error is None


def test_failed_result(job):
    result = CollectionResult(
        job=job,
        candles_collected=0,
        success=False,
        error="API unavailable",
    )

    assert result.success is False
    assert result.error == "API unavailable"


def test_negative_candle_count_is_rejected(job):
    with pytest.raises(ValueError):
        CollectionResult(
            job=job,
            candles_collected=-1,
            success=True,
        )


def test_success_cannot_have_error(job):
    with pytest.raises(ValueError):
        CollectionResult(
            job=job,
            candles_collected=1,
            success=True,
            error="unexpected",
        )


def test_failure_requires_error(job):
    with pytest.raises(ValueError):
        CollectionResult(
            job=job,
            candles_collected=0,
            success=False,
        )