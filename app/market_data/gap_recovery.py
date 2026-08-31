from app.market_data.gap_detector import Gap, GapDetector
from app.market_data.historical_downloader import HistoricalDownloader
from app.storage.models import StoredCandle


class GapRecoveryService:
    """
    Service responsible for filling detected data gaps using HistoricalDownloader.
    """

    def __init__(
        self,
        downloader: HistoricalDownloader,
        gap_detector: GapDetector | None = None,
    ) -> None:
        self.downloader = downloader
        self.gap_detector = gap_detector or GapDetector()

    def recover_gaps(
        self,
        symbol: str,
        timeframe: str,
        gaps: list[Gap],
    ) -> list[StoredCandle]:
        """
        Download missing ranges for the specified gaps and persist them.
        """
        recovered_candles: list[StoredCandle] = []

        for gap in gaps:
            stored = self.downloader.download(
                symbol=symbol,
                timeframe=timeframe,
                start_time=gap.start_time,
                end_time=gap.end_time,
            )
            recovered_candles.extend(stored)

        return recovered_candles
