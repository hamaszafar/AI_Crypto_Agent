"""Multi‑timeframe runner that drives the SignalOrchestrator for every
(symbol, timeframe) pair defined in a :class:`app.orchestration.universe.SymbolUniverse`.
It isolates failures so a single bad symbol/timeframe does not stop the whole
run.
"""

from __future__ import annotations

import logging
from typing import List

from app.orchestration.universe import SymbolUniverse
from app.orchestration.orchestrator import SignalOrchestrator
from app.signals.models import Signal
from app.core.metrics import SIGNAL_GENERATION

logger = logging.getLogger(__name__)


class MultiTimeframeRunner:
    """Execute a SignalOrchestrator for all configured symbol/timeframe combos.

    Parameters
    ----------
    orchestrator: SignalOrchestrator
        The orchestrator responsible for generating a single signal.
    universe: SymbolUniverse
        Holds the deterministic list of (symbol, timeframe) pairs.
    """

    def __init__(self, orchestrator: SignalOrchestrator, universe: SymbolUniverse) -> None:
        self.orchestrator = orchestrator
        self.universe = universe

    def run_all(self) -> List[Signal]:
        """Run the orchestrator for every combination.

        Returns a list of successfully generated ``Signal`` objects.
        Errors for individual combos are logged and ignored.
        """
        signals: List[Signal] = []
        for symbol, timeframe in self.universe.combinations():
            try:
                sig = self.orchestrator.generate(symbol=symbol, timeframe=timeframe)
                SIGNAL_GENERATION.labels(symbol=symbol, timeframe=timeframe, status="success").inc()
                signals.append(sig)
            except Exception as exc:  # pragma: no cover – exercised via tests
                SIGNAL_GENERATION.labels(symbol=symbol, timeframe=timeframe, status="failure").inc()
                logger.error(
                    "Failed to generate signal",
                    extra={"symbol": symbol, "timeframe": timeframe, "error": str(exc)},
                )
        return signals
