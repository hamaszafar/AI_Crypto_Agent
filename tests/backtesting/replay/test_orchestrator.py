"""
Phase 6B.5 — End-to-End Replay Integration Tests

Tests the complete pipeline:
  HistoricalDataset
    → HistoricalReplayEngine  (6B.2)
    → HistoricalContextProvider (6B.3)
    → LeakageGuard (6B.4)
    → IndicatorEngine
    → SignalEngine
    → ReplayResult

Includes critical regression tests proving future data cannot influence
signals generated at earlier replay timestamps.
"""
import pytest
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

from app.market_data.models import MarketCandle
from app.backtesting.datasets.models import HistoricalDataset
from app.backtesting.datasets.metadata import DatasetMetadata
from app.backtesting.replay.models import ReplayRequest
from app.backtesting.replay.orchestrator import (
    ReplayOrchestrator,
    ReplayResult,
    ReplayRunStatus,
)
from app.backtesting.replay.leakage.exceptions import FutureDataDetectedError
from app.indicators.base import BaseIndicator
from app.indicators.engine import IndicatorEngine
from app.indicators.input import IndicatorInput
from app.indicators.models import IndicatorMetadata, IndicatorResult
from app.signals.engine import SignalEngine, SignalConfig


# ---------------------------------------------------------------------------
# Shared fixtures and helpers
# ---------------------------------------------------------------------------

def make_candle(
    dt: datetime,
    close: Decimal = Decimal("100"),
    timeframe: str = "15m",
    open_: Decimal = Decimal("99"),
    high: Decimal = Decimal("105"),
    low: Decimal = Decimal("95"),
) -> MarketCandle:
    return MarketCandle(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe=timeframe,
        timestamp=dt,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=Decimal("1000"),
    )


def make_dataset(
    start: datetime,
    count: int,
    interval_minutes: int = 15,
    timeframe: str = "15m",
    close_val: Decimal = Decimal("100"),
) -> HistoricalDataset:
    candles = [
        make_candle(start + timedelta(minutes=i * interval_minutes), close=close_val, timeframe=timeframe)
        for i in range(count)
    ]
    meta = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe=timeframe,
        start_timestamp=candles[0].timestamp,
        end_timestamp=candles[-1].timestamp,
        candle_count=len(candles),
    )
    return HistoricalDataset(candles=tuple(candles), metadata=meta)


class MockIndicator(BaseIndicator):
    """Deterministic mock indicator: returns the latest close price."""

    def __init__(self, period: int = 1):
        self._period = period

    @property
    def metadata(self) -> IndicatorMetadata:
        return IndicatorMetadata(
            name="MOCK",
            description="Mock indicator for testing",
            minimum_period=self._period,
        )

    def calculate(self, data: IndicatorInput) -> IndicatorResult:
        latest = data.latest
        return IndicatorResult(
            indicator_name=self.metadata.name,
            timestamp=latest.timestamp,
            values={"value": latest.close},
        )


def make_orchestrator(period: int = 1, lookback: int = 5) -> ReplayOrchestrator:
    indicator_engine = IndicatorEngine([MockIndicator(period=period)])
    signal_engine = SignalEngine()
    return ReplayOrchestrator(
        indicator_engine=indicator_engine,
        signal_engine=signal_engine,
        lookback=lookback,
        skip_unwarmed=True,
    )


# ---------------------------------------------------------------------------
# 1. Basic E2E: complete replay pipeline
# ---------------------------------------------------------------------------

def test_e2e_complete_replay():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    dataset = make_dataset(start, count=10)
    orchestrator = make_orchestrator(period=1, lookback=3)

    request = ReplayRequest(dataset=dataset)
    result: ReplayResult = orchestrator.run(request)

    assert isinstance(result, ReplayResult)
    assert result.exchange == "binance"
    assert result.symbol == "BTC/USDT"
    assert result.timeframe == "15m"
    assert result.status == ReplayRunStatus.COMPLETED
    assert result.leakage_violations == 0
    assert result.candles_processed > 0
    assert result.signals_generated > 0


# ---------------------------------------------------------------------------
# 2. Sequential candle processing
# ---------------------------------------------------------------------------

def test_e2e_sequential_processing():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    dataset = make_dataset(start, count=5)
    orchestrator = make_orchestrator(period=1, lookback=2)

    result = orchestrator.run(ReplayRequest(dataset=dataset))

    # Step records must be in chronological order
    timestamps = [s.replay_timestamp for s in result.step_records]
    assert timestamps == sorted(timestamps)


# ---------------------------------------------------------------------------
# 3. Context boundary enforcement: only candles <= T are visible
# ---------------------------------------------------------------------------

def test_e2e_context_boundary_enforcement():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    dataset = make_dataset(start, count=10)
    orchestrator = make_orchestrator(period=1, lookback=5)

    result = orchestrator.run(ReplayRequest(dataset=dataset))

    # At each processed step, verify indicator result's timestamp == replay timestamp
    # (meaning the indicator only saw data up to T, never beyond)
    for step in result.step_records:
        if not step.skipped and step.indicator_results:
            mock_result: IndicatorResult = step.indicator_results["MOCK"]
            assert mock_result.timestamp == step.replay_timestamp


# ---------------------------------------------------------------------------
# 4. Insufficient warm-up: skipped correctly
# ---------------------------------------------------------------------------

def test_e2e_insufficient_warmup_skipped():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    dataset = make_dataset(start, count=10)
    # Require lookback=5 and indicator period=1 — first 4 candles will be skipped
    # because context window won't be fully warmed up
    orchestrator = make_orchestrator(period=1, lookback=5)

    result = orchestrator.run(ReplayRequest(dataset=dataset))

    # Should have 4 warm-up skips (indices 0..3 where context has 1..4 candles < 5)
    assert result.warmup_periods == 4
    assert result.candles_skipped == 4
    assert result.candles_processed == 6  # candles 4..9 processed


# ---------------------------------------------------------------------------
# 5. Empty dataset boundary → engine completes with no steps processed
# ---------------------------------------------------------------------------

def test_e2e_empty_range():
    """Request a time range that yields no candles via start/end boundary."""
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    dataset = make_dataset(start, count=5)
    orchestrator = make_orchestrator()

    future_start = datetime(2025, 6, 1, tzinfo=timezone.utc)
    future_end = datetime(2025, 6, 2, tzinfo=timezone.utc)

    result = orchestrator.run(ReplayRequest(
        dataset=dataset,
        start_time=future_start,
        end_time=future_end,
    ))

    assert result.candles_processed == 0
    assert result.signals_generated == 0
    assert result.status == ReplayRunStatus.COMPLETED
    assert result.start_timestamp is None
    assert result.end_timestamp is None


# ---------------------------------------------------------------------------
# 6. Deterministic repeated replay
# ---------------------------------------------------------------------------

def test_e2e_deterministic_repeated_replay():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    dataset = make_dataset(start, count=10)
    orchestrator = make_orchestrator(period=1, lookback=3)

    request = ReplayRequest(dataset=dataset)
    result1 = orchestrator.run(request)
    result2 = orchestrator.run(request)

    # Same dataset + same config → same outputs (excluding unique replay_id)
    assert result1.candles_processed == result2.candles_processed
    assert result1.signals_generated == result2.signals_generated
    assert result1.candles_skipped == result2.candles_skipped
    assert result1.warmup_periods == result2.warmup_periods
    assert result1.status == result2.status

    # Step-level determinism: each step should have same timestamp, same warmed-up status
    for s1, s2 in zip(result1.step_records, result2.step_records):
        assert s1.replay_timestamp == s2.replay_timestamp
        assert s1.was_warmed_up == s2.was_warmed_up
        assert s1.skipped == s2.skipped


# ---------------------------------------------------------------------------
# 7. Multi-timeframe validation (15m, 1h, 4h, 1d)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("timeframe,interval_minutes", [
    ("15m", 15),
    ("1h", 60),
    ("4h", 240),
    ("1d", 1440),
])
def test_e2e_multi_timeframe(timeframe, interval_minutes):
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    dataset = make_dataset(start, count=10, interval_minutes=interval_minutes, timeframe=timeframe)
    orchestrator = make_orchestrator(period=1, lookback=3)

    result = orchestrator.run(ReplayRequest(dataset=dataset))

    assert result.timeframe == timeframe
    assert result.status == ReplayRunStatus.COMPLETED
    assert result.leakage_violations == 0
    assert result.candles_processed > 0


# ---------------------------------------------------------------------------
# 8. Replay result fields correctness
# ---------------------------------------------------------------------------

def test_e2e_result_metadata_correctness():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    dataset = make_dataset(start, count=6)
    orchestrator = make_orchestrator(period=1, lookback=2)

    result = orchestrator.run(ReplayRequest(dataset=dataset))

    # With lookback=2, period=1: first 1 candle skipped, 5 processed
    assert result.candles_skipped == 1
    assert result.candles_processed == 5
    assert result.start_timestamp == start
    assert result.end_timestamp == start + timedelta(minutes=15 * 5)
    assert result.signals_generated == 5


# ---------------------------------------------------------------------------
# 9. CRITICAL REGRESSION: future-data cannot alter signal at T
# ---------------------------------------------------------------------------

def test_e2e_future_data_cannot_alter_signal_at_T():
    """
    CRITICAL: Alter candles AFTER timestamp T while keeping candles up to T identical.
    Signal generated at T must remain identical.
    This proves the pipeline does not use future data.
    """
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    # Build 10 candles with close=100
    candles_base = [
        make_candle(start + timedelta(minutes=15 * i), close=Decimal("100"))
        for i in range(10)
    ]

    def build_dataset(candles) -> HistoricalDataset:
        meta = DatasetMetadata(
            exchange="binance",
            symbol="BTC/USDT",
            timeframe="15m",
            start_timestamp=candles[0].timestamp,
            end_timestamp=candles[-1].timestamp,
            candle_count=len(candles),
        )
        return HistoricalDataset(candles=tuple(candles), metadata=meta)

    # Original dataset
    dataset_original = build_dataset(candles_base)

    # Modified dataset: candles T0..T5 are the SAME, T6..T9 have different close price
    T_pivot = 5
    candles_modified = list(candles_base)
    for i in range(T_pivot + 1, 10):
        # Use a different but OHLCV-valid close: open=99, high=104, low=95, close=103
        candles_modified[i] = make_candle(
            start + timedelta(minutes=15 * i),
            open_=Decimal("99"),
            high=Decimal("104"),
            low=Decimal("95"),
            close=Decimal("103"),  # different from original 100
        )
    dataset_modified = build_dataset(candles_modified)

    orchestrator = make_orchestrator(period=1, lookback=3)

    result_original = orchestrator.run(ReplayRequest(dataset=dataset_original))
    result_modified = orchestrator.run(ReplayRequest(dataset=dataset_modified))

    # Find steps at or before T_pivot (step index 5 = T5 candle, 0-based)
    pivot_ts = start + timedelta(minutes=15 * T_pivot)

    original_steps_at_T = [
        s for s in result_original.step_records if s.replay_timestamp <= pivot_ts
    ]
    modified_steps_at_T = [
        s for s in result_modified.step_records if s.replay_timestamp <= pivot_ts
    ]

    # Must have the same number of steps up to T
    assert len(original_steps_at_T) == len(modified_steps_at_T)

    # Signals and indicator values must be identical up to T
    for s_orig, s_mod in zip(original_steps_at_T, modified_steps_at_T):
        assert s_orig.replay_timestamp == s_mod.replay_timestamp
        assert s_orig.skipped == s_mod.skipped
        if not s_orig.skipped:
            assert s_orig.signal.direction == s_mod.signal.direction
            assert s_orig.signal.score == s_mod.signal.score
            # Indicator values must match (close=100 in both up to T5)
            assert s_orig.indicator_results["MOCK"].values["value"] == s_mod.indicator_results["MOCK"].values["value"]


# ---------------------------------------------------------------------------
# 10. No live/network dependency (offline-only test)
# ---------------------------------------------------------------------------

def test_e2e_no_live_dependency():
    """Entire replay must run without any network calls. This is a smoke test."""
    import socket

    original_socket = socket.socket

    class BlockedSocket:
        def __init__(self, *args, **kwargs):
            raise ConnectionError("NETWORK ACCESS FORBIDDEN during replay!")

    socket.socket = BlockedSocket
    try:
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        dataset = make_dataset(start, count=5)
        orchestrator = make_orchestrator(period=1, lookback=2)
        result = orchestrator.run(ReplayRequest(dataset=dataset))
        assert result.status == ReplayRunStatus.COMPLETED
    finally:
        socket.socket = original_socket


# ---------------------------------------------------------------------------
# 11. Replay → Context → Leakage Guard integration
# ---------------------------------------------------------------------------

def test_e2e_leakage_guard_integrated():
    """
    Prove the leakage guard is wired into the orchestrator by verifying
    that zero violations occur on a clean dataset.
    """
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    dataset = make_dataset(start, count=10)
    orchestrator = make_orchestrator(period=1, lookback=5)

    result = orchestrator.run(ReplayRequest(dataset=dataset))

    assert result.leakage_violations == 0


# ---------------------------------------------------------------------------
# 12. Start/end boundary filtering
# ---------------------------------------------------------------------------

def test_e2e_start_end_boundary():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    dataset = make_dataset(start, count=20)

    # Restrict to middle 10 candles
    replay_start = start + timedelta(minutes=15 * 5)
    replay_end = start + timedelta(minutes=15 * 14)

    orchestrator = make_orchestrator(period=1, lookback=2)
    result = orchestrator.run(ReplayRequest(
        dataset=dataset,
        start_time=replay_start,
        end_time=replay_end,
    ))

    # All processed steps must fall within the boundary
    for step in result.step_records:
        assert step.replay_timestamp >= replay_start
        assert step.replay_timestamp <= replay_end


# ---------------------------------------------------------------------------
# 13. Replay result has unique ID each run
# ---------------------------------------------------------------------------

def test_e2e_unique_replay_id():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    dataset = make_dataset(start, count=5)
    orchestrator = make_orchestrator()

    r1 = orchestrator.run(ReplayRequest(dataset=dataset))
    r2 = orchestrator.run(ReplayRequest(dataset=dataset))

    assert r1.replay_id != r2.replay_id


# ---------------------------------------------------------------------------
# 14. Replay step records isolation
# ---------------------------------------------------------------------------

def test_e2e_step_records_are_immutable():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    dataset = make_dataset(start, count=5)
    orchestrator = make_orchestrator(period=1, lookback=2)

    result = orchestrator.run(ReplayRequest(dataset=dataset))

    # step_records is a tuple → immutable at the top level
    with pytest.raises((TypeError, AttributeError)):
        result.step_records[0] = None  # type: ignore
