from datetime import datetime, timezone
import pytest

from app.market_data.config import (
    CollectionConfig,
    RateLimitSettings,
    RetrySettings,
    SUPPORTED_TIMEFRAMES,
    DEFAULT_COLLECTION_INTERVALS,
)


def test_retry_settings_default_values():
    retry = RetrySettings()
    assert retry.max_retries == 3
    assert retry.backoff_factor == 1.0
    assert retry.initial_delay == 1.0


def test_retry_settings_invalid_values():
    with pytest.raises(ValueError, match="max_retries"):
        RetrySettings(max_retries=-1)

    with pytest.raises(ValueError, match="backoff_factor"):
        RetrySettings(backoff_factor=-0.5)

    with pytest.raises(ValueError, match="initial_delay"):
        RetrySettings(initial_delay=-1.0)


def test_rate_limit_settings_default_values():
    rate_limit = RateLimitSettings()
    assert rate_limit.requests_per_minute == 600
    assert rate_limit.requests_per_second is None
    assert rate_limit.retry_after_seconds == 1.0


def test_rate_limit_settings_invalid_values():
    with pytest.raises(ValueError, match="requests_per_minute"):
        RateLimitSettings(requests_per_minute=0)

    with pytest.raises(ValueError, match="requests_per_second"):
        RateLimitSettings(requests_per_second=-5)

    with pytest.raises(ValueError, match="retry_after_seconds"):
        RateLimitSettings(retry_after_seconds=0)


def test_collection_config_valid_initialization():
    config = CollectionConfig(
        exchanges=["Binance", "BYBIT"],
        symbols=["btc/usdt", "ETH/USDT"],
        timeframes=["15m", "1H"],
        page_size=200,
        start_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
        end_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
    )

    assert config.exchanges == ("binance", "bybit")
    assert config.symbols == ("BTC/USDT", "ETH/USDT")
    assert config.timeframes == ("15m", "1h")
    assert config.page_size == 200
    assert config.start_time == datetime(2025, 1, 1, tzinfo=timezone.utc)
    assert config.end_time == datetime(2025, 1, 2, tzinfo=timezone.utc)
    assert config.collection_intervals == DEFAULT_COLLECTION_INTERVALS


def test_collection_config_rejects_empty_exchanges():
    with pytest.raises(ValueError, match="exchanges must not be empty"):
        CollectionConfig(exchanges=[], symbols=["BTC/USDT"], timeframes=["15m"])


def test_collection_config_rejects_unsupported_exchange():
    with pytest.raises(ValueError, match="Unsupported exchange"):
        CollectionConfig(exchanges=["unsupported_ex"], symbols=["BTC/USDT"], timeframes=["15m"])


def test_collection_config_rejects_invalid_exchange_name():
    with pytest.raises(ValueError, match="Invalid exchange name"):
        CollectionConfig(exchanges=["   "], symbols=["BTC/USDT"], timeframes=["15m"])


def test_collection_config_rejects_empty_symbols():
    with pytest.raises(ValueError, match="symbols must not be empty"):
        CollectionConfig(exchanges=["binance"], symbols=[], timeframes=["15m"])


def test_collection_config_rejects_unsupported_symbol_format():
    with pytest.raises(ValueError, match="Unsupported symbol format"):
        CollectionConfig(exchanges=["binance"], symbols=["BTCUSDT"], timeframes=["15m"])


def test_collection_config_rejects_invalid_symbol_name():
    with pytest.raises(ValueError, match="Invalid symbol"):
        CollectionConfig(exchanges=["binance"], symbols=[""], timeframes=["15m"])


def test_collection_config_rejects_empty_timeframes():
    with pytest.raises(ValueError, match="timeframes must not be empty"):
        CollectionConfig(exchanges=["binance"], symbols=["BTC/USDT"], timeframes=[])


def test_collection_config_rejects_unsupported_timeframe():
    with pytest.raises(ValueError, match="Unsupported timeframe"):
        CollectionConfig(exchanges=["binance"], symbols=["BTC/USDT"], timeframes=["2h"])


def test_collection_config_rejects_invalid_page_size():
    with pytest.raises(ValueError, match="page_size must be greater than zero"):
        CollectionConfig(exchanges=["binance"], symbols=["BTC/USDT"], timeframes=["15m"], page_size=0)


def test_collection_config_rejects_invalid_historical_range():
    start = datetime(2025, 1, 2, tzinfo=timezone.utc)
    end = datetime(2025, 1, 1, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="start_time must be before or equal to end_time"):
        CollectionConfig(
            exchanges=["binance"],
            symbols=["BTC/USDT"],
            timeframes=["15m"],
            start_time=start,
            end_time=end,
        )


def test_collection_config_rejects_invalid_collection_intervals():
    with pytest.raises(ValueError, match="Unsupported timeframe in collection_intervals"):
        CollectionConfig(
            exchanges=["binance"],
            symbols=["BTC/USDT"],
            timeframes=["15m"],
            collection_intervals={"2h": 7200},
        )

    with pytest.raises(ValueError, match="must be greater than zero"):
        CollectionConfig(
            exchanges=["binance"],
            symbols=["BTC/USDT"],
            timeframes=["15m"],
            collection_intervals={"15m": 0},
        )


def test_collection_config_to_jobs():
    config = CollectionConfig(
        exchanges=["binance", "bybit"],
        symbols=["BTC/USDT", "ETH/USDT"],
        timeframes=["15m", "1h"],
        page_size=150,
    )
    jobs = config.to_jobs()

    assert len(jobs) == 8
    job_keys = [j.key for j in jobs]
    assert ("binance", "BTC/USDT", "15m") in job_keys
    assert ("binance", "BTC/USDT", "1h") in job_keys
    assert ("binance", "ETH/USDT", "15m") in job_keys
    assert ("binance", "ETH/USDT", "1h") in job_keys
    assert ("bybit", "BTC/USDT", "15m") in job_keys
    assert ("bybit", "BTC/USDT", "1h") in job_keys
    assert ("bybit", "ETH/USDT", "15m") in job_keys
    assert ("bybit", "ETH/USDT", "1h") in job_keys
    assert all(j.page_size == 150 for j in jobs)
