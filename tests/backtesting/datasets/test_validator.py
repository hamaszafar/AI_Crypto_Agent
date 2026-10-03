import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.market_data.models import MarketCandle
from app.backtesting.datasets.models import HistoricalDataset
from app.backtesting.datasets.metadata import DatasetMetadata
from app.backtesting.datasets.validator import (
    HistoricalDatasetValidator,
    DatasetValidationResult,
    ValidationIssueType,
    ValidationSeverity,
)


def make_candle(
    ts: datetime,
    exchange: str = "binance",
    symbol: str = "BTC/USDT",
    timeframe: str = "1h",
    open_price: Decimal = Decimal("30000"),
    high_price: Decimal = Decimal("31000"),
    low_price: Decimal = Decimal("29500"),
    close_price: Decimal = Decimal("30500"),
    volume: Decimal = Decimal("123.45"),
) -> MarketCandle:
    return MarketCandle(
        exchange=exchange,
        symbol=symbol,
        timeframe=timeframe,
        timestamp=ts,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
    )


@pytest.fixture
def validator():
    return HistoricalDatasetValidator()


# 1. Valid dataset validation
def test_validator_valid_dataset(validator):
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = tuple(make_candle(start + timedelta(hours=i)) for i in range(3))
    metadata = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=candles[0].timestamp,
        end_timestamp=candles[-1].timestamp,
        candle_count=len(candles),
    )
    dataset = HistoricalDataset(candles=candles, metadata=metadata)
    result = validator.validate(dataset)

    assert result.is_valid is True
    assert result.status == "VALID"
    assert len(result.errors) == 0
    assert len(result.warnings) == 0
    assert result.candle_count == 3
    assert result.dataset_id == dataset.dataset_id


# 2. Duplicate candles detection
def test_validator_duplicate_candles(validator):
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    c1 = make_candle(start)
    c2 = make_candle(start)  # Duplicate timestamp
    c3 = make_candle(start + timedelta(hours=1))

    result = validator.validate_raw(candles=[c1, c2, c3])
    assert result.is_valid is False
    assert result.status == "INVALID"
    assert any(i.issue_type == ValidationIssueType.DUPLICATE_TIMESTAMP for i in result.errors)


# 3. Out-of-order candles detection
def test_validator_out_of_order_candles(validator):
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    c1 = make_candle(start)
    c2 = make_candle(start - timedelta(hours=1))  # Out of order

    result = validator.validate_raw(candles=[c1, c2])
    assert result.is_valid is False
    assert result.status == "INVALID"
    assert any(i.issue_type == ValidationIssueType.OUT_OF_ORDER for i in result.errors)


# 4. Invalid OHLC prices detection
def test_validator_invalid_ohlc(validator):
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    # High < Low is invalid
    c1 = make_candle(start, high_price=Decimal("100"), low_price=Decimal("200"))
    result = validator.validate_raw(candles=[c1])
    assert result.is_valid is False
    assert any(i.issue_type == ValidationIssueType.OHLC_INVALID for i in result.errors)


# 5. Invalid volume detection
def test_validator_invalid_volume(validator):
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    # MarketCandle enforces non-negative volume, but if raw candle has negative volume:
    c1 = make_candle(start)
    # Mutate volume attribute for testing validation reporting
    object.__setattr__(c1, "volume", Decimal("-10"))

    result = validator.validate_raw(candles=[c1])
    assert result.is_valid is False
    assert any(i.issue_type == ValidationIssueType.VOLUME_INVALID for i in result.errors)


# 6. Mixed symbols detection
def test_validator_mixed_symbols(validator):
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    c1 = make_candle(start, symbol="BTC/USDT")
    c2 = make_candle(start + timedelta(hours=1), symbol="ETH/USDT")

    result = validator.validate_raw(candles=[c1, c2])
    assert result.is_valid is False
    assert any(i.issue_type == ValidationIssueType.MIXED_SYMBOLS for i in result.errors)


# 7. Mixed timeframes detection
def test_validator_mixed_timeframes(validator):
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    c1 = make_candle(start, timeframe="1h")
    c2 = make_candle(start + timedelta(hours=1), timeframe="4h")

    result = validator.validate_raw(candles=[c1, c2])
    assert result.is_valid is False
    assert any(i.issue_type == ValidationIssueType.MIXED_TIMEFRAMES for i in result.errors)


# 8. Mixed sources/exchanges detection
def test_validator_mixed_sources(validator):
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    c1 = make_candle(start, exchange="binance")
    c2 = make_candle(start + timedelta(hours=1), exchange="bybit")

    result = validator.validate_raw(candles=[c1, c2])
    assert result.is_valid is False
    assert any(i.issue_type == ValidationIssueType.MIXED_EXCHANGES for i in result.errors)


# 9. Gap detection
def test_validator_gaps(validator):
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    c1 = make_candle(start, timeframe="1h")
    c2 = make_candle(start + timedelta(hours=5), timeframe="1h")  # 4 missing hours gap

    result = validator.validate_raw(candles=[c1, c2])
    # Gaps cause a WARNING, so is_valid remains True (no fatal error), status is WARNING
    assert result.is_valid is True
    assert result.status == "WARNING"
    assert len(result.gaps) == 1
    assert result.gaps[0]["missing_count"] == 4
    assert any(i.issue_type == ValidationIssueType.GAP_DETECTED for i in result.warnings)


# 10. Invalid boundary metadata mismatch
def test_validator_invalid_boundaries(validator):
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    c1 = make_candle(start)
    c2 = make_candle(start + timedelta(hours=1))

    metadata = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=start - timedelta(hours=2),  # Mismatched start
        end_timestamp=c2.timestamp,
        candle_count=2,
    )

    result = validator.validate_raw(candles=[c1, c2], metadata=metadata)
    assert result.is_valid is False
    assert any(i.issue_type == ValidationIssueType.BOUNDARY_MISMATCH for i in result.errors)


# 11. Multiple simultaneous errors
def test_validator_multiple_simultaneous_errors(validator):
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    c1 = make_candle(start, symbol="BTC/USDT")
    c2 = make_candle(start - timedelta(hours=1), symbol="ETH/USDT")  # Out-of-order & mixed symbol
    object.__setattr__(c2, "high", Decimal("100"))
    object.__setattr__(c2, "low", Decimal("200"))  # Invalid OHLC

    result = validator.validate_raw(candles=[c1, c2])
    assert result.is_valid is False
    issue_types = {i.issue_type for i in result.issues}

    assert ValidationIssueType.OUT_OF_ORDER in issue_types
    assert ValidationIssueType.MIXED_SYMBOLS in issue_types
    assert ValidationIssueType.OHLC_INVALID in issue_types
    assert len(result.errors) >= 3


# 12. Deterministic validation result
def test_validator_deterministic_output(validator):
    start = datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = tuple(make_candle(start + timedelta(hours=i)) for i in range(3))
    metadata = DatasetMetadata(
        exchange="binance",
        symbol="BTC/USDT",
        timeframe="1h",
        start_timestamp=candles[0].timestamp,
        end_timestamp=candles[-1].timestamp,
        candle_count=len(candles),
    )
    dataset = HistoricalDataset(candles=candles, metadata=metadata)

    r1 = validator.validate(dataset)
    r2 = validator.validate(dataset)

    assert r1.to_dict() == r2.to_dict()
    assert r1.status == r2.status
    assert r1.is_valid == r2.is_valid
