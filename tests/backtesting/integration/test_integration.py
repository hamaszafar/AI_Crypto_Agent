"""
Module 6C.5 - Backtest Integration & Validation

E2E tests validating the full backtesting flow:
Historical Candles -> Replay Engine -> Signal Generation -> Signal Outcome Tracking -> Trade Simulation -> Performance Metrics -> ReplayResult
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.backtesting.datasets.models import HistoricalDataset
from app.backtesting.datasets.metadata import DatasetMetadata
from app.backtesting.replay.models import ReplayRequest
from app.backtesting.replay.orchestrator import ReplayOrchestrator, ReplayRunStatus, ReplayResult
from app.backtesting.contracts.config import BacktestConfig, PositionSizingConfig
from app.backtesting.contracts.enums import PositionSizingType, TradeStatus, SignalOutcomeStatus
from app.backtesting.trade.simulator import TradeSimulator
from app.backtesting.outcome.tracker import SignalOutcomeTracker
from app.backtesting.outcome.config import OutcomeEvaluationConfig
from app.indicators.engine import IndicatorEngine
from app.indicators.base import BaseIndicator
from app.indicators.models import IndicatorMetadata, IndicatorResult
from app.indicators.input import IndicatorInput
from app.signals.engine import SignalEngine
from app.signals.models import Signal, SignalDirection, SignalStrength, SignalConfidence
from app.market_data.models import MarketCandle


# ---------------------------------------------------------------------------
# Test Mocks and Helpers
# ---------------------------------------------------------------------------

def make_candle(
    dt: datetime,
    close: Decimal,
    open_: Decimal = Decimal("100"),
    high: Decimal = Decimal("150"),
    low: Decimal = Decimal("50"),
    timeframe: str = "15m",
) -> MarketCandle:
    # Ensure high/low bound the open/close
    high = max(high, open_, close)
    low = min(low, open_, close)
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


class MockCloseIndicator(BaseIndicator):
    """Returns the latest close price."""
    @property
    def metadata(self) -> IndicatorMetadata:
        return IndicatorMetadata(name="MOCK_CLOSE", description="Close", minimum_period=1)

    def calculate(self, data: IndicatorInput) -> IndicatorResult:
        latest = data.latest
        return IndicatorResult(
            indicator_name=self.metadata.name,
            timestamp=latest.timestamp,
            values={"close": latest.close},
        )


class MockSignalEngine(SignalEngine):
    """Generates signals deterministically based on close price."""
    def generate(self, indicators: dict, context: dict) -> Signal:
        close_price = indicators.get("MOCK_CLOSE_close", Decimal("100"))
        # Buy if close < 100, Sell if close > 100, Hold otherwise
        if close_price < Decimal("100"):
            direction = SignalDirection.BUY
            # Set TP to 110, SL to 80 for BUY
            metadata = {"take_profit": "110", "stop_loss": "80"}
        elif close_price > Decimal("100"):
            direction = SignalDirection.SELL
            # Set TP to 90, SL to 120 for SELL
            metadata = {"take_profit": "90", "stop_loss": "120"}
        else:
            direction = SignalDirection.HOLD
            metadata = {}

        # The base Signal observation logic will need take_profit and stop_loss to actually use them in trade sim
        # but in our test we override SignalObservation.from_signal or we just rely on trade sim receiving none?
        # Actually, in orchestrator, obs = SignalObservation.from_signal(signal, entry_price). 
        # By default Signal doesn't have TP/SL properties natively unless they are in metadata and extracted by `from_signal`.
        # Wait, Signal does not have TP/SL properties? It has `metadata`. Does `from_signal` extract them?
        # Let's see: `SignalObservation.from_signal` takes kwargs. Let's just create a custom SignalEngine or let trade sim run without TP/SL and close on reverse signals?
        # TradeSimulator closes trades on TP/SL if they are set in observation.
        # But `orchestrator.py` just calls: `obs = SignalObservation.from_signal(signal=signal, entry_price=event.candle.close)`
        # `from_signal` does not automatically populate `stop_loss` and `take_profit` unless passed as kwargs.
        return Signal(
            direction=direction,
            strength=SignalStrength.STRONG,
            confidence=SignalConfidence.HIGH,
            score=Decimal("1.0"),
            context=context,
            evidences=(),
        )


# Since orchestrator.py doesn't extract TP/SL from metadata in `from_signal`, we might monkeypatch it or just have 
# trades open and never close until flush_expired, unless we patch orchestrator to extract them.
# Let's patch orchestrator inside our test setup to extract TP/SL from metadata.
# Or better yet, we can monkey-patch `SignalObservation.from_signal` to extract it.
original_from_signal = None

def setup_module():
    global original_from_signal
    from app.backtesting.contracts.signal_observation import SignalObservation
    original_from_signal = SignalObservation.from_signal

    def mock_from_signal(signal: Signal, entry_price: Decimal, **kwargs):
        if signal.direction == SignalDirection.BUY:
            kwargs["take_profit"] = Decimal("110")
            kwargs["stop_loss"] = Decimal("80")
        elif signal.direction == SignalDirection.SELL:
            kwargs["take_profit"] = Decimal("90")
            kwargs["stop_loss"] = Decimal("120")
        return original_from_signal(signal, entry_price, **kwargs)
    
    SignalObservation.from_signal = mock_from_signal

def teardown_module():
    from app.backtesting.contracts.signal_observation import SignalObservation
    SignalObservation.from_signal = original_from_signal


def make_backtest_config(start_time: datetime, end_time: datetime) -> BacktestConfig:
    return BacktestConfig(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
        start_time=start_time,
        end_time=end_time,
        initial_capital=Decimal("10000"),
        position_sizing=PositionSizingConfig(sizing_type=PositionSizingType.FIXED_AMOUNT, value=Decimal("1")),
        fee_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.002"),
    )


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------

def test_full_backtest_integration():
    """Test full e2e flow with LONG, SHORT, multiple trades, PnL, metrics, and fees."""
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    # 1. Close = 100 -> HOLD
    # 2. Close = 90  -> BUY signal (TP: 110, SL: 80), entry = 90
    # 3. Close = 95, High = 100, Low = 90 -> Trade OPEN
    # 4. Close = 115, High = 115, Low = 95 -> Trade CLOSES (hits TP: 110). SELL signal generated (TP: 90, SL: 120), entry = 115
    # 5. Close = 85, Low = 85, High = 115 -> Trade CLOSES (hits TP: 90). BUY signal generated (TP: 110, SL: 80), entry = 85
    # 6. Close = 85 -> Open trade remains
    # 7. End of replay -> flush expired
    candles = [
        make_candle(start + timedelta(minutes=0), close=Decimal("100")),
        make_candle(start + timedelta(minutes=15), close=Decimal("90"), low=Decimal("85")),
        make_candle(start + timedelta(minutes=30), close=Decimal("95"), high=Decimal("100"), low=Decimal("90")),
        make_candle(start + timedelta(minutes=45), close=Decimal("115"), high=Decimal("115"), low=Decimal("95")),
        make_candle(start + timedelta(minutes=60), close=Decimal("85"), high=Decimal("115"), low=Decimal("85")),
        make_candle(start + timedelta(minutes=75), close=Decimal("85"), high=Decimal("90"), low=Decimal("80")),
    ]
    meta = DatasetMetadata(
        exchange="binance", symbol="BTC/USDT", timeframe="15m",
        start_timestamp=candles[0].timestamp, end_timestamp=candles[-1].timestamp, candle_count=len(candles)
    )
    dataset = HistoricalDataset(candles=tuple(candles), metadata=meta)

    config = make_backtest_config(candles[0].timestamp, candles[-1].timestamp)
    
    trade_simulator = TradeSimulator(config=config, capital=config.initial_capital)
    outcome_tracker = SignalOutcomeTracker(OutcomeEvaluationConfig())
    orchestrator = ReplayOrchestrator(
        indicator_engine=IndicatorEngine([MockCloseIndicator()]),
        signal_engine=MockSignalEngine(),
        lookback=1,
        skip_unwarmed=False,
        trade_simulator=trade_simulator,
        outcome_tracker=outcome_tracker,
    )

    request = ReplayRequest(dataset=dataset)
    result = orchestrator.run(request)

    # 1. ReplayResult Completeness
    assert result.status == ReplayRunStatus.COMPLETED
    assert result.candles_processed == 6
    assert result.signals_generated == 6
    assert result.leakage_violations == 0

    # 2. Trades and Signal Outcomes
    # Signals generated:
    # idx 0: close 100 -> HOLD (invalid for outcome tracking)
    # idx 1: close 90 -> BUY (registered)
    # idx 2: close 95 -> BUY (registered)
    # idx 3: close 115 -> SELL (registered)
    # idx 4: close 85 -> BUY (registered)
    # idx 5: close 85 -> BUY (registered)
    # Valid tracking signals: 5. Some resolve, some flushed.
    assert len(result.signal_outcomes) == 5
    
    assert result.trades_opened == 5
    # Some trades closed normally, rest flushed
    assert result.trades_closed == 5 
    assert len(result.trades) == 5

    assert result.metrics is not None
    assert result.metrics.total_trades == 5

    # Check the first BUY trade (from candle idx 1, entry price 90)
    # Expected to close on candle idx 3 (high 115 >= TP 110)
    trade_1 = result.trades[0]
    assert trade_1.direction == SignalDirection.BUY
    assert trade_1.entry_price == Decimal("90")
    assert trade_1.exit_price == Decimal("110")
    assert trade_1.exit_reason == "take_profit"
    
    # Check Fees and Slippage
    # entry val: 90*1, exit val: 110*1
    # fee: (90+110)*0.001 = 0.2
    # slip: (90+110)*0.002 = 0.4
    assert trade_1.fees == Decimal("0.2")
    assert trade_1.slippage == Decimal("0.4")
    # Realized PnL: Gross = (110-90)*1 = 20. Net = 20 - 0.2 - 0.4 = 19.4
    assert trade_1.realized_pnl == Decimal("19.4")

    # The tracker should also show this as a WIN
    # Note: the first outcome might be from the first BUY signal
    # We can check that at least one outcome is a WIN
    win_outcomes = [o for o in result.signal_outcomes if o.status == SignalOutcomeStatus.WIN]
    assert len(win_outcomes) >= 1

    # Check the SELL trade (from candle idx 3, entry price 115)
    # Expected to close on candle idx 4 (low 85 <= TP 90)
    trade_sell = result.trades[2]
    assert trade_sell.direction == SignalDirection.SELL
    assert trade_sell.entry_price == Decimal("115")
    assert trade_sell.exit_price == Decimal("90")
    assert trade_sell.exit_reason == "take_profit"
    # Realized PnL: Gross = (115-90)*1 = 25. Net = 25 - (115+90)*(0.003) = 25 - 0.615 = 24.385
    assert trade_sell.realized_pnl == Decimal("25") - Decimal("205") * Decimal("0.003")

    # 3. Metrics Consistency
    assert result.metrics.total_trades == 5
    assert result.metrics.total_fees == sum([t.fees for t in result.trades])
    assert result.metrics.total_slippage == sum([t.slippage for t in result.trades])
    assert result.metrics.net_pnl == sum([t.realized_pnl for t in result.trades])
    
    # Equity curve length should match closed trades
    assert len(result.metrics.equity_curve) == 5


def test_no_signal_no_trade():
    """Ensure backtest works perfectly when no trades are executed."""
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    # All closes at 100 -> HOLD signals only
    candles = [make_candle(start + timedelta(minutes=i*15), close=Decimal("100")) for i in range(5)]
    meta = DatasetMetadata(exchange="binance", symbol="BTC/USDT", timeframe="15m", start_timestamp=candles[0].timestamp, end_timestamp=candles[-1].timestamp, candle_count=5)
    dataset = HistoricalDataset(candles=tuple(candles), metadata=meta)
    
    config = make_backtest_config(candles[0].timestamp, candles[-1].timestamp)
    orchestrator = ReplayOrchestrator(
        indicator_engine=IndicatorEngine([MockCloseIndicator()]),
        signal_engine=MockSignalEngine(),
        lookback=1,
        skip_unwarmed=False,
        trade_simulator=TradeSimulator(config=config, capital=config.initial_capital),
        outcome_tracker=SignalOutcomeTracker(OutcomeEvaluationConfig()),
    )
    result = orchestrator.run(ReplayRequest(dataset=dataset))

    assert result.status == ReplayRunStatus.COMPLETED
    assert result.candles_processed == 5
    assert result.signals_generated == 5
    assert result.trades_opened == 0
    assert result.trades_closed == 0
    assert len(result.trades) == 0
    assert len(result.signal_outcomes) == 0
    
    assert result.metrics is not None
    assert result.metrics.total_trades == 0
    assert result.metrics.net_pnl == Decimal("0")


def test_leakage_protection_preservation():
    """Ensure we haven't broken the future data leakage guard."""
    # We can inject a mock that tries to access future data if we want,
    # but test_orchestrator.py already tests this via LeakageGuard.
    # We just ensure the guard still works.
    from app.backtesting.replay.leakage.guard import LeakageGuard
    from app.backtesting.replay.context.models import ContextWindow
    from app.backtesting.replay.leakage.exceptions import FutureDataDetectedError

    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    candles = [make_candle(start, close=Decimal("100")), make_candle(start + timedelta(minutes=15), close=Decimal("101"))]
    window = ContextWindow(
        candles=tuple(candles),
        lookback_size=2,
        replay_timestamp=start,
    )
    
    # Try to validate with replay_ts older than the latest candle
    with pytest.raises(FutureDataDetectedError):
        LeakageGuard.validate_context(window, replay_timestamp=start)


def test_multiple_simultaneous_trades():
    """Ensure the system handles multiple open trades at once."""
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    # 1. Close = 90 -> BUY
    # 2. Close = 90 -> BUY
    # 3. Close = 115 -> Both close on TP (110)
    candles = [
        make_candle(start, close=Decimal("90"), low=Decimal("85")),
        make_candle(start + timedelta(minutes=15), close=Decimal("90"), low=Decimal("85")),
        make_candle(start + timedelta(minutes=30), close=Decimal("115"), high=Decimal("115"), low=Decimal("90")),
    ]
    meta = DatasetMetadata(exchange="binance", symbol="BTC/USDT", timeframe="15m", start_timestamp=candles[0].timestamp, end_timestamp=candles[-1].timestamp, candle_count=3)
    dataset = HistoricalDataset(candles=tuple(candles), metadata=meta)
    
    config = make_backtest_config(candles[0].timestamp, candles[-1].timestamp)
    orchestrator = ReplayOrchestrator(
        indicator_engine=IndicatorEngine([MockCloseIndicator()]),
        signal_engine=MockSignalEngine(),
        lookback=1,
        skip_unwarmed=False,
        trade_simulator=TradeSimulator(config=config, capital=config.initial_capital),
        outcome_tracker=SignalOutcomeTracker(OutcomeEvaluationConfig()),
    )
    result = orchestrator.run(ReplayRequest(dataset=dataset))

    assert result.status == ReplayRunStatus.COMPLETED
    assert result.trades_opened == 3
    assert result.trades_closed == 3 # the 3rd one opens on 115 and is flushed
    
    # First 2 trades should exit at 110
    trade_1 = result.trades[0]
    trade_2 = result.trades[1]
    
    assert trade_1.exit_price == Decimal("110")
    assert trade_2.exit_price == Decimal("110")
    assert trade_1.exit_reason == "take_profit"
    assert trade_2.exit_reason == "take_profit"
    
    # Outcomes: 3 outcomes (the 3 signals). First 2 should be WIN.
    assert result.signals_resolved == 3
    wins = [o for o in result.signal_outcomes if o.status == SignalOutcomeStatus.WIN]
    assert len(wins) == 2
