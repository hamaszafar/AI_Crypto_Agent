from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"


@dataclass
class ExchangeHealthRecord:
    """
    Health metrics and status tracking for an exchange.
    """

    exchange: str
    status: HealthStatus = HealthStatus.HEALTHY
    last_success: datetime | None = None
    last_failure: datetime | None = None
    failure_count: int = 0
    total_collected: int = 0
    latest_candle_time: datetime | None = None


class CollectionHealthTracker:
    """
    Tracks collection health across multiple exchanges and collection jobs.
    """

    def __init__(
        self,
        degraded_threshold: int = 3,
        unhealthy_threshold: int = 5,
    ) -> None:
        if degraded_threshold < 1:
            raise ValueError("degraded_threshold must be >= 1")
        if unhealthy_threshold <= degraded_threshold:
            raise ValueError("unhealthy_threshold must be greater than degraded_threshold")

        self.degraded_threshold = degraded_threshold
        self.unhealthy_threshold = unhealthy_threshold
        self._records: dict[str, ExchangeHealthRecord] = {}

    def record_success(
        self,
        exchange: str,
        candles_collected: int = 0,
        latest_candle_time: datetime | None = None,
        now: datetime | None = None,
    ) -> None:
        record = self._get_or_create(exchange)
        record.last_success = now or datetime.now(timezone.utc)
        record.failure_count = 0
        record.total_collected += candles_collected
        if latest_candle_time is not None:
            record.latest_candle_time = latest_candle_time
        record.status = HealthStatus.HEALTHY

    def record_failure(
        self,
        exchange: str,
        error: str | None = None,
        now: datetime | None = None,
    ) -> None:
        record = self._get_or_create(exchange)
        record.last_failure = now or datetime.now(timezone.utc)
        record.failure_count += 1

        if record.failure_count >= self.unhealthy_threshold:
            record.status = HealthStatus.UNHEALTHY
        elif record.failure_count >= self.degraded_threshold:
            record.status = HealthStatus.DEGRADED

    def get_health(self, exchange: str) -> ExchangeHealthRecord:
        return self._get_or_create(exchange)

    def all_health(self) -> dict[str, ExchangeHealthRecord]:
        return dict(self._records)

    def _get_or_create(self, exchange: str) -> ExchangeHealthRecord:
        ex = exchange.strip().lower()
        if ex not in self._records:
            self._records[ex] = ExchangeHealthRecord(exchange=ex)
        return self._records[ex]
