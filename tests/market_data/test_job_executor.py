from app.market_data.jobs.collection_job import CollectionJob
from app.market_data.jobs.job_executor import CollectionJobExecutor


class FakeCollector:
    def collect(
        self,
        *,
        symbol,
        timeframe,
        page_size,
    ):
        return [
            object(),
            object(),
            object(),
        ]


class FailingCollector:
    def collect(
        self,
        *,
        symbol,
        timeframe,
        page_size,
    ):
        raise RuntimeError("exchange unavailable")


def make_job():
    return CollectionJob(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
    )


def test_executor_success():
    executor = CollectionJobExecutor(
        lambda job: FakeCollector()
    )

    result = executor.execute(make_job())

    assert result.success is True
    assert result.candles_collected == 3
    assert result.error is None


def test_executor_failure_is_captured():
    executor = CollectionJobExecutor(
        lambda job: FailingCollector()
    )

    result = executor.execute(make_job())

    assert result.success is False
    assert result.candles_collected == 0
    assert result.error == "exchange unavailable"


def test_executor_passes_job_to_factory():
    received = []

    def factory(job):
        received.append(job)
        return FakeCollector()

    executor = CollectionJobExecutor(factory)

    job = make_job()

    executor.execute(job)

    assert received == [job]


def test_none_result_is_treated_as_empty():
    class EmptyCollector:
        def collect(
            self,
            *,
            symbol,
            timeframe,
            page_size,
        ):
            return None

    executor = CollectionJobExecutor(
        lambda job: EmptyCollector()
    )

    result = executor.execute(make_job())

    assert result.success is True
    assert result.candles_collected == 0