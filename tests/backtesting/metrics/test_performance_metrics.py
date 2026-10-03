"""
Tests for Module 6C.4 — Performance Metrics.
"""

import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List

from app.backtesting.contracts.enums import TradeStatus
from app.backtesting.contracts.trade import SimulatedTrade
from app.backtesting.metrics.calculator import (
    PerformanceMetrics,
    calculate_performance_metrics,
)
from app.signals.models import SignalDirection

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_T0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
_D = Decimal


def _trade(
    pnl: Decimal,
    fees: Decimal = _D("0"),
    slippage: Decimal = _D("0"),
    status: TradeStatus = TradeStatus.CLOSED,
    direction: SignalDirection = SignalDirection.BUY,
    entry_price: Decimal = _D("100"),
    exit_price: Decimal = _D("110"),
) -> SimulatedTrade:
    """Build a minimal SimulatedTrade fixture."""
    entry_ts = _T0
    exit_ts = _T0 + timedelta(hours=1) if status == TradeStatus.CLOSED else None
    ep = exit_price if status == TradeStatus.CLOSED else None
    return SimulatedTrade(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="15m",
        direction=direction,
        entry_timestamp=entry_ts,
        entry_price=entry_price,
        quantity=_D("1"),
        exit_timestamp=exit_ts,
        exit_price=ep,
        fees=fees,
        slippage=slippage,
        realized_pnl=pnl if status == TradeStatus.CLOSED else None,
        status=status,
        exit_reason="test" if status == TradeStatus.CLOSED else None,
    )


# ---------------------------------------------------------------------------
# Zero-trade edge cases
# ---------------------------------------------------------------------------

class TestZeroTrades:
    def test_empty_list(self):
        m = calculate_performance_metrics([])
        assert m.total_trades == 0
        assert m.winning_trades == 0
        assert m.losing_trades == 0
        assert m.breakeven_trades == 0
        assert m.win_rate == _D("0")
        assert m.loss_rate == _D("0")
        assert m.gross_profit == _D("0")
        assert m.gross_loss == _D("0")
        assert m.net_pnl == _D("0")
        assert m.avg_trade_pnl == _D("0")
        assert m.avg_win == _D("0")
        assert m.avg_loss == _D("0")
        assert m.largest_win == _D("0")
        assert m.largest_loss == _D("0")
        assert m.profit_factor is None
        assert m.expectancy == _D("0")
        assert m.payoff_ratio is None
        assert m.equity_curve == ()
        assert m.max_drawdown == _D("0")
        assert m.max_drawdown_pct == _D("0")
        assert m.total_fees == _D("0")
        assert m.total_slippage == _D("0")

    def test_only_open_trades_excluded(self):
        open_trade = _trade(_D("50"), status=TradeStatus.OPEN)
        m = calculate_performance_metrics([open_trade])
        assert m.total_trades == 0

    def test_pending_and_cancelled_excluded(self):
        t1 = _trade(_D("10"), status=TradeStatus.PENDING)
        t2 = _trade(_D("10"), status=TradeStatus.CANCELLED)
        m = calculate_performance_metrics([t1, t2])
        assert m.total_trades == 0


# ---------------------------------------------------------------------------
# All-win scenario
# ---------------------------------------------------------------------------

class TestAllWins:
    def setup_method(self):
        self.trades = [
            _trade(_D("100")),
            _trade(_D("50")),
            _trade(_D("200")),
        ]
        self.m = calculate_performance_metrics(self.trades)

    def test_counts(self):
        assert self.m.total_trades == 3
        assert self.m.winning_trades == 3
        assert self.m.losing_trades == 0
        assert self.m.breakeven_trades == 0

    def test_rates(self):
        assert self.m.win_rate == _D("1")
        assert self.m.loss_rate == _D("0")

    def test_pnl(self):
        assert self.m.gross_profit == _D("350")
        assert self.m.gross_loss == _D("0")
        assert self.m.net_pnl == _D("350")

    def test_averages(self):
        assert self.m.avg_win == _D("350") / _D("3")
        assert self.m.avg_loss == _D("0")

    def test_extremes(self):
        assert self.m.largest_win == _D("200")
        assert self.m.largest_loss == _D("0")

    def test_profit_factor_none_when_no_loss(self):
        # gross_loss == 0 → profit_factor is None
        assert self.m.profit_factor is None

    def test_payoff_ratio_none_when_no_loss(self):
        assert self.m.payoff_ratio is None


# ---------------------------------------------------------------------------
# All-loss scenario
# ---------------------------------------------------------------------------

class TestAllLosses:
    def setup_method(self):
        self.trades = [_trade(_D("-50")), _trade(_D("-30"))]
        self.m = calculate_performance_metrics(self.trades)

    def test_counts(self):
        assert self.m.total_trades == 2
        assert self.m.winning_trades == 0
        assert self.m.losing_trades == 2

    def test_rates(self):
        assert self.m.win_rate == _D("0")
        assert self.m.loss_rate == _D("1")

    def test_pnl(self):
        assert self.m.gross_profit == _D("0")
        assert self.m.gross_loss == _D("-80")
        assert self.m.net_pnl == _D("-80")

    def test_profit_factor_zero_numerator(self):
        # gross_profit == 0, gross_loss < 0 → profit_factor = 0
        assert self.m.profit_factor == _D("0")

    def test_expectancy_negative(self):
        assert self.m.expectancy < _D("0")

    def test_avg_win_zero(self):
        assert self.m.avg_win == _D("0")

    def test_largest_win_zero(self):
        assert self.m.largest_win == _D("0")


# ---------------------------------------------------------------------------
# Mixed trades (normal profitable)
# ---------------------------------------------------------------------------

class TestMixedProfitable:
    def setup_method(self):
        self.trades = [
            _trade(_D("100")),
            _trade(_D("-40")),
            _trade(_D("60")),
            _trade(_D("-20")),
        ]
        self.m = calculate_performance_metrics(self.trades, initial_equity=_D("1000"))

    def test_counts(self):
        assert self.m.total_trades == 4
        assert self.m.winning_trades == 2
        assert self.m.losing_trades == 2

    def test_win_rate(self):
        assert self.m.win_rate == _D("0.5")
        assert self.m.loss_rate == _D("0.5")

    def test_pnl(self):
        assert self.m.gross_profit == _D("160")
        assert self.m.gross_loss == _D("-60")
        assert self.m.net_pnl == _D("100")

    def test_profit_factor(self):
        assert self.m.profit_factor == _D("160") / _D("60")

    def test_avg_win(self):
        assert self.m.avg_win == _D("80")

    def test_avg_loss(self):
        assert self.m.avg_loss == _D("-30")

    def test_payoff_ratio(self):
        assert self.m.payoff_ratio == _D("80") / _D("30")

    def test_largest_win(self):
        assert self.m.largest_win == _D("100")

    def test_largest_loss(self):
        assert self.m.largest_loss == _D("-40")

    def test_expectancy(self):
        expected = (_D("0.5") * _D("80")) + (_D("0.5") * _D("-30"))
        assert self.m.expectancy == expected

    def test_equity_curve_length(self):
        assert len(self.m.equity_curve) == 4

    def test_equity_curve_values(self):
        curve = self.m.equity_curve
        assert curve[0] == _D("1100")   # 1000 + 100
        assert curve[1] == _D("1060")   # 1100 - 40
        assert curve[2] == _D("1120")   # 1060 + 60
        assert curve[3] == _D("1100")   # 1120 - 20


# ---------------------------------------------------------------------------
# Losing result
# ---------------------------------------------------------------------------

class TestLosingResult:
    def setup_method(self):
        self.trades = [
            _trade(_D("10")),
            _trade(_D("-50")),
            _trade(_D("-30")),
        ]
        self.m = calculate_performance_metrics(self.trades)

    def test_net_pnl_negative(self):
        assert self.m.net_pnl == _D("-70")

    def test_profit_factor_lt_1(self):
        assert self.m.profit_factor == _D("10") / _D("80")

    def test_expectancy_negative(self):
        assert self.m.expectancy < _D("0")


# ---------------------------------------------------------------------------
# Breakeven trades
# ---------------------------------------------------------------------------

class TestBreakevenTrades:
    def setup_method(self):
        self.trades = [
            _trade(_D("10")),
            _trade(_D("0")),   # breakeven
            _trade(_D("-5")),
            _trade(_D("0")),   # breakeven
        ]
        self.m = calculate_performance_metrics(self.trades)

    def test_breakeven_count(self):
        assert self.m.breakeven_trades == 2
        assert self.m.winning_trades == 1
        assert self.m.losing_trades == 1
        assert self.m.total_trades == 4

    def test_rates_exclude_breakeven(self):
        # win_rate = 1/4, loss_rate = 1/4
        assert self.m.win_rate == _D("1") / _D("4")
        assert self.m.loss_rate == _D("1") / _D("4")

    def test_gross_breakeven_not_counted_in_profit_or_loss(self):
        assert self.m.gross_profit == _D("10")
        assert self.m.gross_loss == _D("-5")


# ---------------------------------------------------------------------------
# Drawdown calculation
# ---------------------------------------------------------------------------

class TestDrawdown:
    def test_simple_drawdown(self):
        # equity: 1100 → 1050 → 1150 → 1050
        trades = [
            _trade(_D("100")),
            _trade(_D("-50")),
            _trade(_D("100")),
            _trade(_D("-100")),
        ]
        m = calculate_performance_metrics(trades, initial_equity=_D("1000"))
        # Peak after trade 3 = 1150. Drawdown = 1150 - 1050 = 100
        assert m.max_drawdown == _D("100")

    def test_no_drawdown_monotonic_growth(self):
        trades = [_trade(_D("10")), _trade(_D("20")), _trade(_D("30"))]
        m = calculate_performance_metrics(trades, initial_equity=_D("1000"))
        assert m.max_drawdown == _D("0")

    def test_drawdown_pct(self):
        trades = [_trade(_D("100")), _trade(_D("-50"))]
        m = calculate_performance_metrics(trades, initial_equity=_D("1000"))
        # Peak = 1100, drawdown = 50, pct = 50/1100 * 100
        expected_pct = _D("50") / _D("1100") * _D("100")
        assert m.max_drawdown_pct == expected_pct

    def test_drawdown_pct_zero_when_no_peak(self):
        # initial_equity = 0, all losing — peak stays 0
        trades = [_trade(_D("-10")), _trade(_D("-20"))]
        m = calculate_performance_metrics(trades, initial_equity=_D("0"))
        assert m.max_drawdown_pct == _D("0")

    def test_equity_curve_starts_from_initial(self):
        trades = [_trade(_D("50"))]
        m = calculate_performance_metrics(trades, initial_equity=_D("500"))
        assert m.equity_curve == (_D("550"),)


# ---------------------------------------------------------------------------
# Fees and slippage
# ---------------------------------------------------------------------------

class TestFeesSlippage:
    def test_total_fees_summed(self):
        trades = [
            _trade(_D("10"), fees=_D("1")),
            _trade(_D("20"), fees=_D("2")),
            _trade(_D("-5"), fees=_D("0.5")),
        ]
        m = calculate_performance_metrics(trades)
        assert m.total_fees == _D("3.5")

    def test_total_slippage_summed(self):
        trades = [
            _trade(_D("10"), slippage=_D("0.5")),
            _trade(_D("-5"), slippage=_D("0.3")),
        ]
        m = calculate_performance_metrics(trades)
        assert m.total_slippage == _D("0.8")

    def test_open_trades_fees_excluded(self):
        closed = _trade(_D("10"), fees=_D("2"))
        open_t = _trade(_D("10"), fees=_D("99"), status=TradeStatus.OPEN)
        m = calculate_performance_metrics([closed, open_t])
        assert m.total_fees == _D("2")


# ---------------------------------------------------------------------------
# Profit factor and expectancy edge cases
# ---------------------------------------------------------------------------

class TestProfitFactorExpectancy:
    def test_profit_factor_none_all_wins(self):
        m = calculate_performance_metrics([_trade(_D("50"))])
        assert m.profit_factor is None

    def test_profit_factor_zero_all_losses(self):
        m = calculate_performance_metrics([_trade(_D("-50"))])
        assert m.profit_factor == _D("0")

    def test_expectancy_all_wins(self):
        m = calculate_performance_metrics([_trade(_D("50")), _trade(_D("50"))])
        # win_rate=1, avg_win=50, loss_rate=0, avg_loss=0
        assert m.expectancy == _D("50")

    def test_expectancy_all_losses(self):
        m = calculate_performance_metrics([_trade(_D("-30")), _trade(_D("-10"))])
        # win_rate=0, loss_rate=1, avg_loss=-20
        assert m.expectancy == _D("-20")

    def test_payoff_ratio_none_no_losses(self):
        m = calculate_performance_metrics([_trade(_D("10"))])
        assert m.payoff_ratio is None


# ---------------------------------------------------------------------------
# Single-trade cases
# ---------------------------------------------------------------------------

class TestSingleTrade:
    def test_single_win(self):
        m = calculate_performance_metrics([_trade(_D("75"))])
        assert m.total_trades == 1
        assert m.winning_trades == 1
        assert m.net_pnl == _D("75")
        assert m.avg_trade_pnl == _D("75")
        assert m.win_rate == _D("1")

    def test_single_loss(self):
        m = calculate_performance_metrics([_trade(_D("-30"))])
        assert m.total_trades == 1
        assert m.losing_trades == 1
        assert m.net_pnl == _D("-30")

    def test_single_breakeven(self):
        m = calculate_performance_metrics([_trade(_D("0"))])
        assert m.total_trades == 1
        assert m.breakeven_trades == 1
        assert m.net_pnl == _D("0")
        assert m.profit_factor is None


# ---------------------------------------------------------------------------
# Regression: open trades not in realized PnL
# ---------------------------------------------------------------------------

class TestOpenTradeExclusion:
    def test_open_trade_pnl_not_included(self):
        closed = _trade(_D("100"))
        open_t = _trade(_D("999"), status=TradeStatus.OPEN)
        m = calculate_performance_metrics([closed, open_t])
        assert m.total_trades == 1
        assert m.net_pnl == _D("100")

    def test_no_realized_pnl_field_excluded(self):
        # Construct a CLOSED trade but realized_pnl=None (edge case in data)
        t = SimulatedTrade(
            exchange="binance",
            symbol="BTC/USDT",
            timeframe="15m",
            direction=SignalDirection.BUY,
            entry_timestamp=_T0,
            entry_price=_D("100"),
            quantity=_D("1"),
            exit_timestamp=_T0 + timedelta(hours=1),
            exit_price=_D("110"),
            realized_pnl=None,
            status=TradeStatus.CLOSED,
            exit_reason="test",
        )
        m = calculate_performance_metrics([t])
        assert m.total_trades == 0


# ---------------------------------------------------------------------------
# PerformanceMetrics is immutable (frozen dataclass)
# ---------------------------------------------------------------------------

class TestImmutability:
    def test_metrics_frozen(self):
        m = calculate_performance_metrics([])
        with pytest.raises((AttributeError, TypeError)):
            m.total_trades = 99  # type: ignore[misc]
