from datetime import datetime, timezone
from typing import Callable

from app.exchanges.factory import ExchangeFactory
from app.market_data.config import CollectionConfig
from app.market_data.freshness import FreshnessMonitor, FreshnessResult
from app.market_data.gap_detector import GapDetector
from app.market_data.gap_recovery import GapRecoveryService
from app.market_data.health import CollectionHealthTracker
from app.market_data.historical import HistoricalMarketData
from app.market_data.historical_downloader import HistoricalDownloader
from app.market_data.incremental_collector import IncrementalCollector
from app.market_data.jobs.collection_job import CollectionJob
from app.market_data.jobs.collection_result import CollectionResult
from app.market_data.jobs.job_executor import CollectionJobExecutor
from app.market_data.jobs.scheduler import CollectionScheduler
from app.market_data.storage import MarketDataStorage
from app.storage.repositories.memory_candle_repository import MemoryCandleRepository
from app.storage.service import StorageService


class CollectionPipeline:
    """
    End-to-End Orchestrator for Phase 2B Data Collection Pipeline.

    Integrates:
    - CollectionConfig & CollectionJobs
    - CollectionScheduler & CollectionJobExecutor
    - IncrementalCollector & HistoricalDownloader
    - MarketDataStorage & StorageService
    - GapDetector & GapRecoveryService
    - FreshnessMonitor & CollectionHealthTracker
    """

    def __init__(
        self,
        config: CollectionConfig,
        storage: MarketDataStorage | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.config = config
        self.clock = clock or (lambda: datetime.now(timezone.utc))

        if storage is None:
            repository = MemoryCandleRepository()
            storage_service = StorageService(repository)
            self.storage = MarketDataStorage(storage_service)
        else:
            self.storage = storage

        self.health_tracker = CollectionHealthTracker()
        self.freshness_monitor = FreshnessMonitor()

        self.jobs = self.config.to_jobs()
        if not self.jobs:
            raise ValueError("CollectionConfig generated no jobs")

        self.executor = CollectionJobExecutor(
            collector_factory=self._make_collector
        )

        self.scheduler = CollectionScheduler(
            executor=self.executor,
            jobs=list(self.jobs),
            clock=self.clock,
        )

    def _make_collector(self, job: CollectionJob) -> IncrementalCollector:
        exchange_instance = ExchangeFactory.create(job.exchange)
        return IncrementalCollector(
            exchange=exchange_instance,
            storage_service=self.storage,
        )

    def run_scheduled_cycle(self) -> list[CollectionResult]:
        """
        Runs one cycle of due jobs via scheduler, tracking health and freshness.
        """
        now = self.clock()
        results = self.scheduler.run_due_jobs(now=now)

        for result in results:
            job = result.job
            if result.success:
                latest_candle = self.storage.get_latest_candle(
                    exchange=job.exchange,
                    symbol=job.symbol,
                    timeframe=job.timeframe,
                )
                latest_ts = latest_candle.timestamp if latest_candle else None

                self.health_tracker.record_success(
                    exchange=job.exchange,
                    candles_collected=result.candles_collected,
                    latest_candle_time=latest_ts,
                    now=now,
                )
            else:
                self.health_tracker.record_failure(
                    exchange=job.exchange,
                    error=result.error,
                    now=now,
                )

        return results

    def bootstrap_historical(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime | None = None,
    ) -> dict[str, int]:
        """
        Bootstrap historical candles for all configured exchanges.
        """
        summary = {}
        historical_market_data = HistoricalMarketData(
            self.storage.storage_service._repository
        )

        for ex in self.config.exchanges:
            exchange_instance = ExchangeFactory.create(ex)
            downloader = HistoricalDownloader(
                exchange=exchange_instance,
                historical_data=historical_market_data,
            )
            stored = downloader.download(
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_time,
                end_time=end_time or self.clock(),
            )
            summary[ex] = len(stored)
        return summary

    def evaluate_freshness(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
    ) -> FreshnessResult:
        """
        Evaluate market data freshness for an exchange/symbol/timeframe.
        """
        latest_candle = self.storage.get_latest_candle(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
        )
        latest_ts = latest_candle.timestamp if latest_candle else None
        return self.freshness_monitor.evaluate(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            latest_timestamp=latest_ts,
            now=self.clock(),
        )

    def recover_gaps(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
    ) -> int:
        """
        Detect and fill data gaps for an exchange/symbol/timeframe.
        """
        candles = self.storage.get_candles(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
        )
        gaps = GapDetector.detect_gaps(candles, timeframe)
        if not gaps:
            return 0

        exchange_instance = ExchangeFactory.create(exchange)
        historical_market_data = HistoricalMarketData(
            self.storage.storage_service._repository
        )
        downloader = HistoricalDownloader(
            exchange=exchange_instance,
            historical_data=historical_market_data,
        )
        recovery_service = GapRecoveryService(downloader)
        recovered = recovery_service.recover_gaps(symbol, timeframe, gaps)
        return len(recovered)
