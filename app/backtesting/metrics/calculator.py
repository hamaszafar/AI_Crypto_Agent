"""
Module 6C.4 — Performance Metrics Calculator.

Pure, deterministic, exchange-independent.
Only closed SimulatedTrades with realized_pnl are included.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional, Sequence, Tuple

from app.backtesting.contracts.enums import TradeStatus
from app.backtesting.contracts.trade import SimulatedTrade

_ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class PerformanceMetrics:
    """Immutable performance summary for a set of closed simulated trades."""

    # --- Trade counts ---
    total_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int

    # --- Rates ---
    win_rate: Decimal          # winning / total  (0 if no trades)
    loss_rate: Decimal         # losing  / total  (0 if no trades)

    # --- PnL aggregates ---
    gross_profit: Decimal      # sum of positive realized_pnl
    gross_loss: Decimal        # sum of negative realized_pnl (always <= 0)
    net_pnl: Decimal           # gross_profit + gross_loss

    # --- Per-trade averages ---
    avg_trade_pnl: Decimal     # net_pnl / total  (0 if no trades)
    avg_win: Decimal           # avg winning pnl  (0 if no winners)
    avg_loss: Decimal          # avg losing pnl   (0 if no losers, <= 0)

    # --- Extremes ---
    largest_win: Decimal       # max single trade pnl (0 if no winners)
    largest_loss: Decimal      # min single trade pnl (0 if no losers, <= 0)

    # --- Ratios ---
    profit_factor: Optional[Decimal]   # gross_profit / abs(gross_loss); None if gross_loss == 0
    expectancy: Decimal                # (win_rate * avg_win) + (loss_rate * avg_loss)
    payoff_ratio: Optional[Decimal]    # avg_win / abs(avg_loss); None if avg_loss == 0

    # --- Equity & drawdown ---
    equity_curve: Tuple[Decimal, ...]  # cumulative pnl after each closed trade
    max_drawdown: Decimal              # largest peak-to-trough drop in equity (>= 0)
    max_drawdown_pct: Decimal          # max_drawdown / peak_equity * 100 (0 if peak == 0)

    # --- Cost aggregates ---
    total_fees: Decimal
    total_slippage: Decimal


def calculate_performance_metrics(
    trades: Sequence[SimulatedTrade],
    initial_equity: Decimal = _ZERO,
) -> PerformanceMetrics:
    """
    Compute PerformanceMetrics from a sequence of SimulatedTrades.

    Only CLOSED trades with a non-None realized_pnl are included in
    realized-performance calculations. Open/pending/cancelled trades
    are excluded.

    Args:
        trades: Any iterable of SimulatedTrade (may include non-closed trades).
        initial_equity: Starting equity for equity-curve and drawdown calculation.

    Returns:
        PerformanceMetrics (all fields guaranteed non-NaN, no division by zero).
    """
    closed: List[SimulatedTrade] = [
        t for t in trades
        if t.status == TradeStatus.CLOSED and t.realized_pnl is not None
    ]

    total_trades = len(closed)

    if total_trades == 0:
        return PerformanceMetrics(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            breakeven_trades=0,
            win_rate=_ZERO,
            loss_rate=_ZERO,
            gross_profit=_ZERO,
            gross_loss=_ZERO,
            net_pnl=_ZERO,
            avg_trade_pnl=_ZERO,
            avg_win=_ZERO,
            avg_loss=_ZERO,
            largest_win=_ZERO,
            largest_loss=_ZERO,
            profit_factor=None,
            expectancy=_ZERO,
            payoff_ratio=None,
            equity_curve=(),
            max_drawdown=_ZERO,
            max_drawdown_pct=_ZERO,
            total_fees=_ZERO,
            total_slippage=_ZERO,
        )

    pnls: List[Decimal] = [t.realized_pnl for t in closed]  # type: ignore[misc]

    wins = [p for p in pnls if p > _ZERO]
    losses = [p for p in pnls if p < _ZERO]
    breakevens = [p for p in pnls if p == _ZERO]

    winning_trades = len(wins)
    losing_trades = len(losses)
    breakeven_trades = len(breakevens)

    total_dec = Decimal(total_trades)
    win_rate = Decimal(winning_trades) / total_dec
    loss_rate = Decimal(losing_trades) / total_dec

    gross_profit = sum(wins, _ZERO)
    gross_loss = sum(losses, _ZERO)        # <= 0
    net_pnl = gross_profit + gross_loss

    avg_trade_pnl = net_pnl / total_dec
    avg_win = (gross_profit / Decimal(winning_trades)) if winning_trades else _ZERO
    avg_loss = (gross_loss / Decimal(losing_trades)) if losing_trades else _ZERO  # <= 0

    largest_win = max(wins, default=_ZERO)
    largest_loss = min(losses, default=_ZERO)  # <= 0

    abs_gross_loss = abs(gross_loss)
    profit_factor: Optional[Decimal] = (
        (gross_profit / abs_gross_loss) if abs_gross_loss > _ZERO else None
    )

    abs_avg_loss = abs(avg_loss)
    payoff_ratio: Optional[Decimal] = (
        (avg_win / abs_avg_loss) if abs_avg_loss > _ZERO else None
    )

    expectancy = (win_rate * avg_win) + (loss_rate * avg_loss)

    # --- Equity curve & drawdown ---
    equity_curve, max_drawdown, max_drawdown_pct = _compute_drawdown(
        pnls, initial_equity
    )

    total_fees = sum((t.fees for t in closed), _ZERO)
    total_slippage = sum((t.slippage for t in closed), _ZERO)

    return PerformanceMetrics(
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        breakeven_trades=breakeven_trades,
        win_rate=win_rate,
        loss_rate=loss_rate,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        net_pnl=net_pnl,
        avg_trade_pnl=avg_trade_pnl,
        avg_win=avg_win,
        avg_loss=avg_loss,
        largest_win=largest_win,
        largest_loss=largest_loss,
        profit_factor=profit_factor,
        expectancy=expectancy,
        payoff_ratio=payoff_ratio,
        equity_curve=equity_curve,
        max_drawdown=max_drawdown,
        max_drawdown_pct=max_drawdown_pct,
        total_fees=total_fees,
        total_slippage=total_slippage,
    )


def _compute_drawdown(
    pnls: List[Decimal],
    initial_equity: Decimal,
) -> Tuple[Tuple[Decimal, ...], Decimal, Decimal]:
    """Return (equity_curve, max_drawdown, max_drawdown_pct)."""
    curve: List[Decimal] = []
    equity = initial_equity
    peak = initial_equity
    max_dd = _ZERO

    for pnl in pnls:
        equity += pnl
        curve.append(equity)
        if equity > peak:
            peak = equity
        drawdown = peak - equity
        if drawdown > max_dd:
            max_dd = drawdown

    max_dd_pct = (max_dd / peak * Decimal("100")) if peak > _ZERO else _ZERO

    return tuple(curve), max_dd, max_dd_pct
