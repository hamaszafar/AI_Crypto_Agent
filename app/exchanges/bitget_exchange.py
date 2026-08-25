from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import requests

from app.exchanges.base import BaseExchange
from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe


class BitgetExchange(BaseExchange):
    """
    Bitget market-data exchange implementation.

    Uses Bitget public REST APIs only.
    No API key is required for public market data.
    """

    BASE_URL = "https://api.bitget.com"

    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session if session is not None else requests.Session()

    @property
    def name(self) -> str:
        return "bitget"

    # ------------------------------------------------------------------
    # Symbol conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _to_bitget_symbol(symbol: Symbol) -> str:
        """
        Convert internal symbol format.

        BTC/USDT -> BTCUSDT
        """

        return symbol.value.replace("/", "")

    # ------------------------------------------------------------------
    # Timeframe conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _to_bitget_timeframe(timeframe: Timeframe) -> str:
        """
        Convert internal timeframe to Bitget timeframe.
        """

        mapping = {
            Timeframe.FIFTEEN_MINUTES: "15min",
            Timeframe.ONE_HOUR: "1h",
            Timeframe.FOUR_HOURS: "4h",
            Timeframe.ONE_DAY: "1day",
        }

        return mapping[timeframe]

    # ------------------------------------------------------------------
    # Timestamp conversion
    # ------------------------------------------------------------------

    @staticmethod
    def _timestamp_to_datetime(timestamp_ms: str | int) -> datetime:
        """
        Convert Unix milliseconds to UTC datetime.
        """

        return datetime.fromtimestamp(
            int(timestamp_ms) / 1000,
            tz=timezone.utc,
        )

    # ------------------------------------------------------------------
    # Candle parser
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_bitget_candle(
        row: list[str],
        symbol: Symbol,
        timeframe: Timeframe,
    ) -> Candle:
        """
        Parse a Bitget candle row.

        Expected format:

        [
            timestamp,
            open,
            high,
            low,
            close,
            base_volume,
            quote_volume,
        ]
        """

        return Candle(
            exchange="bitget",
            symbol=symbol,
            timeframe=timeframe,
            timestamp=BitgetExchange._timestamp_to_datetime(row[0]),
            open=Decimal(row[1]),
            high=Decimal(row[2]),
            low=Decimal(row[3]),
            close=Decimal(row[4]),
            volume=Decimal(row[5]),
        )

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
            raise ValueError("Bitget limit cannot exceed 1000")

        params: dict[str, Any] = {
            "symbol": self._to_bitget_symbol(symbol),
            "productType": "USDT-FUTURES",
            "granularity": self._to_bitget_timeframe(timeframe),
            "limit": limit,
        }

        if start_time is not None:
            params["startTime"] = int(
                start_time.timestamp() * 1000
            )

        if end_time is not None:
            params["endTime"] = int(
                end_time.timestamp() * 1000
            )

        response = self._session.get(
            f"{self.BASE_URL}/api/v2/mix/market/candles",
            params=params,
            timeout=10,
        )

        response.raise_for_status()

        payload = response.json()

        if payload.get("code") != "00000":
            raise RuntimeError(
                f"Bitget API error: {payload}"
            )

        rows = payload.get("data", [])

        candles = [
            self._parse_bitget_candle(
                row=row,
                symbol=symbol,
                timeframe=timeframe,
            )
            for row in rows
        ]

        # Bitget may return newest candles first.
        candles.sort(
            key=lambda candle: candle.timestamp
        )

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
    # Symbols
    # ------------------------------------------------------------------

    def get_symbols(self) -> list[Symbol]:
        """
        Return symbols supported by the application.

        We intentionally return the application's Symbol enum
        rather than every Bitget contract.
        """

        return list(Symbol)

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        """
        Check whether Bitget public API is reachable.

        Returns:

            True  -> API reachable and successful
            False -> connection/API failure
        """

        try:
            response = self._session.get(
                f"{self.BASE_URL}/api/v2/public/time",
                timeout=10,
            )

            response.raise_for_status()

            payload = response.json()

            return payload.get("code") == "00000"

        except Exception:
            return False