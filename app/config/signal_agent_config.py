import os
from dataclasses import dataclass, field
from typing import Tuple, List

from app.market_data.config import SUPPORTED_TIMEFRAMES


def _parse_csv_env(var_name: str) -> Tuple[str, ...]:
    """Parse a comma‑separated environment variable into a tuple of stripped strings.
    Returns an empty tuple if the variable is not set.
    """
    raw = os.getenv(var_name, "")
    if not raw:
        return tuple()
    return tuple(item.strip() for item in raw.split(",") if item.strip())


@dataclass(frozen=True)
class SignalAgentConfig:
    """Configuration for Phase 5 signal orchestration.

    Environment variables (comma‑separated) are used to provide values:
        SIGNAL_SYMBOLS   – e.g. "BTC/USDT,ETH/USDT"
        SIGNAL_TIMEFRAMES – e.g. "15m,1h,4h,1d"
        SIGNAL_SCHEDULE – JSON mapping timeframe → interval seconds (optional).

    Validation ensures symbols and timeframes are non‑empty and supported.
    """

    symbols: Tuple[str, ...] = field(default_factory=lambda: _parse_csv_env("SIGNAL_SYMBOLS"))
    timeframes: Tuple[str, ...] = field(default_factory=lambda: _parse_csv_env("SIGNAL_TIMEFRAMES"))
    schedule: dict[str, int] = field(default_factory=dict)

    def __post_init__(self):  # type: ignore[override]
        # Validate symbols
        if not self.symbols:
            raise ValueError("SignalAgentConfig: at least one symbol must be configured via SIGNAL_SYMBOLS")
        for sym in self.symbols:
            if "/" not in sym or not all(part.isalnum() for part in sym.split("/")):
                raise ValueError(f"Invalid symbol format '{sym}'. Expected 'BASE/QUOTE'.")

        # Validate timeframes
        if not self.timeframes:
            raise ValueError("SignalAgentConfig: at least one timeframe must be configured via SIGNAL_TIMEFRAMES")
        for tf in self.timeframes:
            if tf not in SUPPORTED_TIMEFRAMES:
                raise ValueError(f"Unsupported timeframe '{tf}'. Supported: {sorted(SUPPORTED_TIMEFRAMES)}")

        # Optional schedule parsing – env var expects JSON like '{"15m":900,"1h":3600}'
        if not self.schedule:
            raw = os.getenv("SIGNAL_SCHEDULE", "")
            if raw:
                try:
                    import json
                    parsed = json.loads(raw)
                    if not isinstance(parsed, dict):
                        raise ValueError
                    # ensure keys are supported timeframes and values are positive ints
                    schedule_dict: dict[str, int] = {}
                    for k, v in parsed.items():
                        if k not in self.timeframes:
                            raise ValueError(f"Schedule timeframe '{k}' not in enabled timeframes")
                        if not isinstance(v, int) or v <= 0:
                            raise ValueError(f"Schedule interval for '{k}' must be a positive integer")
                        schedule_dict[k] = v
                    object.__setattr__(self, "schedule", schedule_dict)
                except Exception as exc:
                    raise ValueError("SIGNAL_SCHEDULE must be a valid JSON mapping timeframe->positive int") from exc
