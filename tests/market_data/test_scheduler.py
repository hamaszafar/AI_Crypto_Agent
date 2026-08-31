from datetime import datetime, timezone

import pytest

from app.market_data.jobs.collection_job import CollectionJob
from app.market_data.jobs.job_executor import CollectionJobExecutor
from app.market_data.jobs.scheduler import CollectionScheduler


class FakeCollector:
    def collect(
        self,
        *,
        symbol,
        timeframe,
        page_size,
    ):
        return [object(), object()]


def make_executor():
    return CollectionJobExecutor(
        lambda job: FakeCollector()
    )


def make_job(
    exchange="binance",
    symbol="BTC/USDT",
    timeframe="15m",
):
    return CollectionJob(
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
    )


def test_scheduler_requires_jobs():
    with pytest.raises(ValueError):
        CollectionScheduler(
            executor=make_executor(),
            jobs=[],
        )


def test_scheduler_stores_jobs():
    jobs = [
        make_job(),
        make_job(timeframe="1h"),
    ]

    scheduler = CollectionScheduler(
        executor=make_executor(),
        jobs=jobs,
    )

    assert scheduler.jobs == tuple(jobs)


def test_run_once_executes_all_jobs():
    jobs = [
        make_job(timeframe="15m"),
        make_job(timeframe="1h"),
        make_job(timeframe="4h"),
        make_job(timeframe="1D"),
    ]

    scheduler = CollectionScheduler(
        executor=make_executor(),
        jobs=jobs,
    )

    results = scheduler.run_once()

    assert len(results) == 4
    assert all(result.success for result in results)


def test_run_once_collects_candles():
    scheduler = CollectionScheduler(
        executor=make_executor(),
        jobs=[make_job()],
    )

    results = scheduler.run_once()

    assert results[0].candles_collected == 2


def test_schedule_job():
    scheduler = CollectionScheduler(
        executor=make_executor(),
        jobs=[make_job()],
    )

    now = datetime(
        2026,
        8,
        25,
        tzinfo=timezone.utc,
    )

    job = make_job()

    scheduler.schedule_job(
        job,
        interval_seconds=900,
        now=now,
    )

    assert scheduler.next_run(job) == (
        datetime(
            2026,
            8,
            25,
            0,
            15,
            tzinfo=timezone.utc,
        )
    )


def test_mark_completed_schedules_next_run():
    scheduler = CollectionScheduler(
        executor=make_executor(),
        jobs=[make_job()],
    )

    now = datetime(
        2026,
        8,
        25,
        tzinfo=timezone.utc,
    )

    job = make_job()

    scheduler.mark_completed(
        job,
        interval_seconds=3600,
        now=now,
    )

    assert scheduler.next_run(job) == (
        datetime(
            2026,
            8,
            25,
            1,
            0,
            tzinfo=timezone.utc,
        )
    )


def test_run_due_jobs_runs_unscheduled_job():
    job = make_job()

    scheduler = CollectionScheduler(
        executor=make_executor(),
        jobs=[job],
    )

    results = scheduler.run_due_jobs()

    assert len(results) == 1
    assert results[0].success is True


def test_run_due_jobs_does_not_run_before_schedule():
    job = make_job()

    scheduler = CollectionScheduler(
        executor=make_executor(),
        jobs=[job],
    )

    now = datetime(
        2026,
        8,
        25,
        tzinfo=timezone.utc,
    )

    scheduler.schedule_job(
        job,
        interval_seconds=900,
        now=now,
    )

    results = scheduler.run_due_jobs(
        now=now,
    )

    assert results == []


def test_run_due_jobs_runs_after_schedule():
    job = make_job()

    scheduler = CollectionScheduler(
        executor=make_executor(),
        jobs=[job],
    )

    now = datetime(
        2026,
        8,
        25,
        tzinfo=timezone.utc,
    )

    scheduler.schedule_job(
        job,
        interval_seconds=900,
        now=now,
    )

    later = datetime(
        2026,
        8,
        25,
        0,
        16,
        tzinfo=timezone.utc,
    )

    results = scheduler.run_due_jobs(
        now=later,
    )

    assert len(results) == 1
    assert results[0].success is True


def test_clear_schedule():
    job = make_job()

    scheduler = CollectionScheduler(
        executor=make_executor(),
        jobs=[job],
    )

    now = datetime(
        2026,
        8,
        25,
        tzinfo=timezone.utc,
    )

    scheduler.schedule_job(
        job,
        interval_seconds=900,
        now=now,
    )

    scheduler.clear_schedule()

    assert scheduler.next_run(job) is None