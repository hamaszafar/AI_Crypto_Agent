import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.backtesting.contracts.signal_outcome import SignalOutcome
from app.backtesting.contracts.enums import SignalOutcomeStatus
from app.backtesting.contracts.exceptions import InvalidSignalOutcomeError
from app.signals.models import SignalDirection

def test_valid_signal_outcome():
    now = datetime.now(timezone.utc)
    res_time = now + timedelta(hours=2)
    outcome = SignalOutcome(
        signal_id="sig_123",
        signal_timestamp=now,
        status=SignalOutcomeStatus.WIN,
        entry_price=Decimal("50000"),
        direction=SignalDirection.BUY,
        resolution_timestamp=res_time,
        exit_price=Decimal("52000"),
        realized_pnl=Decimal("2000"),
        realized_return=Decimal("0.04")
    )
    
    assert outcome.signal_id == "sig_123"
    assert outcome.status == SignalOutcomeStatus.WIN
    
    outcome_dict = outcome.to_dict()
    assert outcome_dict["signal_id"] == "sig_123"
    
    restored = SignalOutcome.from_dict(outcome_dict)
    # Exclude dynamic id if empty originally, but we didn't specify so it was generated
    assert restored.outcome_id == outcome.outcome_id
    assert restored.status == outcome.status

def test_invalid_resolution_timestamp():
    now = datetime.now(timezone.utc)
    res_time = now - timedelta(hours=2)
    
    with pytest.raises(InvalidSignalOutcomeError):
        SignalOutcome(
            signal_id="sig_123",
            signal_timestamp=now,
            status=SignalOutcomeStatus.WIN,
            entry_price=Decimal("50000"),
            direction=SignalDirection.BUY,
            resolution_timestamp=res_time
        )
