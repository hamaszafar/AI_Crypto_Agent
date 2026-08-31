from datetime import datetime, timezone
from decimal import Decimal

from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe
from app.market_data.gap_detector import Gap
from app.market_data.gap_recovery import GapRecoveryService
from app.market_data.historical_downloader import HistoricalDownloader


class FakeExchange:
    def __init__(self, returned_candles):
        self.returned_candles = returned_candles
        self.calls = []

    def get_ohlcv(self, symbol, timeframe, start_time=None, end_time=None, limit=500):
        self.calls.append({
            "symbol": symbol,
            "timeframe": timeframe,
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit,
        })
        return self.returned_candles


class FakeHistoricalMarketData:
    def __init__(self):
        self.saved = []

    def save_candles(self, candles):
        self.saved.extend(candles)


def test_gap_recovery_service():
    t_start = datetime(2025, 1, 1, 10, 30, tzinfo=timezone.utc)
    t_end = datetime(2025, 1, 1, 10, 45, tzinfo=timezone.utc)

    candle1 = Candle(
        exchange="binance",
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        timestamp=t_start,
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("95"),
        close=Decimal("105"),
        volume=Decimal("10"),
    )

    exchange = FakeExchange([candle1])
    historical = FakeHistoricalMarketData()
    downloader = HistoricalDownloader(exchange, historical, page_size=100)

    recovery = GapRecoveryService(downloader)

    gap = Gap(start_time=t_start, end_time=t_end, missing_count=1)

    recovered = recovery.recover_gaps(
        symbol=Symbol.BTC_USDT,
        timeframe=Timeframe.FIFTEEN_MINUTES,
        gaps=[gap],
    )

    assert len(recovered) == 1
    assert len(historical.saved) == 1
    assert exchange.calls[0]["start_time"] == t_start
    assert exchange.calls[0]["end_time"] == t_end
