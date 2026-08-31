"""Simple scheduler that periodically runs the MultiTimeframeRunner.

It is deliberately lightweight – it uses a background thread with ``time.sleep``
between runs. The interval is read from ``SignalAgentConfig.schedule`` (seconds).
"""

from __future__ import annotations

import threading
import logging
from typing import Callable

from app.config.signal_agent_config import SignalAgentConfig
from app.orchestration.runner import MultiTimeframeRunner

logger = logging.getLogger(__name__)


class SignalScheduler:
    """Runs ``MultiTimeframeRunner.run_all`` at a fixed interval.

    The scheduler is started via :meth:`start` and stops when :meth:`stop` is
    called. It runs in a daemon thread so the process can exit cleanly.
    """

    def __init__(self, config: SignalAgentConfig, runner: MultiTimeframeRunner) -> None:
        self._interval = config.schedule  # seconds (int)
        self._runner = runner
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def _loop(self) -> None:
        logger.info("SignalScheduler started", extra={"interval": self._interval})
        while not self._stop_event.is_set():
            try:
                signals = self._runner.run_all()
                logger.info("Scheduler iteration completed", extra={"generated": len(signals)})
            except Exception as exc:  # pragma: no cover – defensive
                logger.error("Scheduler iteration failed", extra={"error": str(exc)})
            self._stop_event.wait(self._interval)
        logger.info("SignalScheduler stopped")

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
