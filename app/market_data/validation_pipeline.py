"""Lightweight market data pipeline used by SignalOrchestrator for validation/normalization.

In the full system this would perform extensive data quality checks. For the current
tests we only need a stub that returns the input unchanged.
"""

from __future__ import annotations

class MarketDataPipeline:
    """Simple pass‑through pipeline.

    The orchestrator expects a ``validate_and_normalize`` method that accepts raw
    candle data and returns a validated collection. Here we perform no changes.
    """

    def __init__(self) -> None:
        pass

    def validate_and_normalize(self, candles):
        """Return *candles* unchanged.

        A real implementation would filter, fill gaps, and enforce schema.
        """
        return candles
