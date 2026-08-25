from datetime import datetime, timezone
from decimal import Decimal

import requests

from app.exchanges.base import BaseExchange
from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe


class BybitExchange(BaseExchange):
    """
    Bybit public market-data exchange implementation.

    Uses Bybit V5 public API.
    No API key is required for market-data endpoints.
    """

    BASE_URL = "https://api.bybit.com"

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "bybit"

    # ------------------------------------------------------------------
    # Conversion helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _symbol_to_bybit(symbol: Symbol) -> str:
        return symbol.value.replace("/", "")

    @staticmethod
    def _timeframe_to_bybit(timeframe: Timeframe) -> str:
        mapping = {
            Timeframe.FIFTEEN_MINUTES: "15",
            Timeframe.ONE_HOUR: "60",
            Timeframe.FOUR_HOURS: "240",
            Timeframe.ONE_DAY: "D",
        }

        return mapping[timeframe]

    @staticmethod
    def _timestamp_to_milliseconds(timestamp: datetime) -> int:
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        return int(timestamp.timestamp() * 1000)

    @staticmethod
    def _milliseconds_to_datetime(value: str | int) -> datetime:
        return datetime.fromtimestamp(
            int(value) / 1000,
            tz=timezone.utc,
        )

    # ------------------------------------------------------------------
    # Candle parsing
    # ------------------------------------------------------------------

    @classmethod
    def _parse_bybit_candle(
        cls,
        data: list,
        symbol: Symbol,
        timeframe: Timeframe,
    ) -> Candle:
        """
        Bybit kline format:

        [
            startTime,
            open,
            high,
            low,
            close,
            volume,
            turnover
        ]
        """

        return Candle(
            exchange=cls.__name__.replace("Exchange", "").lower(),
            symbol=symbol,
            timeframe=timeframe,
            timestamp=cls._milliseconds_to_datetime(data[0]),
            open=Decimal(str(data[1])),
            high=Decimal(str(data[2])),
            low=Decimal(str(data[3])),
            close=Decimal(str(data[4])),
            volume=Decimal(str(data[5])),
        )

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict) -> dict:
        response = requests.get(
            f"{self.BASE_URL}{path}",
            params=params,
            timeout=self.timeout,
        )

        response.raise_for_status()

        payload = response.json()

        if payload.get("retCode") != 0:
            raise RuntimeError(
                f"Bybit API error: "
                f"{payload.get('retCode')} - "
                f"{payload.get('retMsg')}"
            )

        return payload

    # ------------------------------------------------------------------
    # Symbols
    # ------------------------------------------------------------------

    def get_symbols(self) -> list[Symbol]:
        """
        Return the symbols supported by our universal Symbol enum.

        We only expose symbols that are explicitly supported by the
        application rather than returning every Bybit market.
        """

        return list(Symbol)

    # ------------------------------------------------------------------
    # OHLCV
    # ------------------------------------------------------------------

    def get_ohlcv(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 500,
    ) -> list[Candle]:

        if limit <= 0:
            return []

        if limit > 1000:
            raise ValueError("Bybit limit cannot exceed 1000")

        params = {
            "category": "spot",
            "symbol": self._symbol_to_bybit(symbol),
            "interval": self._timeframe_to_bybit(timeframe),
            "limit": limit,
        }

        if start_time is not None:
            params["start"] = self._timestamp_to_milliseconds(start_time)

        if end_time is not None:
            params["end"] = self._timestamp_to_milliseconds(end_time)

        payload = self._get(
            "/v5/market/kline",
            params,
        )

        rows = payload.get("result", {}).get("list", [])

        candles = [
            self._parse_bybit_candle(
                row,
                symbol,
                timeframe,
            )
            for row in rows
        ]

        # Bybit normally returns newest first.
        candles.sort(key=lambda candle: candle.timestamp)

        return candles

    # ------------------------------------------------------------------
    # Latest candle
    # ------------------------------------------------------------------

    def get_latest_candle(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
    ) -> Candle | None:

        candles = self.get_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            limit=1,
        )

        return candles[-1] if candles else None

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        try:
            response = requests.get(
                f"{self.BASE_URL}/v5/market/time",
                timeout=self.timeout,
            )

            if response.status_code != 200:
                return False

            payload = response.json()

            return payload.get("retCode") == 0

        except requests.RequestException:
            return False