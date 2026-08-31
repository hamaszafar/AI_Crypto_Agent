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
)
from app.signals.conditions import ConditionEngine
from app.signals.scorer import Scorer
from app.signals.confidence import ConfidenceEngine
from app.signals.engine import SignalEngine, SignalConfig
from app.signals.confluence import aggregate_signals, ConfluenceStrength
from app.analysis.market_regime import MarketRegime

# ---------------------------------------------------------------------------
# ConditionEngine tests
# ---------------------------------------------------------------------------

def test_condition_engine_basic():
    ce = ConditionEngine()
    indicators = {
        "ema_fast_vs_slow": Decimal('1'),
        "macd": Decimal('-0.5'),
        "rsi": Decimal('75'),
        "volume_vs_avg": Decimal('1'),
        "atr_expansion": Decimal('1'),
        "exchange_consensus": Decimal('1'),
    }
    evidences = ce.evaluate(indicators)
    reasons = {e.reason for e in evidences}
    expected = {
        ReasonCode.BULLISH_EMA_ALIGNMENT,
        ReasonCode.MACD_BEARISH,
        ReasonCode.RSI_OVERBOUGHT,
        ReasonCode.VOLUME_ABOVE_AVG,
        ReasonCode.HIGH_VOLATILITY,
        ReasonCode.CROSS_EXCHANGE_BULLISH,
    }
    assert reasons == expected

# ---------------------------------------------------------------------------
# Scorer tests
# ---------------------------------------------------------------------------

def test_scorer_with_weights():
    evidences = [
        SignalEvidence(ReasonCode.BULLISH_EMA_ALIGNMENT, Decimal('0.4')),
        SignalEvidence(ReasonCode.RSI_OVERBOUGHT, Decimal('-0.3')),
    ]
    weights = {ReasonCode.BULLISH_EMA_ALIGNMENT: Decimal('2')}
    scorer = Scorer(weights)
    total = scorer.score(evidences)
    # 0.4 * 2 + (-0.3) * 1 = 0.5
    assert total == Decimal('0.5')
    assert scorer.max_possible(evidences) == Decimal('0.4') * Decimal('2') + Decimal('0.3') * Decimal('1')

# ---------------------------------------------------------------------------
# ConfidenceEngine tests
# ---------------------------------------------------------------------------
def test_confidence_engine_tiers():
    evidences = [
        SignalEvidence(ReasonCode.BULLISH_EMA_ALIGNMENT, Decimal('0.4')),
        SignalEvidence(ReasonCode.RSI_OVERSOLD, Decimal('0.3')),
    ]
    scorer = Scorer()
    ce = ConfidenceEngine(scorer)
    # score = 0.7, max_possible = 0.7 --> ratio = 1 -> HIGH
    assert ce.confidence(evidences) == SignalConfidence.HIGH

    # Reduce one evidence magnitude
    evidences2 = [
        SignalEvidence(ReasonCode.BULLISH_EMA_ALIGNMENT, Decimal('0.2')),
        SignalEvidence(ReasonCode.RSI_OVERSOLD, Decimal('0.1')),
    ]
    # score = 0.3, max_possible = 0.3 -> HIGH still (ratio 1). Force lower ratio by mixed signs
    evidences3 = [
        SignalEvidence(ReasonCode.BULLISH_EMA_ALIGNMENT, Decimal('0.4')),
        SignalEvidence(ReasonCode.RSI_OVERBOUGHT, Decimal('-0.2')),
    ]
    # score = 0.2, max = 0.6 -> ratio = 0.333 -> UNKNOWN (below LOW)
    assert ce.confidence(evidences3) == SignalConfidence.UNKNOWN

# ---------------------------------------------------------------------------
# SignalEngine tests (including regime adjustment)
# ---------------------------------------------------------------------------
def make_context(regime=None):
    return SignalContext(
        symbol="BTC/USDT",
        exchange="binance",
        timeframe="1h",
        timestamp=datetime.utcnow(),
        market_regime=regime,
    )

def test_signal_engine_buy_direction():
    engine = SignalEngine()
    indicators = {"ema_fast_vs_slow": Decimal('1')}
    sig = engine.generate(indicators, make_context())
    assert sig.direction == SignalDirection.BUY
    assert sig.strength in (SignalStrength.WEAK, SignalStrength.MODERATE, SignalStrength.STRONG)
    assert sig.confidence == SignalConfidence.HIGH

def test_signal_engine_regime_adjustment():
    engine = SignalEngine()
    indicators = {"ema_fast_vs_slow": Decimal('1')}
    # High volatility should reduce the score (0.4 * 0.8 = 0.32) -> still BUY because threshold 0.5
    sig_low = engine.generate(indicators, make_context(MarketRegime.HIGH_VOLATILITY))
    # With low volatility the score is amplified -> still BUY and stronger
    sig_high = engine.generate(indicators, make_context(MarketRegime.LOW_VOLATILITY))
    assert sig_low.direction == SignalDirection.HOLD or sig_low.direction == SignalDirection.BUY
    assert sig_high.direction == SignalDirection.BUY

# ---------------------------------------------------------------------------
# Confluence aggregation tests
# ---------------------------------------------------------------------------
def test_confluence_majority_buy():
    ctx = make_context()
    sig_buy = SignalDirection.BUY
    # create dummy signals
    from app.signals.models import Signal
    s1 = Signal(
        direction=SignalDirection.BUY,
        strength=SignalStrength.WEAK,
        confidence=SignalConfidence.HIGH,
        score=Decimal('0.6'),
        context=ctx,
        evidences=(),
    )
    s2 = Signal(
        direction=SignalDirection.SELL,
        strength=SignalStrength.WEAK,
        confidence=SignalConfidence.HIGH,
        score=Decimal('-0.6'),
        context=ctx,
        evidences=(),
    )
    s3 = s1
    result = aggregate_signals([s1, s2, s3])
    assert result.overall_direction == SignalDirection.BUY
    assert result.strength == ConfluenceStrength.BULLISH_ALIGNMENT

def test_confluence_tie_results_in_mixed():
    ctx = make_context()
    from app.signals.models import Signal
    s_buy = Signal(
        direction=SignalDirection.BUY,
        strength=SignalStrength.WEAK,
        confidence=SignalConfidence.HIGH,
        score=Decimal('0.6'),
        context=ctx,
        evidences=(),
    )
    s_sell = Signal(
        direction=SignalDirection.SELL,
        strength=SignalStrength.WEAK,
        confidence=SignalConfidence.HIGH,
        score=Decimal('-0.6'),
        context=ctx,
        evidences=(),
    )
    result = aggregate_signals([s_buy, s_sell])
    assert result.overall_direction == SignalDirection.HOLD
    assert result.strength == ConfluenceStrength.MIXED
