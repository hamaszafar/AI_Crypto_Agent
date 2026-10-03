from decimal import Decimal, getcontext, ROUND_DOWN
from typing import Optional

from app.backtesting.contracts.config import BacktestConfig
from app.backtesting.contracts.signal_observation import SignalObservation
from app.backtesting.contracts.exceptions import InvalidPositionError

# Ensure deterministic rounding (28 precision, 8 decimal places for quantity)
getcontext().prec = 28

def resolve_position_size(
    observation: SignalObservation,
    config: BacktestConfig,
    capital: Decimal,
) -> Decimal:
    """Resolve the trade quantity based on per‑signal or global sizing.

    Hierarchy:
    1️⃣ Per‑signal sizing in ``observation.metadata["position_sizing"]`` (if present).
    2️⃣ Global sizing from ``config.position_sizing``.
    3️⃣ Raise :class:`InvalidPositionError` if neither is available.

    ``PositionSizingConfig.value`` is interpreted as a **whole percentage** (e.g. ``10`` = 10 %).
    ``initial_capital`` from ``BacktestConfig`` is the equity base.
    """
    # Per‑signal override
    per_signal_cfg = observation.metadata.get("position_sizing")
    if per_signal_cfg:
        sizing_type = per_signal_cfg.get("sizing_type")
        value = Decimal(str(per_signal_cfg.get("value")))
    else:
        sizing_type = config.position_sizing.sizing_type
        value = config.position_sizing.value

    if sizing_type is None or value is None:
        raise InvalidPositionError("No position sizing information available")

    # Compute quantity according to the sizing type
    if sizing_type.name == "PERCENT_OF_EQUITY":
        fraction = value / Decimal("100")  # whole percent to fraction
        quantity = (capital * fraction) / observation.entry_price
    elif sizing_type.name == "FIXED_AMOUNT":
        quantity = value
    elif sizing_type.name == "RISK_PERCENT":
        if observation.stop_loss is None:
            raise InvalidPositionError("RISK_PERCENT sizing requires a stop_loss on the signal")
        risk_fraction = value / Decimal("100")
        risk_amount = capital * risk_fraction
        price_diff = abs(observation.entry_price - observation.stop_loss)
        if price_diff == Decimal("0"):
            raise InvalidPositionError("Stop loss price equals entry price for risk sizing")
        quantity = risk_amount / price_diff
    else:
        raise InvalidPositionError(f"Unsupported PositionSizingType: {sizing_type}")

    # Deterministic rounding to 8 decimal places (common for crypto quantities)
    return quantity.quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)
