"""Agent runtime bootstrap – wires all Phase 5 components together and
starts the scheduler. It is deliberately lightweight for the test environment
and can be used as a script entry point.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.config.signal_agent_config import SignalAgentConfig
from app.orchestration.universe import SymbolUniverse
from app.orchestration.orchestrator import SignalOrchestrator
from app.orchestration.runner import MultiTimeframeRunner
from app.scheduler.scheduler import SignalScheduler
from app.signals.persistence import SignalRepository

# Minimal placeholder exchange – in production you would use a concrete
# implementation from ``app.exchanges``.
class DummyExchange:
    name = "dummy"
    def get_ohlcv(self, symbol, timeframe, start_time=None, end_time=None):
        # Return a list of dummy Candle objects compatible with the pipeline.
        from app.exchanges.models import Candle
        from datetime import datetime, timezone
        # generate 10 dummy candles
        return [Candle(timestamp=datetime.now(timezone.utc), open=1, high=2, low=0.5, close=1.5, volume=100) for _ in range(10)]
    def health_check(self) -> bool:
        return True

class AgentRuntime:
    """Bootstrap class for the trading‑signal agent.

    Usage example::

        runtime = AgentRuntime()
        runtime.start()
        # … let it run …
        runtime.stop()
    """

    def __init__(self, config: Optional[SignalAgentConfig] = None) -> None:
        self.config = config or SignalAgentConfig()
        self.universe = SymbolUniverse.from_config(self.config)
        self.exchange = DummyExchange()
        # In the real system the IndicatorEngine would be built from a registry.
        from app.indicators.engine import IndicatorEngine
        # For now we instantiate it with an empty list – the orchestrator will
        # raise if no indicators are present, but tests mock the engine.
        self.indicator_engine = IndicatorEngine([])
        self.orchestrator = SignalOrchestrator(
            exchange=self.exchange,
            indicator_engine=self.indicator_engine,
        )
        self.runner = MultiTimeframeRunner(self.orchestrator, self.universe)
        self.scheduler = SignalScheduler(self.config, self.runner)
        self.repository = SignalRepository()
        self._logger = logging.getLogger(__name__)

    def start(self) -> None:
        self._logger.info("Starting AgentRuntime")
        self.scheduler.start()

    def stop(self) -> None:
        self._logger.info("Stopping AgentRuntime")
        self.scheduler.stop()
