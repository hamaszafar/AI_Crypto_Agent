"""
Phase 6C.2 — Signal Outcome Tracker.

Core component: SignalOutcomeTracker
=====================================

Tracks every generated signal independently and evaluates it against
subsequent replay candles, resolving each signal into a SignalOutcome
(the 6C.1 contract) when a termination condition is reached.

Design principles
-----------------
* **Deterministic** — identical inputs always produce identical outputs.
  No wall-clock time, randomness, or live-API calls anywhere.
* **No future data** — a candle whose timestamp is strictly earlier than
  a signal's registration timestamp is silently skipped *for that signal*.
  Chronological ordering is the caller's responsibility (the replay engine
  guarantees this); the tracker does not enforce it globally.
* **No cross-signal state mixing** — each signal_id is tracked in complete
  isolation; different symbols, timeframes, and IDs never share state.
* **6C.1 contracts only** — outputs are ``SignalOutcome`` instances; no new
  result models are introduced.

TP/SL Ambiguity Rule (documented)
-----------------------------------
When a single candle simultaneously satisfies both the TP and SL condition
(e.g. for a BUY: candle.high >= take_profit AND candle.low <= stop_loss),
the tracker applies the ``tp_sl_ambiguity_rule`` from ``OutcomeEvaluationConfig``:

  ``"sl_wins"`` (default)
      Resolve as LOSS. Conservative choice: in live markets a stop order is
      triggered the moment price crosses the SL level; the simultaneous TP
      touch cannot be guaranteed to have occurred first.

  ``"tp_wins"``
      Resolve as WIN. Use when a caller's execution model assumes TP fills
      have priority (e.g. limit orders matched before market orders).

HOLD-direction policy
-----------------------
A ``SignalDirection.HOLD`` signal carries no directional conviction and
cannot have a meaningful TP/SL outcome. Such a signal is immediately
resolved as ``INVALID`` at registration time and is never placed in the
active tracking table.

Breakeven detection
-------------------
When a signal resolves (WIN or LOSS), if the fractional distance between
the exit_price and entry_price is within ``breakeven_threshold``:

    abs(exit_price - entry_price) / entry_price <= breakeven_threshold

the outcome is promoted to ``BREAKEVEN`` rather than WIN or LOSS.
A ``breakeven_threshold`` of ``Decimal("0")`` (the default) disables
this classification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from app.backtesting.contracts.enums import SignalOutcomeStatus
from app.backtesting.contracts.signal_observation import SignalObservation
from app.backtesting.contracts.signal_outcome import SignalOutcome
from app.backtesting.outcome.config import (
    OutcomeEvaluationConfig,
    TP_SL_AMBIGUITY_SL_WINS,
    TP_SL_AMBIGUITY_TP_WINS,
)
from app.backtesting.outcome.exceptions import (
    SignalAlreadyRegisteredError,
    OutcomeTrackerStateError,
)
from app.market_data.models import MarketCandle
from app.signals.models import SignalDirection


# ---------------------------------------------------------------------------
# Internal state type
# ---------------------------------------------------------------------------


@dataclass
class _ActiveSignal:
    """
    Mutable bookkeeping record for one tracked signal.

    Not part of the public API.
    """

    observation: SignalObservation
    registered_at_ts: datetime  # == observation.timestamp
    candles_seen: int = 0       # incremented each time process_candle visits this signal


# ---------------------------------------------------------------------------
# Public tracker
# ---------------------------------------------------------------------------


class SignalOutcomeTracker:
    """
    Registers generated signals and evaluates them against subsequent candles.

    Usage (typical replay loop):
    ::

        config = OutcomeEvaluationConfig(max_candles=48)
        tracker = SignalOutcomeTracker(config)

        for event in replay_engine:
            candle = event.candle
            signal = signal_engine.generate(...)

            # Build a SignalObservation from the signal (6C.1 contract)
            obs = SignalObservation.from_signal(signal, entry_price=candle.close,
                                                take_profit=..., stop_loss=...)
            tracker.register(obs)

            # Evaluate all active signals against the current candle
            new_outcomes = tracker.process_candle(candle)
            # new_outcomes is a list[SignalOutcome]

        # At end-of-replay, expire any still-pending signals
        terminal_outcomes = tracker.flush_expired(current_ts=last_candle_ts)

    """

    def __init__(self, config: Optional[OutcomeEvaluationConfig] = None) -> None:
        """
        Args:
            config: Evaluation parameters.  Defaults to ``OutcomeEvaluationConfig()``
                    (no breakeven, no expiry, sl_wins ambiguity rule).
        """
        self._config: OutcomeEvaluationConfig = config or OutcomeEvaluationConfig()
        # Keyed by signal_id; preserves insertion order (Python 3.7+)
        self._active: Dict[str, _ActiveSignal] = {}
        self._resolved: List[SignalOutcome] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, observation: SignalObservation) -> Optional[SignalOutcome]:
        """
        Register a new signal for outcome tracking.

        HOLD-direction signals are immediately resolved as INVALID and returned
        directly (they are never placed in the active table).

        Args:
            observation: A fully validated ``SignalObservation`` produced during replay.

        Returns:
            A ``SignalOutcome`` with status ``INVALID`` if the signal direction is
            HOLD (immediately resolved); ``None`` otherwise.

        Raises:
            SignalAlreadyRegisteredError: If the ``signal_id`` is already being tracked.
        """
        if observation.signal_id in self._active:
            raise SignalAlreadyRegisteredError(
                f"signal_id {observation.signal_id!r} is already registered and active."
            )

        # HOLD signals cannot produce a directional outcome → INVALID immediately
        if observation.direction == SignalDirection.HOLD:
            outcome = _build_outcome(
                observation=observation,
                status=SignalOutcomeStatus.INVALID,
                resolution_timestamp=observation.timestamp,
                exit_price=None,
                reason="HOLD direction has no directional TP/SL outcome; resolved INVALID at registration.",
            )
            self._resolved.append(outcome)
            return outcome

        # Normal directional signal → place in active table
        self._active[observation.signal_id] = _ActiveSignal(
            observation=observation,
            registered_at_ts=observation.timestamp,
        )
        return None

    def process_candle(self, candle: MarketCandle) -> List[SignalOutcome]:
        """
        Evaluate all active signals against *candle* and resolve any that meet a
        termination condition.

        Candles whose timestamp is **strictly before** a signal's registration
        timestamp are silently skipped for that signal (future-candle guard in
        reverse: we never let a signal be evaluated against data it "predates").

        Args:
            candle: The next candle in strict chronological replay order.

        Returns:
            A list of ``SignalOutcome`` objects resolved on this candle step
            (may be empty).  The resolved outcomes are also appended to
            ``self.resolved_outcomes``.
        """
        newly_resolved: List[SignalOutcome] = []
        to_remove: List[str] = []

        for signal_id, active in self._active.items():
            obs = active.observation

            # --- Future-candle guard ---
            # A candle older than the signal cannot inform its outcome.
            if candle.timestamp < obs.timestamp:
                continue  # skip this candle for this signal; do not increment candles_seen

            active.candles_seen += 1

            outcome = _evaluate(candle, active, self._config)

            if outcome is not None:
                newly_resolved.append(outcome)
                self._resolved.append(outcome)
                to_remove.append(signal_id)

        for sid in to_remove:
            del self._active[sid]

        return newly_resolved

    def flush_expired(self, current_ts: datetime) -> List[SignalOutcome]:
        """
        Resolve all remaining active signals as ``EXPIRED``.

        Call this at the end of a replay run to ensure no signals are left pending.

        Args:
            current_ts: The timestamp to use as the resolution timestamp for expired
                        signals (typically the last processed candle's timestamp).

        Returns:
            A list of newly resolved ``SignalOutcome`` objects (status ``EXPIRED``).
        """
        if current_ts.tzinfo is None or current_ts.tzinfo.utcoffset(current_ts) is None:
            raise OutcomeTrackerStateError(
                "current_ts passed to flush_expired must be timezone-aware."
            )

        expired: List[SignalOutcome] = []
        for signal_id, active in list(self._active.items()):
            obs = active.observation
            outcome = _build_outcome(
                observation=obs,
                status=SignalOutcomeStatus.EXPIRED,
                resolution_timestamp=current_ts,
                exit_price=None,
                reason=f"Signal expired: flush_expired called after {active.candles_seen} candle(s).",
            )
            expired.append(outcome)
            self._resolved.append(outcome)

        self._active.clear()
        return expired

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def pending_signals(self) -> List[str]:
        """Return a list of signal_ids that are still active (not yet resolved)."""
        return list(self._active.keys())

    @property
    def resolved_outcomes(self) -> List[SignalOutcome]:
        """Return a copy of all resolved outcomes accumulated so far."""
        return list(self._resolved)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """
        Clear all tracker state.

        After a reset the tracker is equivalent to a freshly constructed instance
        with the same config.  Use this between replay runs to avoid state leaking.
        """
        self._active.clear()
        self._resolved.clear()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _evaluate(
    candle: MarketCandle,
    active: _ActiveSignal,
    config: OutcomeEvaluationConfig,
) -> Optional[SignalOutcome]:
    """
    Determine whether *active* resolves on *candle*.

    Returns a ``SignalOutcome`` if resolution occurs, ``None`` to keep the
    signal pending.
    """
    obs = active.observation
    direction = obs.direction
    take_profit = obs.take_profit
    stop_loss = obs.stop_loss

    # --- Directional hit detection ---
    if direction == SignalDirection.BUY:
        tp_hit = take_profit is not None and candle.high >= take_profit
        sl_hit = stop_loss is not None and candle.low <= stop_loss
    elif direction == SignalDirection.SELL:
        tp_hit = take_profit is not None and candle.low <= take_profit
        sl_hit = stop_loss is not None and candle.high >= stop_loss
    else:
        # HOLD should never reach here (resolved at registration), but guard anyway
        tp_hit = False
        sl_hit = False

    # --- Ambiguity resolution ---
    if tp_hit and sl_hit:
        if config.tp_sl_ambiguity_rule == TP_SL_AMBIGUITY_SL_WINS:
            tp_hit = False  # SL takes precedence → LOSS
        else:  # TP_SL_AMBIGUITY_TP_WINS
            sl_hit = False  # TP takes precedence → WIN

    # --- Resolve WIN ---
    if tp_hit:
        exit_price = take_profit  # type: ignore[assignment]  # guaranteed non-None by tp_hit
        status = _apply_breakeven(
            status=SignalOutcomeStatus.WIN,
            exit_price=exit_price,
            entry_price=obs.entry_price,
            threshold=config.breakeven_threshold,
        )
        return _build_outcome(
            observation=obs,
            status=status,
            resolution_timestamp=candle.timestamp,
            exit_price=exit_price,
            reason=_reason_for(status, "take_profit"),
        )

    # --- Resolve LOSS ---
    if sl_hit:
        exit_price = stop_loss  # type: ignore[assignment]  # guaranteed non-None by sl_hit
        status = _apply_breakeven(
            status=SignalOutcomeStatus.LOSS,
            exit_price=exit_price,
            entry_price=obs.entry_price,
            threshold=config.breakeven_threshold,
        )
        return _build_outcome(
            observation=obs,
            status=status,
            resolution_timestamp=candle.timestamp,
            exit_price=exit_price,
            reason=_reason_for(status, "stop_loss"),
        )

    # --- Resolve EXPIRED (max_candles reached) ---
    if config.max_candles is not None and active.candles_seen >= config.max_candles:
        return _build_outcome(
            observation=obs,
            status=SignalOutcomeStatus.EXPIRED,
            resolution_timestamp=candle.timestamp,
            exit_price=candle.close,
            reason=f"Signal expired after {active.candles_seen} candle(s) (max_candles={config.max_candles}).",
        )

    # --- Still pending ---
    return None


def _apply_breakeven(
    status: SignalOutcomeStatus,
    exit_price: Decimal,
    entry_price: Decimal,
    threshold: Decimal,
) -> SignalOutcomeStatus:
    """
    Promote a WIN or LOSS to BREAKEVEN if the exit is within *threshold* of entry.

    A threshold of Decimal("0") disables this check (distance is always > 0 for
    non-identical prices; identical exit == entry also satisfies the check when
    threshold == 0 because 0 <= 0).
    """
    if threshold == Decimal("0"):
        return status
    fractional_distance = abs(exit_price - entry_price) / entry_price
    if fractional_distance <= threshold:
        return SignalOutcomeStatus.BREAKEVEN
    return status


def _reason_for(status: SignalOutcomeStatus, trigger: str) -> str:
    """Human-readable resolution reason string."""
    if status == SignalOutcomeStatus.BREAKEVEN:
        return f"Resolved BREAKEVEN: {trigger} triggered but exit within breakeven threshold of entry."
    if status == SignalOutcomeStatus.WIN:
        return f"Resolved WIN: {trigger} reached."
    if status == SignalOutcomeStatus.LOSS:
        return f"Resolved LOSS: {trigger} reached."
    return f"Resolved {status.value}: {trigger}."


def _build_outcome(
    observation: SignalObservation,
    status: SignalOutcomeStatus,
    resolution_timestamp: datetime,
    exit_price: Optional[Decimal],
    reason: str,
) -> SignalOutcome:
    """
    Construct a ``SignalOutcome`` (6C.1 contract) from an observation and resolution data.

    PnL is computed only for WIN / LOSS / BREAKEVEN where an exit_price is available:
        realized_pnl    = (exit_price - entry_price) * direction_sign
        realized_return = realized_pnl / entry_price
    where direction_sign = +1 for BUY, -1 for SELL.
    """
    realized_pnl: Optional[Decimal] = None
    realized_return: Optional[Decimal] = None

    if exit_price is not None and status in (
        SignalOutcomeStatus.WIN,
        SignalOutcomeStatus.LOSS,
        SignalOutcomeStatus.BREAKEVEN,
        SignalOutcomeStatus.EXPIRED,
    ):
        direction_sign = (
            Decimal("1") if observation.direction == SignalDirection.BUY else Decimal("-1")
        )
        realized_pnl = (exit_price - observation.entry_price) * direction_sign
        if observation.entry_price != Decimal("0"):
            realized_return = realized_pnl / observation.entry_price

    return SignalOutcome(
        signal_id=observation.signal_id,
        signal_timestamp=observation.timestamp,
        status=status,
        entry_price=observation.entry_price,
        direction=observation.direction,
        resolution_timestamp=resolution_timestamp,
        exit_price=exit_price,
        realized_pnl=realized_pnl,
        realized_return=realized_return,
        reason=reason,
    )
