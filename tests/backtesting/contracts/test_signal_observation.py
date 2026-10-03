import pytest
from datetime import datetime, timezone
from decimal import Decimal
import uuid

from app.backtesting.contracts.signal_observation import SignalObservation
from app.backtesting.contracts.exceptions import InvalidSignalObservationError
from app.signals.models import SignalDirection, SignalStrength, SignalConfidence

def test_valid_signal_observation():
    now = datetime.now(timezone.utc)
    obs = SignalObservation(
        signal_id="sig_123",
        timestamp=now,
        exchange="BINANCE",
        symbol="BTC/USDT",
        timeframe="1h",
        direction=SignalDirection.BUY,
        strength=SignalStrength.STRONG,
        confidence=SignalConfidence.HIGH,
        score=Decimal("0.85"),
        entry_price=Decimal("50000"),
        stop_loss=Decimal("49000"),
        take_profit=Decimal("52000"),
        metadata={"model": "v1"}
    )
    
    assert obs.signal_id == "sig_123"
    assert obs.direction == SignalDirection.BUY
    
    obs_dict = obs.to_dict()
    assert obs_dict["signal_id"] == "sig_123"
    assert obs_dict["score"] == "0.85"
    
    restored = SignalObservation.from_dict(obs_dict)
    assert restored == obs

def test_invalid_signal_observation():
    now = datetime.now(timezone.utc)
    with pytest.raises(InvalidSignalObservationError):
        SignalObservation(
            signal_id="",
            timestamp=now,
            exchange="BINANCE",
            symbol="BTC/USDT",
            timeframe="1h",
            direction=SignalDirection.BUY,
            strength=SignalStrength.STRONG,
            confidence=SignalConfidence.HIGH,
            score=Decimal("0.85"),
            entry_price=Decimal("50000")
        )

    with pytest.raises(InvalidSignalObservationError):
        SignalObservation(
            signal_id="sig_123",
            timestamp=now,
            exchange="BINANCE",
            symbol="BTC/USDT",
            timeframe="1h",
            direction=SignalDirection.BUY,
            strength=SignalStrength.STRONG,
            confidence=SignalConfidence.HIGH,
            score=Decimal("0.85"),
            entry_price=Decimal("-50000")
        )
