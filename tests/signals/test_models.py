import pytest
from decimal import Decimal
from datetime import datetime

from app.signals.models import (
    SignalDirection,
    SignalStrength,
    SignalConfidence,
    ReasonCode,
    SignalEvidence,
    SignalContext,
    Signal,
)

def test_signal_creation_immutable():
    ctx = SignalContext(
        symbol="BTC/USDT",
        exchange="binance",
        timeframe="1h",
        timestamp=datetime(2023, 1, 1, 0, 0, 0),
        market_regime="TRENDING_BULLISH",
    )
    ev = SignalEvidence(reason=ReasonCode.BULLISH_EMA_ALIGNMENT, value=Decimal('0.4'))
    sig = Signal(
        direction=SignalDirection.BUY,
        strength=SignalStrength.STRONG,
        confidence=SignalConfidence.HIGH,
        score=Decimal('0.4'),
        context=ctx,
        evidences=(ev,)
    )
    assert sig.direction == SignalDirection.BUY
    assert sig.strength == SignalStrength.STRONG
    assert sig.confidence == SignalConfidence.HIGH
    assert sig.evidences[0].reason == ReasonCode.BULLISH_EMA_ALIGNMENT
    # immutability test – assigning should raise FrozenInstanceError
    with pytest.raises(AttributeError):
        sig.direction = SignalDirection.SELL

def test_reason_derivation():
    ctx = SignalContext(
        symbol="ETH/USDT",
        exchange="kraken",
        timeframe="15m",
        timestamp=datetime.utcnow(),
    )
    ev1 = SignalEvidence(reason=ReasonCode.RSI_OVERSOLD, value=Decimal('0.3'))
    ev2 = SignalEvidence(reason=ReasonCode.MACD_BULLISH, value=Decimal('0.2'))
    sig = Signal(
        direction=SignalDirection.BUY,
        strength=SignalStrength.MODERATE,
        confidence=SignalConfidence.MEDIUM,
        score=Decimal('0.5'),
        context=ctx,
        evidences=(ev1, ev2)
    )
    assert sig.reasons == (ReasonCode.RSI_OVERSOLD, ReasonCode.MACD_BULLISH)
