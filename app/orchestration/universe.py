"""SymbolUniverse – deterministic abstraction for configured symbols and timeframes.

It is built from :class:`app.config.signal_agent_config.SignalAgentConfig` and provides
convenient helpers used by the multi‑timeframe runner and scheduler.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple, List

from app.config.signal_agent_config import SignalAgentConfig
from app.market_data.config import SUPPORTED_TIMEFRAMES


@dataclass(frozen=True)
class SymbolUniverse:
    """Encapsulates the trading universe defined by configuration.

    * ``symbols`` – tuple of ``BASE/QUOTE`` strings.
    * ``timeframes`` – tuple of validated timeframe strings (must be in
      ``SUPPORTED_TIMEFRAMES``).
    """

    symbols: Tuple[str, ...]
    timeframes: Tuple[str, ...]

    @classmethod
    def from_config(cls, config: SignalAgentConfig) -> "SymbolUniverse":
        # Validation already done in SignalAgentConfig, but we double‑check the
        # timeframes against the globally supported list.
        for tf in config.timeframes:
            if tf not in SUPPORTED_TIMEFRAMES:
                raise ValueError(
                    f"Unsupported timeframe {tf!r} – allowed: {sorted(SUPPORTED_TIMEFRAMES)}"
                )
        return cls(symbols=config.symbols, timeframes=config.timeframes)

    def combinations(self) -> List[Tuple[str, str]]:
        """Return a deterministic list of ``(symbol, timeframe)`` pairs.

        Symbols are sorted alphabetically; timeframes follow the order in
        ``self.timeframes`` (which is already deterministic based on configuration).
        """
        combos: List[Tuple[str, str]] = []
        for sym in sorted(self.symbols):
            for tf in self.timeframes:
                combos.append((sym, tf))
        return combos

    def validate_symbol(self, symbol: str) -> bool:
        return symbol in self.symbols

    def validate_timeframe(self, timeframe: str) -> bool:
        return timeframe in self.timeframes
