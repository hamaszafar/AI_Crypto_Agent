from dataclasses import dataclass
from datetime import datetime

from app.indicators.input import IndicatorInput
from app.indicators.pipeline import IndicatorInputPipeline


@dataclass(frozen=True)
class MultiTimeframeInput:
    """
    Indicator input grouped across multiple timeframes.

    Each timeframe contains its own IndicatorInput. Missing
    timeframes are represented by None.
    """

    exchange: str
    symbol: str

    timeframe_15m: IndicatorInput | None = None
    timeframe_1h: IndicatorInput | None = None
    timeframe_4h: IndicatorInput | None = None
    timeframe_1d: IndicatorInput | None = None

    @property
    def available_timeframes(self) -> tuple[str, ...]:
        """Return the timeframes that contain data."""

        available: list[str] = []

        if self.timeframe_15m is not None:
            available.append("15m")

        if self.timeframe_1h is not None:
            available.append("1h")

        if self.timeframe_4h is not None:
            available.append("4h")

        if self.timeframe_1d is not None:
            available.append("1d")

        return tuple(available)

    @property
    def is_complete(self) -> bool:
        """
        Return True when all supported signal timeframes exist.
        """

        return (
            self.timeframe_15m is not None
            and self.timeframe_1h is not None
            and self.timeframe_4h is not None
            and self.timeframe_1d is not None
        )


class MultiTimeframePipeline:
    """
    Build indicator inputs for multiple market timeframes.
    """

    SUPPORTED_TIMEFRAMES = (
        "15m",
        "1h",
        "4h",
        "1d",
    )

    def __init__(
        self,
        indicator_pipeline: IndicatorInputPipeline,
    ) -> None:
        self.indicator_pipeline = indicator_pipeline

    def build(
        self,
        exchange: str,
        symbol: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
        timeframes: tuple[str, ...] | None = None,
    ) -> MultiTimeframeInput:
        """
        Build indicator input across selected timeframes.

        If timeframes is omitted, all supported timeframes are loaded.
        """

        selected = (
            self.SUPPORTED_TIMEFRAMES
            if timeframes is None
            else timeframes
        )

        self._validate_timeframes(selected)

        inputs: dict[str, IndicatorInput] = {}

        for timeframe in selected:
            inputs[timeframe] = self.indicator_pipeline.build(
                exchange=exchange,
                symbol=symbol,
                timeframe=timeframe,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
            )

        return MultiTimeframeInput(
            exchange=exchange,
            symbol=symbol,
            timeframe_15m=inputs.get("15m"),
            timeframe_1h=inputs.get("1h"),
            timeframe_4h=inputs.get("4h"),
            timeframe_1d=inputs.get("1d"),
        )

    def _validate_timeframes(
        self,
        timeframes: tuple[str, ...],
    ) -> None:
        """Validate requested timeframes."""

        unsupported = set(timeframes) - set(
            self.SUPPORTED_TIMEFRAMES
        )

        if unsupported:
            raise ValueError(
                "Unsupported timeframe(s): "
                + ", ".join(sorted(unsupported))
            )