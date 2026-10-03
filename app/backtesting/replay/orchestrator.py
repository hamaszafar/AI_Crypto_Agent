"""
Phase 6B.5 — Replay Orchestrator

Integrates the full replay pipeline:
  HistoricalDataset
    → ReplayRequest + HistoricalReplayEngine  (6B.2)
    → HistoricalContextProvider               (6B.3)
    → LeakageGuard                            (6B.4)
    → IndicatorEngine                         (existing)
    → SignalEngine                            (existing)
    → ReplayResult
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Sequence, Tuple

from app.backtesting.contracts.config import BacktestConfig
from app.backtesting.contracts.trade import SimulatedTrade
from app.backtesting.contracts.signal_observation import SignalObservation
from app.backtesting.contracts.signal_outcome import SignalOutcome
from app.backtesting.metrics.calculator import PerformanceMetrics, calculate_performance_metrics
from app.backtesting.trade.simulator import TradeSimulator
from app.backtesting.outcome.tracker import SignalOutcomeTracker

from app.backtesting.datasets.models import HistoricalDataset
from app.backtesting.replay.engine import HistoricalReplayEngine
from app.backtesting.replay.models import ReplayRequest, ReplayEvent, ReplayStatus
from app.backtesting.replay.exceptions import ReplayFinishedError, ReplayInitializationError
from app.backtesting.replay.context.provider import HistoricalContextProvider
from app.backtesting.replay.context.models import ContextWindow
from app.backtesting.replay.leakage.guard import LeakageGuard
from app.backtesting.replay.leakage.exceptions import FutureDataDetectedError, InvalidReplayTimestampError
from app.indicators.engine import IndicatorEngine
from app.indicators.input import IndicatorInput, IndicatorCandle
from app.indicators.models import IndicatorResult
from app.signals.engine import SignalEngine
from app.signals.models import Signal, SignalContext


class ReplayRunStatus(str, Enum):
    """Terminal status of a full replay run."""
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABORTED_LEAKAGE = "ABORTED_LEAKAGE"


@dataclass(frozen=True)
class ReplayStepRecord:
    """Immutable record of what happened at a single replay step."""
    replay_timestamp: datetime
    candle_index: int
    indicator_results: dict
    signal: Optional[Signal]
    was_warmed_up: bool
    skipped: bool = False


@dataclass(frozen=True)
class ReplayResult:
    """
    Complete, immutable result of a full historical replay run.

    Attributes:
        replay_id: Unique deterministic identifier for this run.
        exchange: Exchange the data belongs to.
        symbol: Trading pair symbol.
        timeframe: Candle timeframe.
        start_timestamp: First candle timestamp processed.
        end_timestamp: Last candle timestamp processed.
        candles_processed: Number of candles that went through the full pipeline.
        candles_skipped: Number of candles skipped due to insufficient warm-up.
        warmup_periods: Number of candles that did not have full lookback satisfied.
        signals_generated: Number of Signal objects produced.
        signals_resolved: Number of signals that reached a terminal outcome (WIN/LOSS/etc).
        trades_opened: Number of trades opened.
        trades_closed: Number of trades closed.
        leakage_violations: Number of leakage violations detected (should always be 0).
        status: Final run status.
        step_records: Tuple of per-step records.
        trades: Tuple of all SimulatedTrades generated.
        signal_outcomes: Tuple of all SignalOutcomes generated.
    """
    replay_id: str
    exchange: str
    symbol: str
    timeframe: str
    start_timestamp: Optional[datetime]
    end_timestamp: Optional[datetime]
    candles_processed: int
    candles_skipped: int
    warmup_periods: int
    signals_generated: int
    signals_resolved: int
    trades_opened: int
    trades_closed: int
    leakage_violations: int
    status: ReplayRunStatus
    step_records: tuple
    trades: tuple
    signal_outcomes: tuple
    metrics: Optional[PerformanceMetrics] = None


class ReplayOrchestrator:
    """
    Orchestrates the complete end-to-end historical replay pipeline.

    Pipeline:
        HistoricalDataset
          → HistoricalReplayEngine   [feeds candles one at a time]
          → HistoricalContextProvider [builds lookback window up to T]
          → LeakageGuard             [validates no future data]
          → context → IndicatorInput [converts window to indicator format]
          → IndicatorEngine          [calculates indicators]
          → SignalEngine             [generates signal]
          → ReplayResult             [accumulates all step records]

    The orchestrator holds no hidden global state. All dependencies are
    injected at construction time.
    """

    def __init__(
        self,
        indicator_engine: IndicatorEngine,
        signal_engine: SignalEngine,
        lookback: int,
        skip_unwarmed: bool = True,
        trade_simulator: Optional[TradeSimulator] = None,
        outcome_tracker: Optional[SignalOutcomeTracker] = None,
    ) -> None:
        """
        Args:
            indicator_engine: Fully configured IndicatorEngine.
            signal_engine: Fully configured SignalEngine.
            lookback: Number of historical candles to supply to indicators at each step.
            skip_unwarmed: If True, candles where context is not fully warmed up
                           are recorded as skipped and no signal is generated.
                           If False, attempts to run indicators on partial data
                           (IndicatorEngine itself will raise ValueError when
                           insufficient data is present for a given indicator).
        """
        self._indicator_engine = indicator_engine
        self._signal_engine = signal_engine
        self._lookback = lookback
        self._skip_unwarmed = skip_unwarmed
        self._trade_simulator = trade_simulator
        self._outcome_tracker = outcome_tracker

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, request: ReplayRequest) -> ReplayResult:
        """
        Execute the complete replay for the given request.

        Returns:
            A fully populated, immutable ReplayResult.

        Raises:
            ReplayInitializationError: If the dataset/request is invalid.
            FutureDataDetectedError: If a leakage violation is detected
                (never silently ignored; execution aborts immediately).
        """
        replay_id = str(uuid.uuid4())
        engine = HistoricalReplayEngine()
        engine.initialize(request)

        context_provider = HistoricalContextProvider(
            dataset=request.dataset,
            lookback=self._lookback,
        )

        steps: List[ReplayStepRecord] = []
        signal_outcomes_list: List[SignalOutcome] = []
        candles_processed = 0
        candles_skipped = 0
        warmup_periods = 0
        signals_generated = 0
        signals_resolved = 0
        leakage_violations = 0

        status = ReplayRunStatus.COMPLETED
        start_ts: Optional[datetime] = None
        end_ts: Optional[datetime] = None

        while True:
            try:
                event: ReplayEvent = engine.next_step()
            except ReplayFinishedError:
                break

            replay_ts = event.timestamp

            if start_ts is None:
                start_ts = replay_ts
            end_ts = replay_ts

            # --- 6B.3: Build context window ---
            context: ContextWindow = context_provider.get_context(replay_ts)

            # --- 6B.4: Leakage guard ---
            try:
                LeakageGuard.validate_context(context, replay_ts)
            except (FutureDataDetectedError, InvalidReplayTimestampError) as exc:
                leakage_violations += 1
                status = ReplayRunStatus.ABORTED_LEAKAGE
                raise  # Never silently ignore leakage

            # --- Warm-up check ---
            if not context.is_warmed_up:
                warmup_periods += 1
                if self._skip_unwarmed:
                    candles_skipped += 1
                    steps.append(ReplayStepRecord(
                        replay_timestamp=replay_ts,
                        candle_index=event.index,
                        indicator_results={},
                        signal=None,
                        was_warmed_up=False,
                        skipped=True,
                    ))
                    continue

            # --- Convert ContextWindow → IndicatorInput ---
            indicator_input = _context_to_indicator_input(context, request.dataset)

            # --- Indicator Engine ---
            try:
                indicator_results: dict[str, IndicatorResult] = self._indicator_engine.calculate_all(indicator_input)
            except ValueError:
                # Insufficient data for at least one indicator — treat as warm-up skip
                warmup_periods += 1
                candles_skipped += 1
                steps.append(ReplayStepRecord(
                    replay_timestamp=replay_ts,
                    candle_index=event.index,
                    indicator_results={},
                    signal=None,
                    was_warmed_up=False,
                    skipped=True,
                ))
                continue

            # --- Flatten indicator results to name → latest value map ---
            flat_indicators = _flatten_indicator_results(indicator_results)

            # --- Signal Engine ---
            signal_context = SignalContext(
                symbol=request.dataset.symbol,
                exchange=request.dataset.exchange,
                timeframe=request.dataset.timeframe,
                timestamp=replay_ts,
            )
            signal: Signal = self._signal_engine.generate(flat_indicators, signal_context)
            signals_generated += 1
            candles_processed += 1

            # Shared observation for trade sim and outcome tracker
            obs = SignalObservation.from_signal(
                signal=signal,
                entry_price=event.candle.close,
            )

            # --- Outcome Tracker ---
            if self._outcome_tracker:
                # 1. Process candle for active signals
                new_outcomes = self._outcome_tracker.process_candle(event.candle)
                signal_outcomes_list.extend(new_outcomes)
                signals_resolved += len(new_outcomes)

                # 2. Register new signal
                self._outcome_tracker.register(obs)

            # --- Trade Simulator ---
            if self._trade_simulator:
                # 1. Process candle for active trades
                self._trade_simulator.process_candle(event.candle)
                
                # 2. Feed new signal observation
                self._trade_simulator.on_signal(obs)

            steps.append(ReplayStepRecord(
                replay_timestamp=replay_ts,
                candle_index=event.index,
                indicator_results=indicator_results,
                signal=signal,
                was_warmed_up=True,
                skipped=False,
            ))

        # End of run: flush expired trades and signals
        trades: Tuple[SimulatedTrade, ...] = ()
        trades_opened = 0
        trades_closed = 0
        
        if self._trade_simulator:
            if end_ts and event.candle:
                self._trade_simulator.flush_expired(end_ts, event.candle.close)
            
            trades = tuple(self._trade_simulator.closed_trades)
            trades_opened = self._trade_simulator.trades_opened
            trades_closed = self._trade_simulator.trades_closed

        if self._outcome_tracker and end_ts:
            terminal_outcomes = self._outcome_tracker.flush_expired(end_ts)
            signal_outcomes_list.extend(terminal_outcomes)
            signals_resolved += len(terminal_outcomes)

        metrics: Optional[PerformanceMetrics] = None
        if self._trade_simulator:
            metrics = calculate_performance_metrics(trades)

        return ReplayResult(
            replay_id=replay_id,
            exchange=request.dataset.exchange,
            symbol=request.dataset.symbol,
            timeframe=request.dataset.timeframe,
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            candles_processed=candles_processed,
            candles_skipped=candles_skipped,
            warmup_periods=warmup_periods,
            signals_generated=signals_generated,
            signals_resolved=signals_resolved,
            trades_opened=trades_opened,
            trades_closed=trades_closed,
            leakage_violations=leakage_violations,
            status=status,
            step_records=tuple(steps),
            trades=trades,
            signal_outcomes=tuple(signal_outcomes_list),
            metrics=metrics,
        )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _context_to_indicator_input(context: ContextWindow, dataset: HistoricalDataset) -> IndicatorInput:
    """Convert a ContextWindow into an IndicatorInput without touching the dataset directly."""
    indicator_candles = tuple(
        IndicatorCandle(
            timestamp=c.timestamp,
            open=c.open,
            high=c.high,
            low=c.low,
            close=c.close,
            volume=c.volume,
        )
        for c in context.candles
    )
    return IndicatorInput(
        exchange=dataset.exchange,
        symbol=dataset.symbol,
        timeframe=dataset.timeframe,
        candles=indicator_candles,
    )


def _flatten_indicator_results(results: dict[str, IndicatorResult]) -> dict[str, object]:
    """
    Flatten IndicatorResult.values into a single mapping keyed by
    '{indicator_name}_{value_key}' for consumption by the SignalEngine.
    Also include the raw result objects under their indicator name.
    """
    flat: dict[str, object] = {}
    for name, result in results.items():
        for key, value in result.values.items():
            flat[f"{name}_{key}"] = value
    return flat
