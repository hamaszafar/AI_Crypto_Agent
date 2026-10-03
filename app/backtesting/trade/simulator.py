from datetime import datetime
from decimal import Decimal
from typing import List, Optional
import uuid

from app.backtesting.contracts.config import BacktestConfig
from app.backtesting.contracts.enums import TradeStatus
from app.backtesting.contracts.signal_observation import SignalObservation
from app.backtesting.contracts.trade import SimulatedTrade
from app.backtesting.trade.sizing import resolve_position_size
from app.market_data.models import MarketCandle
from app.signals.models import SignalDirection
from app.backtesting.outcome.config import TP_SL_AMBIGUITY_SL_WINS


class TradeSimulator:
    """
    Trade Simulator responsible for tracking open trades, processing candles,
    and closing trades based on Take Profit / Stop Loss conditions.
    """

    def __init__(
        self,
        config: BacktestConfig,
        capital: Decimal,
        tp_sl_ambiguity_rule: str = TP_SL_AMBIGUITY_SL_WINS,
    ) -> None:
        self._config = config
        self._capital = capital
        self._tp_sl_ambiguity_rule = tp_sl_ambiguity_rule
        self._active_trades: List[SimulatedTrade] = []
        self._closed_trades: List[SimulatedTrade] = []
        self._trades_opened = 0
        self._trades_closed = 0

    @property
    def capital(self) -> Decimal:
        return self._capital

    @property
    def active_trades(self) -> List[SimulatedTrade]:
        return list(self._active_trades)

    @property
    def closed_trades(self) -> List[SimulatedTrade]:
        return list(self._closed_trades)

    @property
    def trades_opened(self) -> int:
        return self._trades_opened

    @property
    def trades_closed(self) -> int:
        return self._trades_closed

    def on_signal(self, observation: SignalObservation) -> Optional[SimulatedTrade]:
        """
        Process a new signal observation and optionally open a trade.
        """
        if observation.direction == SignalDirection.HOLD:
            return None

        # Resolve quantity
        quantity = resolve_position_size(observation, self._config, self._capital)

        trade_id = f"trd_{observation.timestamp.timestamp()}_{uuid.uuid4().hex[:6]}"
        
        trade = SimulatedTrade(
            trade_id=trade_id,
            source_signal_id=observation.signal_id,
            exchange=observation.exchange,
            symbol=observation.symbol,
            timeframe=observation.timeframe,
            direction=observation.direction,
            entry_timestamp=observation.timestamp,
            entry_price=observation.entry_price,
            quantity=quantity,
            stop_loss=observation.stop_loss,
            take_profit=observation.take_profit,
            fees=Decimal("0"),
            slippage=Decimal("0"),
            status=TradeStatus.OPEN,
        )

        self._active_trades.append(trade)
        self._trades_opened += 1
        return trade

    def process_candle(self, candle: MarketCandle) -> List[SimulatedTrade]:
        """
        Evaluate all active trades against the current candle.
        """
        newly_closed: List[SimulatedTrade] = []
        still_open: List[SimulatedTrade] = []

        for trade in self._active_trades:
            # Future-candle protection (a candle shouldn't close a trade on the same bar it was opened,
            # or before it was opened)
            if candle.timestamp <= trade.entry_timestamp:
                still_open.append(trade)
                continue

            tp_hit = False
            sl_hit = False

            if trade.direction == SignalDirection.BUY:
                tp_hit = trade.take_profit is not None and candle.high >= trade.take_profit
                sl_hit = trade.stop_loss is not None and candle.low <= trade.stop_loss
            elif trade.direction == SignalDirection.SELL:
                tp_hit = trade.take_profit is not None and candle.low <= trade.take_profit
                sl_hit = trade.stop_loss is not None and candle.high >= trade.stop_loss

            if tp_hit and sl_hit:
                if self._tp_sl_ambiguity_rule == TP_SL_AMBIGUITY_SL_WINS:
                    tp_hit = False
                else:
                    sl_hit = False

            if tp_hit or sl_hit:
                exit_price = trade.take_profit if tp_hit else trade.stop_loss
                reason = "take_profit" if tp_hit else "stop_loss"
                # For typing: we checked above that it's not None
                assert exit_price is not None

                closed_trade = self._close_trade(
                    trade,
                    exit_timestamp=candle.timestamp,
                    exit_price=exit_price,
                    exit_reason=reason,
                )
                newly_closed.append(closed_trade)
                self._closed_trades.append(closed_trade)
                self._trades_closed += 1
            else:
                still_open.append(trade)

        self._active_trades = still_open
        return newly_closed

    def flush_expired(self, current_ts: datetime, exit_price: Decimal) -> List[SimulatedTrade]:
        """
        Force-close any open trades at the end of the backtest.
        """
        newly_closed: List[SimulatedTrade] = []

        for trade in self._active_trades:
            closed_trade = self._close_trade(
                trade,
                exit_timestamp=current_ts,
                exit_price=exit_price,
                exit_reason="flush_expired",
            )
            newly_closed.append(closed_trade)
            self._closed_trades.append(closed_trade)
            self._trades_closed += 1

        self._active_trades.clear()
        return newly_closed

    def _close_trade(
        self,
        trade: SimulatedTrade,
        exit_timestamp: datetime,
        exit_price: Decimal,
        exit_reason: str,
    ) -> SimulatedTrade:
        """
        Return a new SimulatedTrade with CLOSED status and calculated PnL, fees, and slippage.
        """
        trade_value_entry = trade.quantity * trade.entry_price
        trade_value_exit = trade.quantity * exit_price

        # Basic fees
        entry_fee = trade_value_entry * self._config.fee_rate
        exit_fee = trade_value_exit * self._config.fee_rate
        total_fees = entry_fee + exit_fee

        # Slippage approximation based on trade value
        entry_slippage = trade_value_entry * self._config.slippage_rate
        exit_slippage = trade_value_exit * self._config.slippage_rate
        total_slippage = entry_slippage + exit_slippage

        direction_sign = Decimal("1") if trade.direction == SignalDirection.BUY else Decimal("-1")
        
        # Realized PnL strictly from price difference, before fees and slippage
        # or after? Usually realized_pnl includes fees/slippage. Let's include them.
        gross_pnl = (exit_price - trade.entry_price) * trade.quantity * direction_sign
        net_pnl = gross_pnl - total_fees - total_slippage

        # Update capital
        self._capital += net_pnl

        return SimulatedTrade(
            trade_id=trade.trade_id,
            source_signal_id=trade.source_signal_id,
            exchange=trade.exchange,
            symbol=trade.symbol,
            timeframe=trade.timeframe,
            direction=trade.direction,
            entry_timestamp=trade.entry_timestamp,
            entry_price=trade.entry_price,
            quantity=trade.quantity,
            stop_loss=trade.stop_loss,
            take_profit=trade.take_profit,
            exit_timestamp=exit_timestamp,
            exit_price=exit_price,
            fees=total_fees,
            slippage=total_slippage,
            realized_pnl=net_pnl,
            status=TradeStatus.CLOSED,
            exit_reason=exit_reason,
        )
