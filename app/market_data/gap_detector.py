from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Sequence

TIMEFRAME_DELTAS: dict[str, timedelta] = {
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "1d": timedelta(days=1),
}


@dataclass(frozen=True)
class Gap:
    """
    Represents a missing candle range.
    """

    start_time: datetime
    end_time: datetime
    missing_count: int


class GapDetector:
    """
    Identifies missing candle timestamps in a sequence of market candles.
    """

    @staticmethod
    def get_step(timeframe: str) -> timedelta:
        tf = timeframe.strip().lower()
        if tf not in TIMEFRAME_DELTAS:
            raise ValueError(f"Unsupported timeframe for gap detection: {timeframe}")
        return TIMEFRAME_DELTAS[tf]

    @classmethod
    def detect_gaps(
        cls,
        candles: Iterable,
        timeframe: str,
    ) -> list[Gap]:
        c_list = sorted(list(candles), key=lambda c: c.timestamp)
        if len(c_list) < 2:
            return []

        step = cls.get_step(timeframe)
        gaps: list[Gap] = []

        for i in range(len(c_list) - 1):
            curr_ts = c_list[i].timestamp
            next_ts = c_list[i + 1].timestamp

            expected_next = curr_ts + step
            if next_ts > expected_next:
                gap_start = expected_next
                gap_end = next_ts - step
                missing_count = int((next_ts - curr_ts) / step) - 1
                gaps.append(
                    Gap(
                        start_time=gap_start,
                        end_time=gap_end,
                        missing_count=missing_count,
                    )
                )

        return gaps
