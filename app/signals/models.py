from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Mapping, Sequence


class SignalDirection(str, Enum):
    """Possible signal directions."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SignalStrength(str, Enum):
    """Strength of a signal based on score magnitude."""

    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    NEUTRAL = "NEUTRAL"


class SignalConfidence(str, Enum):
    """Confidence level for a generated signal."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


class ReasonCode(str, Enum):
    """Machine‑readable identifiers for why a signal was generated."""

    BULLISH_EMA_ALIGNMENT = "BULLISH_EMA_ALIGNMENT"
    BEARISH_EMA_ALIGNMENT = "BEARISH_EMA_ALIGNMENT"
    RSI_OVERBOUGHT = "RSI_OVERBOUGHT"
    RSI_OVERSOLD = "RSI_OVERSOLD"
    MACD_BULLISH = "MACD_BULLISH"
    MACD_BEARISH = "MACD_BEARISH"
    VOLUME_ABOVE_AVG = "VOLUME_ABOVE_AVG"
    VOLUME_BELOW_AVG = "VOLUME_BELOW_AVG"
    CROSS_EXCHANGE_BULLISH = "CROSS_EXCHANGE_BULLISH"
    CROSS_EXCHANGE_BEARISH = "CROSS_EXCHANGE_BEARISH"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    LOW_VOLATILITY = "LOW_VOLATILITY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class SignalEvidence:
    """A single piece of evidence contributing to a signal.

    Attributes:
        reason: ReasonCode identifying the evidence.
        value: Numeric contribution (positive for bullish, negative for bearish).
        details: Optional human readable explanation.
    """

    reason: ReasonCode
    value: Decimal
    details: str | None = None


@dataclass(frozen=True)
class SignalContext:
    """Contextual information for a generated signal.

    Attributes:
        symbol: Trading symbol (e.g., "BTC/USDT").
        exchange: Primary exchange name.
        timeframe: Timeframe string (e.g., "1h").
        timestamp: Time of the latest candle used for the decision.
        market_regime: Optional string describing the market regime.
    """

    symbol: str
    exchange: str
    timeframe: str
    timestamp: datetime
    market_regime: str | None = None


@dataclass(frozen=True)
class Signal:
    """Final signal object returned by the engine.

    Attributes:
        direction: BUY/SELL/HOLD.
        strength: SignalStrength describing the magnitude.
        confidence: Confidence level.
        score: Overall numeric score.
        context: SignalContext.
        evidences: Tuple of SignalEvidence objects.
        reasons: Tuple of ReasonCode identifiers (derived from evidences).
    """

    direction: SignalDirection
    strength: SignalStrength
    confidence: SignalConfidence
    score: Decimal
    context: SignalContext
    evidences: tuple[SignalEvidence, ...]
    reasons: tuple[ReasonCode, ...] = field(default_factory=tuple)

    def __post_init__(self):
        # Ensure reasons match evidences for easy consumption.
        object.__setattr__(self, "reasons", tuple(e.reason for e in self.evidences))
