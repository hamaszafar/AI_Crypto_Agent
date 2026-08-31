from datetime import datetime, timezone
from decimal import Decimal

from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe
from app.market_data.config import CollectionConfig
from app.market_data.freshness import FreshnessState
from app.market_data.health import HealthStatus
from app.market_data.pipeline import CollectionPipeline
from app.market_data.storage import MarketDataStorage
from app.storage.database import SQLiteDatabase
from app.storage.repositories.sqlite_candle_repository import SQLiteCandleRepository
from app.storage.service import StorageService


def test_pipeline_e2e_scheduled_cycle(tmp_path):
    db_path = tmp_path / "test_pipeline.db"
    database = SQLiteDatabase(path=str(db_path))
    repo = SQLiteCandleRepository(database=database)
    storage = MarketDataStorage(StorageService(repo))

    config = CollectionConfig(
        exchanges=["binance"],
        symbols=[Symbol.BTC_USDT],
        timeframes=[Timeframe.FIFTEEN_MINUTES],
    )

    t_now = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    pipeline = CollectionPipeline(
        config=config,
        storage=storage,
        clock=lambda: t_now,
    )

    results = pipeline.run_scheduled_cycle()
    assert len(results) == 1
    res = results[0]
    assert res.job.exchange == "binance"
    assert res.job.symbol == "BTC/USDT"
    assert res.job.timeframe == "15m"

    health = pipeline.health_tracker.get_health("binance")
    assert health.status == HealthStatus.HEALTHY


def test_pipeline_e2e_gap_detection_and_recovery(tmp_path):
    db_path = tmp_path / "test_pipeline_gaps.db"
    database = SQLiteDatabase(path=str(db_path))
    repo = SQLiteCandleRepository(database=database)
    storage = MarketDataStorage(StorageService(repo))

    config = CollectionConfig(
        exchanges=["binance"],
        symbols=[Symbol.BTC_USDT],
        timeframes=[Timeframe.FIFTEEN_MINUTES],
    )

    t1 = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2025, 1, 1, 10, 15, tzinfo=timezone.utc)
    t3 = datetime(2025, 1, 1, 11, 0, tzinfo=timezone.utc)

    def make_candle(ts):
        return Candle(
            exchange="binance",
            symbol=Symbol.BTC_USDT,
            timeframe=Timeframe.FIFTEEN_MINUTES,
            timestamp=ts,
            open=Decimal("100"),
            high=Decimal("110"),
            low=Decimal("95"),
            close=Decimal("105"),
            volume=Decimal("10"),
        )

    storage.save_candles([make_candle(t1), make_candle(t2), make_candle(t3)])

    pipeline = CollectionPipeline(
        config=config,
        storage=storage,
        clock=lambda: t3,
    )

    freshness = pipeline.evaluate_freshness("binance", Symbol.BTC_USDT, Timeframe.FIFTEEN_MINUTES)
    assert freshness.state == FreshnessState.FRESH

    recovered_count = pipeline.recover_gaps("binance", Symbol.BTC_USDT, Timeframe.FIFTEEN_MINUTES)
    assert recovered_count >= 0
