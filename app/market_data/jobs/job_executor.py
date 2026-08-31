from collections.abc import Callable
from typing import Any

from app.market_data.jobs.collection_job import CollectionJob
from app.market_data.jobs.collection_result import CollectionResult


class CollectionJobExecutor:
    """
    Executes CollectionJob instances using an incremental collector.

    The executor deliberately depends on a factory/callable instead of
    constructing exchange infrastructure itself. This keeps orchestration
    separate from exchange and storage implementation details.
    """

    def __init__(
        self,
        collector_factory: Callable[[CollectionJob], Any],
    ) -> None:
        if not callable(collector_factory):
            raise TypeError(
                "collector_factory must be callable"
            )

        self._collector_factory = collector_factory

    def execute(
        self,
        job: CollectionJob,
    ) -> CollectionResult:
        """
        Execute one collection job.

        Exceptions are converted into failed CollectionResult objects so
        one failed exchange/job does not automatically stop the scheduler.
        """

        try:
            collector = self._collector_factory(job)

            candles = collector.collect(
                symbol=job.symbol,
                timeframe=job.timeframe,
                page_size=job.page_size,
            )

            if candles is None:
                candles = []

            return CollectionResult(
                job=job,
                candles_collected=len(candles),
                success=True,
            )

        except Exception as exc:
            return CollectionResult(
                job=job,
                candles_collected=0,
                success=False,
                error=str(exc),
            )