from dataclasses import dataclass, field
from datetime import datetime
from typing import FrozenSet, Iterable

from app.exchanges.factory import ExchangeFactory

SUPPORTED_TIMEFRAMES: FrozenSet[str] = frozenset({"15m", "1h", "4h", "1d"})

DEFAULT_COLLECTION_INTERVALS: dict[str, int] = {
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}


@dataclass(frozen=True)
class RetrySettings:
    """
    Configuration for job execution retries and backoff.
    """

    max_retries: int = 3
    backoff_factor: float = 1.0
    initial_delay: float = 1.0

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.backoff_factor < 0:
            raise ValueError("backoff_factor must be non-negative")
        if self.initial_delay < 0:
            raise ValueError("initial_delay must be non-negative")


@dataclass(frozen=True)
class RateLimitSettings:
    """
    Configuration for rate limiting exchange API calls.
    """

    requests_per_minute: int = 600
    requests_per_second: int | None = None
    retry_after_seconds: float = 1.0

    def __post_init__(self) -> None:
        if self.requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be greater than zero")
        if self.requests_per_second is not None and self.requests_per_second <= 0:
            raise ValueError("requests_per_second must be greater than zero")
        if self.retry_after_seconds <= 0:
            raise ValueError("retry_after_seconds must be greater than zero")


@dataclass(frozen=True)
class CollectionConfig:
    """
    Configuration layer for controlling crypto market-data collection.
    """

    exchanges: tuple[str, ...]
    symbols: tuple[str, ...]
    timeframes: tuple[str, ...]
    page_size: int = 100
    start_time: datetime | None = None
    end_time: datetime | None = None
    collection_intervals: dict[str, int] = field(
        default_factory=lambda: dict(DEFAULT_COLLECTION_INTERVALS)
    )
    retry_settings: RetrySettings = field(default_factory=RetrySettings)
    rate_limit_settings: RateLimitSettings = field(default_factory=RateLimitSettings)

    def __init__(
        self,
        exchanges: Iterable[str],
        symbols: Iterable[str],
        timeframes: Iterable[str],
        page_size: int = 100,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        collection_intervals: dict[str, int] | None = None,
        retry_settings: RetrySettings | None = None,
        rate_limit_settings: RateLimitSettings | None = None,
    ) -> None:
        # Validate and normalize exchanges
        ex_list = list(exchanges) if exchanges is not None else []
        if not ex_list:
            raise ValueError("exchanges must not be empty")

        available_exchanges = set(ExchangeFactory.available())
        normalized_exchanges: list[str] = []
        for ex in ex_list:
            if not isinstance(ex, str) or not ex.strip():
                raise ValueError(f"Invalid exchange name: {ex}")
            norm_ex = ex.strip().lower()
            if norm_ex not in available_exchanges:
                raise ValueError(f"Unsupported exchange: {ex}")
            normalized_exchanges.append(norm_ex)

        # Validate and normalize symbols
        sym_list = list(symbols) if symbols is not None else []
        if not sym_list:
            raise ValueError("symbols must not be empty")

        normalized_symbols: list[str] = []
        for sym in sym_list:
            if not isinstance(sym, str) or not sym.strip():
                raise ValueError(f"Invalid symbol: {sym}")
            norm_sym = sym.strip().upper()
            parts = norm_sym.split("/")
            if len(parts) != 2 or not parts[0] or not parts[1]:
                raise ValueError(f"Unsupported symbol format: {sym}")
            normalized_symbols.append(norm_sym)

        # Validate and normalize timeframes
        tf_list = list(timeframes) if timeframes is not None else []
        if not tf_list:
            raise ValueError("timeframes must not be empty")

        normalized_timeframes: list[str] = []
        for tf in tf_list:
            if not isinstance(tf, str) or not tf.strip():
                raise ValueError(f"Invalid timeframe: {tf}")
            norm_tf = tf.strip().lower()
            if norm_tf not in SUPPORTED_TIMEFRAMES:
                raise ValueError(f"Unsupported timeframe: {tf}")
            normalized_timeframes.append(norm_tf)

        # Validate page size
        if page_size <= 0:
            raise ValueError("page_size must be greater than zero")

        # Validate historical range
        if start_time and end_time and start_time > end_time:
            raise ValueError("start_time must be before or equal to end_time")

        # Validate collection intervals
        intervals = (
            dict(collection_intervals)
            if collection_intervals is not None
            else dict(DEFAULT_COLLECTION_INTERVALS)
        )
        for tf_key, val in intervals.items():
            if tf_key not in SUPPORTED_TIMEFRAMES:
                raise ValueError(f"Unsupported timeframe in collection_intervals: {tf_key}")
            if val <= 0:
                raise ValueError(f"Collection interval for {tf_key} must be greater than zero")

        ret_settings = retry_settings or RetrySettings()
        rl_settings = rate_limit_settings or RateLimitSettings()

        object.__setattr__(self, "exchanges", tuple(normalized_exchanges))
        object.__setattr__(self, "symbols", tuple(normalized_symbols))
        object.__setattr__(self, "timeframes", tuple(normalized_timeframes))
        object.__setattr__(self, "page_size", page_size)
        object.__setattr__(self, "start_time", start_time)
        object.__setattr__(self, "end_time", end_time)
        object.__setattr__(self, "collection_intervals", intervals)
        object.__setattr__(self, "retry_settings", ret_settings)
        object.__setattr__(self, "rate_limit_settings", rl_settings)

    def to_jobs(self) -> list:
        """Generate CollectionJob instances for all configured combinations."""
        from app.market_data.jobs.collection_job import CollectionJob

        jobs: list[CollectionJob] = []
        for exchange in self.exchanges:
            for symbol in self.symbols:
                for timeframe in self.timeframes:
                    jobs.append(
                        CollectionJob(
                            exchange=exchange,
                            symbol=symbol,
                            timeframe=timeframe,
                            page_size=self.page_size,
                        )
                    )
        return jobs
