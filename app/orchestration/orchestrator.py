"""Signal Orchestrator – coordinates market data, validation, indicator calculation, and the Phase 4 Signal Engine.

Exports:
    SignalOrchestrator – class with a ``generate`` method returning a fully‑populated ``Signal``.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Mapping

from app.exchanges.base import BaseExchange
from app.indicators.engine import IndicatorEngine
from app.market_data.pipeline import MarketDataPipeline
from app.signals.engine import SignalEngine, SignalConfig
from app.signals.models import Signal, SignalContext
from app.analysis.market_regime import MarketRegime
from app.core.metrics import EXCHANGE_FAILURES
from .execution import SignalExecutionMetadata

logger = logging.getLogger(__name__)

class SignalOrchestrator:
    """Core orchestrator for end‑to‑end signal generation.

    Workflow:
        1. Pull raw candles from the exchange.
        2. Validate/normalize via :class:`MarketDataPipeline`.
        3. Convert to ``IndicatorInput`` and calculate indicators.
        4. Build a :class:`SignalContext` (including market regime).
        5. Run the Phase 4 :class:`SignalEngine`.
        6. Attach execution metadata and return the ``Signal``.
    """

    def __init__(
        self,
        exchange: BaseExchange,
        indicator_engine: IndicatorEngine,
        signal_engine: SignalEngine | None = None,
        pipeline: MarketDataPipeline | None = None,
    ) -> None:
        self.exchange = exchange
        self.indicator_engine = indicator_engine
        self.signal_engine = signal_engine or SignalEngine()
        self.pipeline = pipeline or MarketDataPipeline()
        self._config = SignalConfig()  # Phase‑4 config (defaults)

    def generate(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        execution_source: str = "orchestrator",
    ) -> Signal:
        """Generate a ``Signal`` for a single symbol/timeframe pair.

        Parameters
        ----------
        symbol: str – market symbol (e.g. ``"BTC/USDT"``).
        timeframe: str – e.g. ``"15m"``.
        start_time, end_time: optional bounds for candle retrieval.
        execution_source: identifier for the caller (useful for logging).
        """
        logger.debug(
            "Orchestrator start",
            extra={"symbol": symbol, "timeframe": timeframe, "source": execution_source},
        )

        # 1️⃣ Pull raw candles
        try:
            raw_candles = self.exchange.get_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_time,
                end_time=end_time,
            )
        except Exception as e:
            EXCHANGE_FAILURES.labels(exchange=self.exchange.name, operation="get_ohlcv").inc()
            raise RuntimeError(f"Exchange data fetch failed for {symbol}/{timeframe}: {e}") from e

        if not raw_candles:
            EXCHANGE_FAILURES.labels(exchange=self.exchange.name, operation="get_ohlcv").inc()
            raise RuntimeError(f"No market data for {symbol}/{timeframe}")

        # 2️⃣ Validate / normalize via pipeline (may raise)
        validated = self.pipeline.validate_and_normalize(raw_candles)

        # 3️⃣ Build IndicatorInput – the engine provides a helper
        indicator_input = self.indicator_engine.indicator_input_from_candles(validated)

        # 4️⃣ Calculate all indicators
        indicators = self.indicator_engine.calculate_all(indicator_input)

        # 5️⃣ Determine market regime (simple heuristic based on ATR expansion)
        regime = MarketRegime.HIGH_VOLATILITY if indicators.get("atr_expansion", 0) > 1 else MarketRegime.NORMAL

        # 6️⃣ Build SignalContext
        ctx = SignalContext(
            symbol=symbol,
            exchange=self.exchange.name,
            timeframe=timeframe,
            timestamp=datetime.utcnow(),
            market_regime=regime,
        )

        # 7️⃣ Run Phase‑4 SignalEngine
        signal = self.signal_engine.generate(indicators, ctx)

        # 8️⃣ Attach execution metadata (non‑intrusive – stored as an extra attribute)
        execution_meta = SignalExecutionMetadata(source=execution_source)
        # Re‑create signal with metadata (preserves immutability)
        signal = signal.__class__(
            direction=signal.direction,
            strength=signal.strength,
            confidence=signal.confidence,
            score=signal.score,
            context=signal.context,
            evidences=signal.evidences,
            metadata=execution_meta,
        )

        logger.info(
            "Signal generated",
            extra={
                "symbol": symbol,
                "timeframe": timeframe,
                "direction": signal.direction.name,
                "strength": signal.strength.name,
                "confidence": signal.confidence.name,
                "execution_id": execution_meta.execution_id,
            },
        )
        return signal
