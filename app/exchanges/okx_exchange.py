from datetime import datetime, timezone
from decimal import Decimal

import requests

from app.exchanges.base import BaseExchange
from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe


class OKXExchange(BaseExchange):
    """
    OKX public market-data implementation.

    Uses the OKX public REST API.
    No API key is required for the market-data endpoints.
    """

    BASE_URL = "https://www.okx.com"

    SYMBOL_MAP = {
        Symbol.BTC_USDT: "BTC-USDT",
        Symbol.ETH_USDT: "ETH-USDT",
        Symbol.XRP_USDT: "XRP-USDT",
        Symbol.LTC_USDT: "LTC-USDT",
        Symbol.SOL_USDT: "SOL-USDT",
    }

    TIMEFRAME_MAP = {
        Timeframe.FIFTEEN_MINUTES: "15m",
        Timeframe.ONE_HOUR: "1H",
        Timeframe.FOUR_HOURS: "4H",
        Timeframe.ONE_DAY: "1D",
    }

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout
        self.session = requests.Session()

    @property
    def name(self) -> str:
        return "okx"

    def get_symbols(self) -> list[Symbol]:
        return list(Symbol)

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

        if limit > 100:
            raise ValueError("OKX limit cannot exceed 100")

        params = {
            "instId": self._convert_symbol(symbol),
            "bar": self._convert_timeframe(timeframe),
            "limit": str(limit),
        }

        if start_time is not None:
            params["after"] = str(
                self._to_timestamp_ms(start_time)
            )

        if end_time is not None:
            params["before"] = str(
                self._to_timestamp_ms(end_time)
            )

        response = self.session.get(
            f"{self.BASE_URL}/api/v5/market/candles",
            params=params,
            timeout=self.timeout,
        )

        response.raise_for_status()

        payload = response.json()

        if payload.get("code") != "0":
            raise RuntimeError(
                f"OKX API error: {payload.get('msg')}"
            )

        rows = payload.get("data", [])

        candles = [
            self._parse_okx_candle(
                row=row,
                symbol=symbol,
                timeframe=timeframe,
            )
            for row in rows
        ]

        candles.sort(key=lambda candle: candle.timestamp)

        return candles

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

    def health_check(self) -> bool:
        try:
            response = self.session.get(
                f"{self.BASE_URL}/api/v5/public/time",
                timeout=self.timeout,
            )

            response.raise_for_status()

            payload = response.json()

            return payload.get("code") == "0"

        except Exception:
            return False

    @classmethod
    def _convert_symbol(cls, symbol: Symbol) -> str:
        try:
            return cls.SYMBOL_MAP[symbol]
        except KeyError:
            raise ValueError(
                f"Unsupported OKX symbol: {symbol}"
            )

    @classmethod
    def _convert_timeframe(cls, timeframe: Timeframe) -> str:
        try:
            return cls.TIMEFRAME_MAP[timeframe]
        except KeyError:
            raise ValueError(
                f"Unsupported OKX timeframe: {timeframe}"
            )

    @staticmethod
    def _to_timestamp_ms(value: datetime) -> int:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)

        return int(value.timestamp() * 1000)

    @staticmethod
    def _parse_okx_candle(
        row: list,
        symbol: Symbol,
        timeframe: Timeframe,
    ) -> Candle:
        """
        OKX candle format:

        [
            timestamp,
            open,
            high,
            low,
            close,
            volume,
            volume_currency,
            volume_currency_quote,
            confirm
        ]
        """

        timestamp_ms = int(row[0])

        return Candle(
            exchange="okx",
            symbol=symbol,
            timeframe=timeframe,
            timestamp=datetime.fromtimestamp(
                timestamp_ms / 1000,
                tz=timezone.utc,
            ),
            open=Decimal(row[1]),
            high=Decimal(row[2]),
            low=Decimal(row[3]),
            close=Decimal(row[4]),
            volume=Decimal(row[5]),
        )