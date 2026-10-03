import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.backtesting.contracts.config import BacktestConfig, PositionSizingConfig
from app.backtesting.contracts.enums import PositionSizingType, TradeStatus
from app.backtesting.contracts.signal_observation import SignalObservation
from app.backtesting.trade.simulator import TradeSimulator
from app.market_data.models import MarketCandle
from app.signals.models import SignalDirection, SignalStrength, SignalConfidence
from app.backtesting.outcome.config import TP_SL_AMBIGUITY_SL_WINS, TP_SL_AMBIGUITY_TP_WINS


def make_candle(
    dt: datetime,
    open_: Decimal = Decimal("100"),
    high: Decimal = Decimal("105"),
    low: Decimal = Decimal("95"),
    close: Decimal = Decimal("100"),
) -> MarketCandle:
    return MarketCandle(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
        timestamp=dt,
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=Decimal("1000"),
    )


def make_observation(
    dt: datetime,
    direction: SignalDirection,
    entry_price: Decimal,
    stop_loss: Decimal = None,
    take_profit: Decimal = None,
    metadata: dict = None,
) -> SignalObservation:
    return SignalObservation(
        signal_id="test_signal",
        timestamp=dt,
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
        direction=direction,
        strength=SignalStrength.STRONG,
        confidence=SignalConfidence.HIGH,
        score=Decimal("0.9"),
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        metadata=metadata or {},
    )


@pytest.fixture
def default_config() -> BacktestConfig:
    return BacktestConfig(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
        start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_time=datetime(2024, 1, 2, tzinfo=timezone.utc),
        initial_capital=Decimal("10000"),
        position_sizing=PositionSizingConfig(
            sizing_type=PositionSizingType.FIXED_AMOUNT,
            value=Decimal("1"),  # 1 BTC
        ),
        fee_rate=Decimal("0"),
        slippage_rate=Decimal("0"),
    )


def test_long_trade_lifecycle(default_config):
    sim = TradeSimulator(config=default_config, capital=default_config.initial_capital)
    
    start_ts = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    obs = make_observation(
        start_ts,
        direction=SignalDirection.BUY,
        entry_price=Decimal("100"),
        take_profit=Decimal("110"),
        stop_loss=Decimal("90"),
    )
    
    trade = sim.on_signal(obs)
    assert trade is not None
    assert trade.status == TradeStatus.OPEN
    assert sim.trades_opened == 1
    assert sim.trades_closed == 0
    assert len(sim.active_trades) == 1
    
    # Process a candle that doesn't hit TP or SL
    candle1 = make_candle(start_ts + timedelta(minutes=15), low=Decimal("95"), high=Decimal("105"))
    closed = sim.process_candle(candle1)
    assert len(closed) == 0
    assert len(sim.active_trades) == 1
    
    # Process a candle that hits TP
    candle2 = make_candle(start_ts + timedelta(minutes=30), low=Decimal("95"), high=Decimal("115"))
    closed = sim.process_candle(candle2)
    assert len(closed) == 1
    assert len(sim.active_trades) == 0
    assert sim.trades_closed == 1
    
    closed_trade = closed[0]
    assert closed_trade.status == TradeStatus.CLOSED
    assert closed_trade.exit_price == Decimal("110")
    assert closed_trade.realized_pnl == Decimal("10") * Decimal("1")  # (110 - 100) * 1


def test_short_trade_lifecycle(default_config):
    sim = TradeSimulator(config=default_config, capital=default_config.initial_capital)
    
    start_ts = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    obs = make_observation(
        start_ts,
        direction=SignalDirection.SELL,
        entry_price=Decimal("100"),
        take_profit=Decimal("90"),
        stop_loss=Decimal("110"),
    )
    
    sim.on_signal(obs)
    
    # Hits TP for short (price drops to 85)
    candle = make_candle(start_ts + timedelta(minutes=15), low=Decimal("85"), high=Decimal("95"))
    closed = sim.process_candle(candle)
    
    assert len(closed) == 1
    closed_trade = closed[0]
    assert closed_trade.exit_price == Decimal("90")
    assert closed_trade.realized_pnl == Decimal("10") * Decimal("1")  # (100 - 90) * 1


def test_tp_sl_ambiguity_sl_wins(default_config):
    sim = TradeSimulator(
        config=default_config,
        capital=default_config.initial_capital,
        tp_sl_ambiguity_rule=TP_SL_AMBIGUITY_SL_WINS,
    )
    
    start_ts = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    obs = make_observation(
        start_ts,
        direction=SignalDirection.BUY,
        entry_price=Decimal("100"),
        take_profit=Decimal("110"),
        stop_loss=Decimal("90"),
    )
    sim.on_signal(obs)
    
    # Candle that hits BOTH TP and SL
    candle = make_candle(start_ts + timedelta(minutes=15), low=Decimal("80"), high=Decimal("120"))
    closed = sim.process_candle(candle)
    
    assert len(closed) == 1
    closed_trade = closed[0]
    # Under SL_WINS, SL takes precedence
    assert closed_trade.exit_price == Decimal("90")
    assert closed_trade.exit_reason == "stop_loss"
    assert closed_trade.realized_pnl == Decimal("-10")


def test_tp_sl_ambiguity_tp_wins(default_config):
    sim = TradeSimulator(
        config=default_config,
        capital=default_config.initial_capital,
        tp_sl_ambiguity_rule=TP_SL_AMBIGUITY_TP_WINS,
    )
    
    start_ts = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    obs = make_observation(
        start_ts,
        direction=SignalDirection.BUY,
        entry_price=Decimal("100"),
        take_profit=Decimal("110"),
        stop_loss=Decimal("90"),
    )
    sim.on_signal(obs)
    
    # Candle that hits BOTH TP and SL
    candle = make_candle(start_ts + timedelta(minutes=15), low=Decimal("80"), high=Decimal("120"))
    closed = sim.process_candle(candle)
    
    assert len(closed) == 1
    closed_trade = closed[0]
    # Under TP_WINS, TP takes precedence
    assert closed_trade.exit_price == Decimal("110")
    assert closed_trade.exit_reason == "take_profit"
    assert closed_trade.realized_pnl == Decimal("10")


def test_fees_and_slippage():
    # Fee: 0.1%, Slippage: 0.2%
    config = BacktestConfig(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
        start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end_time=datetime(2024, 1, 2, tzinfo=timezone.utc),
        initial_capital=Decimal("10000"),
        position_sizing=PositionSizingConfig(
            sizing_type=PositionSizingType.FIXED_AMOUNT,
            value=Decimal("1"),
        ),
        fee_rate=Decimal("0.001"),
        slippage_rate=Decimal("0.002"),
    )
    sim = TradeSimulator(config=config, capital=config.initial_capital)
    
    start_ts = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    obs = make_observation(
        start_ts,
        direction=SignalDirection.BUY,
        entry_price=Decimal("100"),
        take_profit=Decimal("110"),
    )
    sim.on_signal(obs)
    
    candle = make_candle(start_ts + timedelta(minutes=15), low=Decimal("100"), high=Decimal("115"))
    closed = sim.process_candle(candle)
    
    trade = closed[0]
    entry_value = Decimal("100") * Decimal("1")
    exit_value = Decimal("110") * Decimal("1")
    
    expected_fees = (entry_value * Decimal("0.001")) + (exit_value * Decimal("0.001"))
    expected_slippage = (entry_value * Decimal("0.002")) + (exit_value * Decimal("0.002"))
    expected_gross_pnl = Decimal("10")
    expected_net_pnl = expected_gross_pnl - expected_fees - expected_slippage
    
    assert trade.fees == expected_fees
    assert trade.slippage == expected_slippage
    assert trade.realized_pnl == expected_net_pnl
    assert sim.capital == Decimal("10000") + expected_net_pnl


def test_multiple_simultaneous_trades(default_config):
    sim = TradeSimulator(config=default_config, capital=default_config.initial_capital)
    
    start_ts = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    
    # Trade 1
    obs1 = make_observation(
        start_ts, direction=SignalDirection.BUY, entry_price=Decimal("100"), take_profit=Decimal("110")
    )
    sim.on_signal(obs1)
    
    # Trade 2
    obs2 = make_observation(
        start_ts, direction=SignalDirection.SELL, entry_price=Decimal("100"), take_profit=Decimal("90")
    )
    sim.on_signal(obs2)
    
    assert len(sim.active_trades) == 2
    
    # Process candle that hits TP for Trade 1 (price goes up)
    candle = make_candle(start_ts + timedelta(minutes=15), low=Decimal("95"), high=Decimal("115"))
    closed = sim.process_candle(candle)
    
    assert len(closed) == 1
    assert closed[0].direction == SignalDirection.BUY
    assert len(sim.active_trades) == 1
    assert sim.active_trades[0].direction == SignalDirection.SELL


def test_chronological_protection(default_config):
    sim = TradeSimulator(config=default_config, capital=default_config.initial_capital)
    
    start_ts = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    obs = make_observation(
        start_ts, direction=SignalDirection.BUY, entry_price=Decimal("100"), take_profit=Decimal("110")
    )
    sim.on_signal(obs)
    
    # Process a candle from BEFORE or EXACTLY AT the entry timestamp
    candle = make_candle(start_ts, low=Decimal("50"), high=Decimal("150"))
    closed = sim.process_candle(candle)
    
    # Should not close the trade because of chronological protection
    assert len(closed) == 0
    assert len(sim.active_trades) == 1


def test_flush_expired(default_config):
    sim = TradeSimulator(config=default_config, capital=default_config.initial_capital)
    
    start_ts = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    obs = make_observation(
        start_ts, direction=SignalDirection.BUY, entry_price=Decimal("100")
    )
    sim.on_signal(obs)
    
    end_ts = datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc)
    closed = sim.flush_expired(end_ts, exit_price=Decimal("105"))
    
    assert len(closed) == 1
    assert len(sim.active_trades) == 0
    
    trade = closed[0]
    assert trade.status == TradeStatus.CLOSED
    assert trade.exit_price == Decimal("105")
    assert trade.exit_timestamp == end_ts
    assert trade.exit_reason == "flush_expired"
    assert trade.realized_pnl == Decimal("5")
