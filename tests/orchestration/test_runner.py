import pytest
from unittest.mock import MagicMock, create_autospec
from datetime import datetime, timezone

from app.orchestration.universe import SymbolUniverse
from app.orchestration.orchestrator import SignalOrchestrator
from app.orchestration.runner import MultiTimeframeRunner
from app.signals.models import Signal, SignalDirection, SignalStrength, SignalConfidence, SignalContext

@pytest.fixture
def dummy_universe():
    # Simple universe with two symbols and two timeframes
    config = MagicMock()
    config.symbols = ("BTC/USDT", "ETH/USDT")
    config.timeframes = ("15m", "1h")
    return SymbolUniverse.from_config(config)

@pytest.fixture
def mock_orchestrator_success():
    orchestrator = MagicMock(spec=SignalOrchestrator)
    # Return a simple Signal object for any call
    def gen(symbol, timeframe, **kwargs):
        ctx = SignalContext(
            symbol=symbol,
            exchange="mock",
            timeframe=timeframe,
            timestamp=datetime.now(timezone.utc),
            market_regime=None,
        )
        return Signal(
            direction=SignalDirection.BUY,
            strength=SignalStrength.WEAK,
            confidence=SignalConfidence.HIGH,
            score=Decimal('0.5'),
            context=ctx,
            evidences=(),
        )
    orchestrator.generate.side_effect = gen
    return orchestrator

@pytest.fixture
def mock_orchestrator_partial_failure():
    orchestrator = MagicMock(spec=SignalOrchestrator)
    def gen(symbol, timeframe, **kwargs):
        if symbol == "ETH/USDT" and timeframe == "1h":
            raise RuntimeError("simulated failure")
        ctx = SignalContext(
            symbol=symbol,
            exchange="mock",
            timeframe=timeframe,
            timestamp=datetime.now(timezone.utc),
            market_regime=None,
        )
        return Signal(
            direction=SignalDirection.SELL,
            strength=SignalStrength.WEAK,
            confidence=SignalConfidence.HIGH,
            score=Decimal('0.3'),
            context=ctx,
            evidences=(),
        )
    orchestrator.generate.side_effect = gen
    return orchestrator

def test_runner_all_success(dummy_universe, mock_orchestrator_success):
    runner = MultiTimeframeRunner(orchestrator=mock_orchestrator_success, universe=dummy_universe)
    signals = runner.run_all()
    # Universe has 4 combos, should get 4 signals
    assert len(signals) == 4
    # Verify orchestrator called for each combo
    expected_calls = [("BTC/USDT", "15m"), ("BTC/USDT", "1h"), ("ETH/USDT", "15m"), ("ETH/USDT", "1h")]
    actual_calls = [(c[1]['symbol'], c[1]['timeframe']) for c in mock_orchestrator_success.generate.call_args_list]
    assert set(actual_calls) == set(expected_calls)

def test_runner_partial_failure(dummy_universe, mock_orchestrator_partial_failure):
    runner = MultiTimeframeRunner(orchestrator=mock_orchestrator_partial_failure, universe=dummy_universe)
    signals = runner.run_all()
    # One combo fails, so we expect 3 signals returned
    assert len(signals) == 3
    # Ensure the failing combo is not in the results
    for sig in signals:
        assert not (sig.context.symbol == "ETH/USDT" and sig.context.timeframe == "1h")
