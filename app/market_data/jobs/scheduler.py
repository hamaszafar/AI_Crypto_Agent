from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from app.market_data.jobs.collection_job import CollectionJob
from app.market_data.jobs.collection_result import CollectionResult
from app.market_data.jobs.job_executor import CollectionJobExecutor


@dataclass(frozen=True)
class SchedulerConfig:
    """
    Configuration for the collection scheduler.
    """

    interval_seconds: int

    def __post_init__(self) -> None:
        if self.interval_seconds <= 0:
            raise ValueError(
                "interval_seconds must be greater than zero"
            )


class CollectionScheduler:
    """
    Coordinates repeated execution of market-data collection jobs.

    The scheduler itself does not know how exchanges work.
    It only decides which jobs should run and when.
    """

    def __init__(
        self,
        executor: CollectionJobExecutor,
        jobs: list[CollectionJob],
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not jobs:
            raise ValueError("jobs must not be empty")

        self._executor = executor
        self._jobs = list(jobs)

        self._clock = clock or (
            lambda: datetime.now(timezone.utc)
        )

        self._next_run: dict[
            tuple[str, str, str],
            datetime,
        ] = {}

    @property
    def jobs(self) -> tuple[CollectionJob, ...]:
        return tuple(self._jobs)

    def run_once(self) -> list[CollectionResult]:
        """
        Execute all configured jobs once.
        """

        results: list[CollectionResult] = []

        for job in self._jobs:
            result = self._executor.execute(job)
            results.append(result)

        return results

    def run_due_jobs(
        self,
        now: datetime | None = None,
    ) -> list[CollectionResult]:
        """
        Execute jobs whose scheduled time has arrived.
        """

        current_time = now or self._clock()

        results: list[CollectionResult] = []

        for job in self._jobs:
            next_run = self._next_run.get(job.key)

            if next_run is None or current_time >= next_run:
                result = self._executor.execute(job)
                results.append(result)

        return results

    def schedule_job(
        self,
        job: CollectionJob,
        interval_seconds: int,
        now: datetime | None = None,
    ) -> None:
        """
        Schedule a job for execution.

        The first execution is immediately eligible.
        """

        if interval_seconds <= 0:
            raise ValueError(
                "interval_seconds must be greater than zero"
            )

        if job not in self._jobs:
            self._jobs.append(job)

        current_time = now or self._clock()

        self._next_run[job.key] = (
            current_time + timedelta(
                seconds=interval_seconds
            )
        )

    def mark_completed(
        self,
        job: CollectionJob,
        interval_seconds: int,
        now: datetime | None = None,
    ) -> None:
        """
        Schedule the next execution after a completed run.
        """

        if interval_seconds <= 0:
            raise ValueError(
                "interval_seconds must be greater than zero"
            )

        current_time = now or self._clock()

        self._next_run[job.key] = (
            current_time + timedelta(
                seconds=interval_seconds
            )
        )

    def next_run(
        self,
        job: CollectionJob,
    ) -> datetime | None:
        return self._next_run.get(job.key)

    def clear_schedule(self) -> None:
        self._next_run.clear()