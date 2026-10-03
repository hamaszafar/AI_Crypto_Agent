"""
Phase 6C.2 — Signal Outcome Tracker Tests
==========================================

Covers:
  1.  signal registration
  2.  pending signal (no candles)
  3.  TP → WIN (BUY)
  4.  SL → LOSS (BUY)
  5.  TP → WIN (SELL)
  6.  SL → LOSS (SELL)
  7.  breakeven detection
  8.  expiration by max_candles
  9.  flush_expired remaining signals
  10. INVALID — HOLD direction
  11. INVALID — no TP, no SL, no max_candles (only via flush)
  12. multiple active signals, independent resolution
  13. duplicate signal_id raises SignalAlreadyRegisteredError
  14. chronological processing order
  15. candle exactly at signal timestamp (inclusive boundary)
  16. candle before signal timestamp is skipped for that signal
  17. TP/SL ambiguity — sl_wins (default)
  18. TP/SL ambiguity — tp_wins (config override)
  19. deterministic repeated evaluation
  20. PnL calculation — BUY WIN
  21. PnL calculation — SELL WIN
  22. resolved outcome is a SignalOutcome (6C.1 contract)
  23. reset() clears all state
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

from app.market_data.models import MarketCandle
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
from app.backtesting.outcome.tracker import SignalOutcomeTracker
from app.signals.models import (
    SignalConfidence,
    SignalDirection,
    SignalStrength,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

BASE_TS = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def ts(offset_minutes: int = 0) -> datetime:
    """Return BASE_TS + offset_minutes."""
    return BASE_TS + timedelta(minutes=offset_minutes)


def make_observation(
    signal_id: str = "sig_001",
    direction: SignalDirection = SignalDirection.BUY,
    entry_price: Decimal = Decimal("100"),
    take_profit: Optional[Decimal] = Decimal("110"),
    stop_loss: Optional[Decimal] = Decimal("90"),
    timestamp: Optional[datetime] = None,
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
) -> SignalObservation:
    """Build a minimal, valid SignalObservation for testing."""
    return SignalObservation(
        signal_id=signal_id,
        timestamp=timestamp or BASE_TS,
        exchange="binance",
        symbol=symbol,
        timeframe=timeframe,
        direction=direction,
        strength=SignalStrength.MODERATE,
        confidence=SignalConfidence.MEDIUM,
        score=Decimal("0.6"),
        entry_price=entry_price,
        take_profit=take_profit,
        stop_loss=stop_loss,
    )


def make_candle(
    open_: Decimal,
    high: Decimal,
    low: Decimal,
    close: Decimal,
    timestamp: Optional[datetime] = None,
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
) -> MarketCandle:
    """Build a minimal, valid MarketCandle."""
    return MarketCandle(
        exchange="binance",
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp or BASE_TS,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=Decimal("1000"),
    )


def neutral_candle(timestamp: Optional[datetime] = None) -> MarketCandle:
    """A candle that does NOT touch TP (110) or SL (90) for default BUY obs."""
    return make_candle(
        open_=Decimal("100"),
        high=Decimal("105"),
        low=Decimal("95"),
        close=Decimal("100"),
        timestamp=timestamp or BASE_TS,
    )


# ---------------------------------------------------------------------------
# 1. Signal registration
# ---------------------------------------------------------------------------

def test_register_signal():
    """Registered signal appears in pending_signals and not in resolved_outcomes."""
    tracker = SignalOutcomeTracker()
    obs = make_observation()
    result = tracker.register(obs)

    assert result is None  # BUY signal → not immediately resolved
    assert "sig_001" in tracker.pending_signals
    assert len(tracker.resolved_outcomes) == 0


# ---------------------------------------------------------------------------
# 2. Pending signal — no candles processed
# ---------------------------------------------------------------------------

def test_pending_signal_no_candles():
    """Without processing any candles the signal remains PENDING (in active table)."""
    tracker = SignalOutcomeTracker()
    tracker.register(make_observation())

    assert len(tracker.pending_signals) == 1
    assert len(tracker.resolved_outcomes) == 0


# ---------------------------------------------------------------------------
# 3. TP → WIN (BUY)
# ---------------------------------------------------------------------------

def test_tp_win_buy():
    """BUY signal: candle.high >= take_profit → WIN."""
    tracker = SignalOutcomeTracker()
    obs = make_observation(
        entry_price=Decimal("100"),
        take_profit=Decimal("110"),
        stop_loss=Decimal("90"),
    )
    tracker.register(obs)

    # Candle whose high exactly touches TP
    candle = make_candle(
        open_=Decimal("100"),
        high=Decimal("110"),   # exactly TP
        low=Decimal("95"),
        close=Decimal("108"),
        timestamp=ts(1),
    )
    outcomes = tracker.process_candle(candle)

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status == SignalOutcomeStatus.WIN
    assert outcome.exit_price == Decimal("110")
    assert outcome.signal_id == "sig_001"
    assert "sig_001" not in tracker.pending_signals


# ---------------------------------------------------------------------------
# 4. SL → LOSS (BUY)
# ---------------------------------------------------------------------------

def test_sl_loss_buy():
    """BUY signal: candle.low <= stop_loss → LOSS."""
    tracker = SignalOutcomeTracker()
    obs = make_observation(
        entry_price=Decimal("100"),
        take_profit=Decimal("110"),
        stop_loss=Decimal("90"),
    )
    tracker.register(obs)

    candle = make_candle(
        open_=Decimal("100"),
        high=Decimal("105"),
        low=Decimal("90"),   # exactly SL
        close=Decimal("92"),
        timestamp=ts(1),
    )
    outcomes = tracker.process_candle(candle)

    assert len(outcomes) == 1
    outcome = outcomes[0]
    assert outcome.status == SignalOutcomeStatus.LOSS
    assert outcome.exit_price == Decimal("90")
    assert "sig_001" not in tracker.pending_signals


# ---------------------------------------------------------------------------
# 5. TP → WIN (SELL)
# ---------------------------------------------------------------------------

def test_tp_win_sell():
    """SELL signal: candle.low <= take_profit → WIN."""
    tracker = SignalOutcomeTracker()
    obs = make_observation(
        direction=SignalDirection.SELL,
        entry_price=Decimal("100"),
        take_profit=Decimal("90"),   # price must drop to TP
        stop_loss=Decimal("110"),    # price must rise to SL
    )
    tracker.register(obs)

    candle = make_candle(
        open_=Decimal("100"),
        high=Decimal("105"),
        low=Decimal("90"),   # exactly TP for SELL
        close=Decimal("92"),
        timestamp=ts(1),
    )
    outcomes = tracker.process_candle(candle)

    assert len(outcomes) == 1
    assert outcomes[0].status == SignalOutcomeStatus.WIN
    assert outcomes[0].exit_price == Decimal("90")


# ---------------------------------------------------------------------------
# 6. SL → LOSS (SELL)
# ---------------------------------------------------------------------------

def test_sl_loss_sell():
    """SELL signal: candle.high >= stop_loss → LOSS."""
    tracker = SignalOutcomeTracker()
    obs = make_observation(
        direction=SignalDirection.SELL,
        entry_price=Decimal("100"),
        take_profit=Decimal("90"),
        stop_loss=Decimal("110"),
    )
    tracker.register(obs)

    candle = make_candle(
        open_=Decimal("100"),
        high=Decimal("110"),   # exactly SL for SELL
        low=Decimal("95"),
        close=Decimal("108"),
        timestamp=ts(1),
    )
    outcomes = tracker.process_candle(candle)

    assert len(outcomes) == 1
    assert outcomes[0].status == SignalOutcomeStatus.LOSS
    assert outcomes[0].exit_price == Decimal("110")


# ---------------------------------------------------------------------------
# 7. Breakeven detection
# ---------------------------------------------------------------------------

def test_breakeven_buy():
    """
    BUY signal hits TP but exit is within the breakeven_threshold of entry
    → outcome should be BREAKEVEN, not WIN.
    """
    # entry=100, TP=100.05 → 0.05% above entry
    # breakeven_threshold=0.001 (0.1%)  → 0.05% <= 0.1% → BREAKEVEN
    config = OutcomeEvaluationConfig(breakeven_threshold=Decimal("0.001"))
    tracker = SignalOutcomeTracker(config)
    obs = make_observation(
        entry_price=Decimal("100"),
        take_profit=Decimal("100.05"),
        stop_loss=Decimal("99"),
    )
    tracker.register(obs)

    candle = make_candle(
        open_=Decimal("100"),
        high=Decimal("100.05"),  # hits TP exactly
        low=Decimal("99.5"),
        close=Decimal("100.02"),
        timestamp=ts(1),
    )
    outcomes = tracker.process_candle(candle)

    assert len(outcomes) == 1
    assert outcomes[0].status == SignalOutcomeStatus.BREAKEVEN


def test_breakeven_disabled_when_threshold_zero():
    """With threshold=0 (default), a close TP hit is still WIN."""
    tracker = SignalOutcomeTracker(OutcomeEvaluationConfig(breakeven_threshold=Decimal("0")))
    obs = make_observation(
        entry_price=Decimal("100"),
        take_profit=Decimal("100.01"),
        stop_loss=Decimal("99"),
    )
    tracker.register(obs)

    candle = make_candle(
        open_=Decimal("100"),
        high=Decimal("100.01"),
        low=Decimal("99.5"),
        close=Decimal("100.01"),
        timestamp=ts(1),
    )
    outcomes = tracker.process_candle(candle)

    assert outcomes[0].status == SignalOutcomeStatus.WIN


# ---------------------------------------------------------------------------
# 8. Expiration by max_candles
# ---------------------------------------------------------------------------

def test_expiration_by_max_candles():
    """Signal expires after max_candles candles without hitting TP or SL."""
    config = OutcomeEvaluationConfig(max_candles=3)
    tracker = SignalOutcomeTracker(config)
    obs = make_observation(
        entry_price=Decimal("100"),
        take_profit=Decimal("110"),
        stop_loss=Decimal("90"),
    )
    tracker.register(obs)

    # 2 neutral candles → not yet expired
    outcomes_1 = tracker.process_candle(neutral_candle(ts(1)))
    outcomes_2 = tracker.process_candle(neutral_candle(ts(2)))
    assert outcomes_1 == []
    assert outcomes_2 == []
    assert "sig_001" in tracker.pending_signals

    # 3rd candle → max_candles reached → EXPIRED
    outcomes_3 = tracker.process_candle(neutral_candle(ts(3)))
    assert len(outcomes_3) == 1
    assert outcomes_3[0].status == SignalOutcomeStatus.EXPIRED
    assert "sig_001" not in tracker.pending_signals


def test_expiry_candle_count_is_exact():
    """
    With max_candles=1, the very first candle (at or after signal ts) expires the signal.
    """
    config = OutcomeEvaluationConfig(max_candles=1)
    tracker = SignalOutcomeTracker(config)
    tracker.register(make_observation(
        take_profit=Decimal("110"), stop_loss=Decimal("90")
    ))
    outcomes = tracker.process_candle(neutral_candle(ts(1)))
    assert len(outcomes) == 1
    assert outcomes[0].status == SignalOutcomeStatus.EXPIRED


# ---------------------------------------------------------------------------
# 9. flush_expired remaining signals
# ---------------------------------------------------------------------------

def test_flush_expired_remaining():
    """flush_expired() resolves all still-pending signals as EXPIRED."""
    tracker = SignalOutcomeTracker()
    tracker.register(make_observation("sig_A"))
    tracker.register(make_observation("sig_B"))

    assert len(tracker.pending_signals) == 2

    flush_ts = ts(100)
    expired = tracker.flush_expired(flush_ts)

    assert len(expired) == 2
    assert all(o.status == SignalOutcomeStatus.EXPIRED for o in expired)
    assert len(tracker.pending_signals) == 0
    assert len(tracker.resolved_outcomes) == 2


def test_flush_expired_empty_when_no_pending():
    """flush_expired with no active signals returns empty list."""
    tracker = SignalOutcomeTracker()
    result = tracker.flush_expired(ts(10))
    assert result == []


# ---------------------------------------------------------------------------
# 10. INVALID — HOLD direction
# ---------------------------------------------------------------------------

def test_invalid_hold_signal():
    """
    A HOLD-direction signal is immediately resolved as INVALID at registration;
    it must never enter the active table.
    """
    tracker = SignalOutcomeTracker()
    obs = make_observation(
        direction=SignalDirection.HOLD,
        take_profit=None,
        stop_loss=None,
    )
    outcome = tracker.register(obs)

    assert outcome is not None
    assert outcome.status == SignalOutcomeStatus.INVALID
    assert "sig_001" not in tracker.pending_signals
    # Should appear in resolved outcomes
    assert len(tracker.resolved_outcomes) == 1
    assert tracker.resolved_outcomes[0].status == SignalOutcomeStatus.INVALID


# ---------------------------------------------------------------------------
# 11. INVALID — no TP, no SL, no max_candles (only via flush)
# ---------------------------------------------------------------------------

def test_no_tp_no_sl_no_expiry_stays_pending_until_flush():
    """
    A BUY signal with no TP, no SL, and no max_candles cannot resolve via
    candle evaluation.  It stays pending until flush_expired is called.
    """
    tracker = SignalOutcomeTracker()  # default config: no max_candles
    obs = make_observation(
        direction=SignalDirection.BUY,
        take_profit=None,
        stop_loss=None,
    )
    tracker.register(obs)

    # Many neutral candles → signal stays pending
    for i in range(10):
        outcomes = tracker.process_candle(neutral_candle(ts(i + 1)))
        assert outcomes == []

    assert "sig_001" in tracker.pending_signals

    # flush_expired resolves it
    expired = tracker.flush_expired(ts(100))
    assert len(expired) == 1
    assert expired[0].status == SignalOutcomeStatus.EXPIRED


# ---------------------------------------------------------------------------
# 12. Multiple active signals, independent resolution
# ---------------------------------------------------------------------------

def test_multiple_active_signals_independent():
    """
    Two signals with different IDs and different TP/SL levels resolve
    independently without polluting each other's state.
    """
    tracker = SignalOutcomeTracker()

    obs_a = make_observation(
        signal_id="sig_A",
        direction=SignalDirection.BUY,
        entry_price=Decimal("100"),
        take_profit=Decimal("110"),
        stop_loss=Decimal("90"),
    )
    obs_b = make_observation(
        signal_id="sig_B",
        direction=SignalDirection.SELL,
        entry_price=Decimal("200"),
        take_profit=Decimal("180"),
        stop_loss=Decimal("220"),
        symbol="ETH/USDT",
    )
    tracker.register(obs_a)
    tracker.register(obs_b)

    assert len(tracker.pending_signals) == 2

    # Candle that hits TP for sig_A (BUY, high=110).
    # sig_B is SELL with entry=200, TP=180, SL=220.
    # To avoid accidentally triggering sig_B's TP (SELL TP: low <= 180),
    # the candle's low must be > 180.  Use low=195.
    candle_a_resolves = make_candle(
        open_=Decimal("200"), high=Decimal("210"), low=Decimal("195"), close=Decimal("208"),
        timestamp=ts(1),
    )
    # sig_A: BUY TP=110 — candle high=210 >= 110 → WIN
    # sig_B: SELL TP=180 — candle low=195 > 180 → no; SELL SL=220 — candle high=210 < 220 → no
    outcomes = tracker.process_candle(candle_a_resolves)

    # sig_A resolved; sig_B still pending
    assert len(outcomes) == 1
    assert outcomes[0].signal_id == "sig_A"
    assert outcomes[0].status == SignalOutcomeStatus.WIN
    assert "sig_A" not in tracker.pending_signals
    assert "sig_B" in tracker.pending_signals

    # Now resolve sig_B with its TP (SELL: low <= 180)
    candle_b_resolves = make_candle(
        open_=Decimal("190"), high=Decimal("195"), low=Decimal("180"), close=Decimal("182"),
        timestamp=ts(2),
        symbol="ETH/USDT",
        timeframe="1h",
    )
    outcomes_b = tracker.process_candle(candle_b_resolves)
    assert len(outcomes_b) == 1
    assert outcomes_b[0].signal_id == "sig_B"
    assert outcomes_b[0].status == SignalOutcomeStatus.WIN
    assert len(tracker.pending_signals) == 0


# ---------------------------------------------------------------------------
# 13. Duplicate signal_id raises
# ---------------------------------------------------------------------------

def test_duplicate_signal_id_raises():
    """Re-registering the same signal_id raises SignalAlreadyRegisteredError."""
    tracker = SignalOutcomeTracker()
    obs = make_observation(signal_id="dup_id")
    tracker.register(obs)

    with pytest.raises(SignalAlreadyRegisteredError):
        tracker.register(obs)


# ---------------------------------------------------------------------------
# 14. Chronological processing
# ---------------------------------------------------------------------------

def test_chronological_processing():
    """
    Process 5 neutral candles then one TP-hit candle.
    Verify the resolution_timestamp matches the TP-hit candle's timestamp.
    """
    tracker = SignalOutcomeTracker()
    obs = make_observation(take_profit=Decimal("110"), stop_loss=Decimal("90"))
    tracker.register(obs)

    for i in range(1, 6):
        outcomes = tracker.process_candle(neutral_candle(ts(i)))
        assert outcomes == [], f"Unexpected resolution at candle {i}"

    tp_ts = ts(6)
    tp_candle = make_candle(
        open_=Decimal("100"), high=Decimal("112"), low=Decimal("98"), close=Decimal("111"),
        timestamp=tp_ts,
    )
    outcomes = tracker.process_candle(tp_candle)
    assert len(outcomes) == 1
    assert outcomes[0].resolution_timestamp == tp_ts


# ---------------------------------------------------------------------------
# 15. Candle exactly at signal timestamp (inclusive boundary)
# ---------------------------------------------------------------------------

def test_candle_exactly_at_signal_timestamp():
    """
    A candle whose timestamp equals the signal's timestamp is valid and
    must be evaluated (inclusive boundary).
    """
    tracker = SignalOutcomeTracker()
    signal_ts = BASE_TS
    obs = make_observation(
        timestamp=signal_ts,
        take_profit=Decimal("110"),
        stop_loss=Decimal("90"),
    )
    tracker.register(obs)

    # TP-hitting candle at exactly signal_ts
    candle = make_candle(
        open_=Decimal("100"), high=Decimal("115"), low=Decimal("98"), close=Decimal("112"),
        timestamp=signal_ts,
    )
    outcomes = tracker.process_candle(candle)

    assert len(outcomes) == 1
    assert outcomes[0].status == SignalOutcomeStatus.WIN


# ---------------------------------------------------------------------------
# 16. Candle before signal timestamp is skipped for that signal
# ---------------------------------------------------------------------------

def test_candle_before_signal_timestamp_skipped():
    """
    A candle with timestamp strictly before a signal's timestamp must NOT
    trigger resolution for that signal (future-candle guard).
    """
    tracker = SignalOutcomeTracker()
    signal_ts = ts(5)
    obs = make_observation(
        timestamp=signal_ts,
        take_profit=Decimal("110"),
        stop_loss=Decimal("90"),
    )
    tracker.register(obs)

    # Candle before the signal's timestamp — even a TP hit must be ignored
    early_candle = make_candle(
        open_=Decimal("100"), high=Decimal("120"), low=Decimal("80"), close=Decimal("115"),
        timestamp=ts(3),  # before signal_ts=ts(5)
    )
    outcomes = tracker.process_candle(early_candle)

    assert outcomes == []
    assert "sig_001" in tracker.pending_signals  # still active


# ---------------------------------------------------------------------------
# 17. TP/SL ambiguity — sl_wins (default)
# ---------------------------------------------------------------------------

def test_tp_sl_ambiguity_sl_wins_default():
    """
    BUY signal: same candle touches both TP (high >= 110) and SL (low <= 90).
    Default rule "sl_wins" → LOSS.
    """
    tracker = SignalOutcomeTracker()  # default: sl_wins
    obs = make_observation(
        entry_price=Decimal("100"),
        take_profit=Decimal("110"),
        stop_loss=Decimal("90"),
    )
    tracker.register(obs)

    ambiguous_candle = make_candle(
        open_=Decimal("100"),
        high=Decimal("115"),   # >= TP=110 ✓
        low=Decimal("85"),     # <= SL=90  ✓
        close=Decimal("100"),
        timestamp=ts(1),
    )
    outcomes = tracker.process_candle(ambiguous_candle)

    assert len(outcomes) == 1
    assert outcomes[0].status == SignalOutcomeStatus.LOSS
    assert outcomes[0].exit_price == Decimal("90")  # SL price


# ---------------------------------------------------------------------------
# 18. TP/SL ambiguity — tp_wins (config override)
# ---------------------------------------------------------------------------

def test_tp_sl_ambiguity_tp_wins():
    """Same ambiguous candle with tp_sl_ambiguity_rule="tp_wins" → WIN."""
    config = OutcomeEvaluationConfig(tp_sl_ambiguity_rule=TP_SL_AMBIGUITY_TP_WINS)
    tracker = SignalOutcomeTracker(config)
    obs = make_observation(
        entry_price=Decimal("100"),
        take_profit=Decimal("110"),
        stop_loss=Decimal("90"),
    )
    tracker.register(obs)

    ambiguous_candle = make_candle(
        open_=Decimal("100"),
        high=Decimal("115"),
        low=Decimal("85"),
        close=Decimal("100"),
        timestamp=ts(1),
    )
    outcomes = tracker.process_candle(ambiguous_candle)

    assert len(outcomes) == 1
    assert outcomes[0].status == SignalOutcomeStatus.WIN
    assert outcomes[0].exit_price == Decimal("110")  # TP price


# ---------------------------------------------------------------------------
# 19. Deterministic repeated evaluation
# ---------------------------------------------------------------------------

def test_deterministic_repeated_evaluation():
    """
    Running the same signal through the same sequence of candles twice must
    produce identical SignalOutcome fields (excluding auto-generated outcome_id).
    """
    def run_once() -> SignalOutcome:
        tracker = SignalOutcomeTracker()
        tracker.register(make_observation(take_profit=Decimal("110"), stop_loss=Decimal("90")))
        for i in range(1, 4):
            tracker.process_candle(neutral_candle(ts(i)))
        tp_candle = make_candle(
            open_=Decimal("100"), high=Decimal("112"), low=Decimal("98"), close=Decimal("111"),
            timestamp=ts(4),
        )
        outcomes = tracker.process_candle(tp_candle)
        return outcomes[0]

    r1 = run_once()
    r2 = run_once()

    assert r1.signal_id == r2.signal_id
    assert r1.status == r2.status
    assert r1.entry_price == r2.entry_price
    assert r1.exit_price == r2.exit_price
    assert r1.realized_pnl == r2.realized_pnl
    assert r1.realized_return == r2.realized_return
    assert r1.resolution_timestamp == r2.resolution_timestamp
    assert r1.signal_timestamp == r2.signal_timestamp


# ---------------------------------------------------------------------------
# 20. PnL calculation — BUY WIN
# ---------------------------------------------------------------------------

def test_pnl_calculation_buy_win():
    """
    BUY: entry=100, TP=110 → WIN.
    realized_pnl   = (110 - 100) * 1 = 10
    realized_return = 10 / 100 = 0.1
    """
    tracker = SignalOutcomeTracker()
    obs = make_observation(
        entry_price=Decimal("100"),
        take_profit=Decimal("110"),
        stop_loss=Decimal("90"),
    )
    tracker.register(obs)

    candle = make_candle(
        open_=Decimal("100"), high=Decimal("110"), low=Decimal("95"), close=Decimal("108"),
        timestamp=ts(1),
    )
    outcomes = tracker.process_candle(candle)

    o = outcomes[0]
    assert o.realized_pnl == Decimal("10")
    assert o.realized_return == Decimal("0.1")


# ---------------------------------------------------------------------------
# 21. PnL calculation — SELL WIN
# ---------------------------------------------------------------------------

def test_pnl_calculation_sell_win():
    """
    SELL: entry=100, TP=80 → WIN.
    realized_pnl   = (80 - 100) * -1 = 20
    realized_return = 20 / 100 = 0.2
    """
    tracker = SignalOutcomeTracker()
    obs = make_observation(
        direction=SignalDirection.SELL,
        entry_price=Decimal("100"),
        take_profit=Decimal("80"),
        stop_loss=Decimal("120"),
    )
    tracker.register(obs)

    # SELL TP hit: low <= 80
    candle = make_candle(
        open_=Decimal("95"), high=Decimal("98"), low=Decimal("80"), close=Decimal("82"),
        timestamp=ts(1),
    )
    outcomes = tracker.process_candle(candle)

    o = outcomes[0]
    assert o.status == SignalOutcomeStatus.WIN
    assert o.realized_pnl == Decimal("20")
    assert o.realized_return == Decimal("0.2")


def test_pnl_calculation_buy_loss():
    """
    BUY: entry=100, SL=90 → LOSS.
    realized_pnl   = (90 - 100) * 1 = -10
    realized_return = -10 / 100 = -0.1
    """
    tracker = SignalOutcomeTracker()
    obs = make_observation(
        entry_price=Decimal("100"),
        take_profit=Decimal("110"),
        stop_loss=Decimal("90"),
    )
    tracker.register(obs)

    candle = make_candle(
        open_=Decimal("100"), high=Decimal("105"), low=Decimal("90"), close=Decimal("92"),
        timestamp=ts(1),
    )
    outcomes = tracker.process_candle(candle)

    o = outcomes[0]
    assert o.status == SignalOutcomeStatus.LOSS
    assert o.realized_pnl == Decimal("-10")
    assert o.realized_return == Decimal("-0.1")


# ---------------------------------------------------------------------------
# 22. Resolved outcome is a SignalOutcome (6C.1 contract)
# ---------------------------------------------------------------------------

def test_outcome_uses_6c1_signal_outcome_contract():
    """Every resolved outcome must be a genuine SignalOutcome (6C.1 contract)."""
    tracker = SignalOutcomeTracker()
    tracker.register(make_observation(take_profit=Decimal("110"), stop_loss=Decimal("90")))

    candle = make_candle(
        open_=Decimal("100"), high=Decimal("112"), low=Decimal("98"), close=Decimal("110"),
        timestamp=ts(1),
    )
    outcomes = tracker.process_candle(candle)

    assert len(outcomes) == 1
    assert isinstance(outcomes[0], SignalOutcome)
    # Must survive round-trip through its own contract methods
    d = outcomes[0].to_dict()
    restored = SignalOutcome.from_dict(d)
    assert restored.status == outcomes[0].status
    assert restored.signal_id == outcomes[0].signal_id


# ---------------------------------------------------------------------------
# 23. reset() clears all state
# ---------------------------------------------------------------------------

def test_reset_clears_state():
    """After reset(), both active and resolved lists are empty."""
    tracker = SignalOutcomeTracker()
    tracker.register(make_observation("sig_A"))
    tracker.register(make_observation("sig_B"))

    candle = make_candle(
        open_=Decimal("100"), high=Decimal("112"), low=Decimal("98"), close=Decimal("110"),
        timestamp=ts(1),
    )
    tracker.process_candle(candle)

    # Before reset: some state exists
    assert len(tracker.resolved_outcomes) >= 0

    tracker.reset()

    assert tracker.pending_signals == []
    assert tracker.resolved_outcomes == []


# ---------------------------------------------------------------------------
# Additional edge-case tests
# ---------------------------------------------------------------------------

def test_config_invalid_ambiguity_rule():
    """OutcomeEvaluationConfig rejects unknown ambiguity rules."""
    with pytest.raises(ValueError, match="tp_sl_ambiguity_rule"):
        OutcomeEvaluationConfig(tp_sl_ambiguity_rule="unknown_rule")


def test_config_negative_breakeven_threshold():
    """OutcomeEvaluationConfig rejects negative breakeven_threshold."""
    with pytest.raises(ValueError, match="breakeven_threshold"):
        OutcomeEvaluationConfig(breakeven_threshold=Decimal("-0.01"))


def test_config_zero_max_candles():
    """OutcomeEvaluationConfig rejects max_candles=0."""
    with pytest.raises(ValueError, match="max_candles"):
        OutcomeEvaluationConfig(max_candles=0)


def test_flush_expired_naive_timestamp_raises():
    """flush_expired rejects a naive (tz-unaware) timestamp."""
    tracker = SignalOutcomeTracker()
    tracker.register(make_observation())
    naive_ts = datetime(2024, 1, 1, 12, 0, 0)  # no tzinfo

    with pytest.raises(OutcomeTrackerStateError):
        tracker.flush_expired(naive_ts)


def test_candle_seen_count_only_increments_for_eligible_candles():
    """
    candles_seen must not increment for candles before the signal timestamp.
    Verifies that with max_candles=2 and one pre-signal candle, the signal
    does not expire prematurely.
    """
    signal_ts = ts(5)
    config = OutcomeEvaluationConfig(max_candles=2)
    tracker = SignalOutcomeTracker(config)
    obs = make_observation(
        timestamp=signal_ts,
        take_profit=Decimal("110"),
        stop_loss=Decimal("90"),
    )
    tracker.register(obs)

    # Pre-signal candle → must not count
    early = neutral_candle(ts(3))
    tracker.process_candle(early)
    assert "sig_001" in tracker.pending_signals

    # First eligible candle (ts=5 == signal_ts) → candles_seen becomes 1
    tracker.process_candle(neutral_candle(signal_ts))
    assert "sig_001" in tracker.pending_signals

    # Second eligible candle → candles_seen becomes 2 → EXPIRED
    outcomes = tracker.process_candle(neutral_candle(ts(6)))
    assert len(outcomes) == 1
    assert outcomes[0].status == SignalOutcomeStatus.EXPIRED


def test_multiple_signals_same_candle_resolved_independently():
    """
    Process two signals that both resolve on the same candle.
    Both must appear in the returned outcomes list.
    """
    tracker = SignalOutcomeTracker()
    obs_a = make_observation(
        signal_id="sig_A",
        entry_price=Decimal("100"),
        take_profit=Decimal("110"),
        stop_loss=Decimal("90"),
    )
    obs_b = make_observation(
        signal_id="sig_B",
        entry_price=Decimal("100"),
        take_profit=Decimal("110"),
        stop_loss=Decimal("90"),
    )
    tracker.register(obs_a)
    tracker.register(obs_b)

    candle = make_candle(
        open_=Decimal("100"), high=Decimal("112"), low=Decimal("98"), close=Decimal("110"),
        timestamp=ts(1),
    )
    outcomes = tracker.process_candle(candle)

    assert len(outcomes) == 2
    ids = {o.signal_id for o in outcomes}
    assert ids == {"sig_A", "sig_B"}
    assert all(o.status == SignalOutcomeStatus.WIN for o in outcomes)
    assert tracker.pending_signals == []
