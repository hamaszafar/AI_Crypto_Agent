from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import requests

from app.exchanges.base import BaseExchange
from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe


class OKXExchange(BaseExchange):
    """
    Production OKX public market-data exchange implementation.

    Responsibilities:
    - Fetch OKX Spot market data.
    - Convert internal symbols/timeframes to OKX format.
    - Validate API responses.
    - Validate OHLCV candle data.
    - Remove duplicate candles.
    - Return normalized Candle objects.
    """

    BASE_URL = "https://www.okx.com"

    KLINE_ENDPOINT = "/api/v5/market/candles"
    SERVER_TIME_ENDPOINT = "/api/v5/public/time"

    MAX_KLINE_LIMIT = 300

    def __init__(
        self,
        timeout: float = 10.0,
    ) -> None:
        if timeout <= 0:
            raise ValueError(
                "timeout must be greater than zero"
            )

        self.timeout = timeout

    # ================================================================
    # BASIC PROPERTIES
    # ================================================================
    @property
    def name(self) -> str:
        return "okx"

    # ================================================================
    # HTTP
    # ================================================================

    def _get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute a GET request against OKX.

        OKX uses:
            code == "0"

        for successful API responses.
        """

        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = requests.request(
                "GET",
                url,
                params=params,
                headers=None,
                timeout=self.timeout,
            )

            response.raise_for_status()

        except requests.RequestException:
            raise

        try:
            data = response.json()

        except ValueError as exc:
            raise RuntimeError(
                "OKX returned invalid JSON"
            ) from exc

        if not isinstance(data, dict):
            raise RuntimeError(
                "Invalid OKX API response"
            )

        code = data.get("code")

        if code is not None and str(code) != "0":
            message = data.get(
                "msg",
                "Unknown error",
            )

            raise RuntimeError(
                f"OKX API error {code}: {message}"
            )

        return data

    # ================================================================
    # SYMBOLS
    # ================================================================

    def get_symbols(self) -> list[Symbol]:
        """
        Return supported OKX Spot symbols.

        Only symbols represented by the internal Symbol enum
        are returned.
        """

        endpoint = "/api/v5/public/instruments"

        data = self._get(
            endpoint,
            params={
                "instType": "SPOT",
            },
        )

        raw_data = data.get("data")

        if not isinstance(raw_data, list):
            raise RuntimeError(
                "Invalid OKX instruments response"
            )

        supported_symbols = {
            self._to_okx_symbol(symbol): symbol
            for symbol in Symbol
        }

        available: list[Symbol] = []

        for item in raw_data:

            if not isinstance(item, dict):
                continue

            inst_id = item.get("instId")

            if not isinstance(inst_id, str):
                continue

            symbol = supported_symbols.get(
                inst_id.upper()
            )

            if symbol is not None:
                available.append(symbol)

        return available

    # ================================================================
    # OHLCV
    # ================================================================

    def get_ohlcv(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[Candle]:
        """
        Retrieve OKX Spot OHLCV candles.

        OKX returns candles in reverse chronological order.

        Returned candles are:
        - validated
        - deduplicated
        - sorted chronologically
        """

        if limit < 1 or limit > self.MAX_KLINE_LIMIT:
            raise ValueError(
                f"limit must be between 1 and "
                f"{self.MAX_KLINE_LIMIT}"
            )

        if (
            start_time is not None
            and end_time is not None
            and start_time > end_time
        ):
            raise ValueError(
                "start_time cannot be later than end_time"
            )

        params: dict[str, Any] = {
            "instId": self._to_okx_symbol(symbol),
            "bar": self._to_okx_timeframe(timeframe),
            "limit": limit,
        }

        if start_time is not None:
            params["after"] = self._to_timestamp_ms(
                start_time
            )

        if end_time is not None:
            params["before"] = self._to_timestamp_ms(
                end_time
            )

        data = self._get(
            self.KLINE_ENDPOINT,
            params=params,
        )

        raw_list = data.get("data")

        if raw_list is None:
            return []

        if not isinstance(raw_list, list):
            raise RuntimeError(
                "OKX candle data must be a list"
            )

        if not raw_list:
            return []

        candles: list[Candle] = []

        seen_timestamps: set[datetime] = set()

        for index, item in enumerate(raw_list):

            try:
                candle = self._parse_candle(
                    data=item,
                    symbol=symbol,
                    timeframe=timeframe,
                )

            except (
                ValueError,
                InvalidOperation,
                TypeError,
            ) as exc:

                raise RuntimeError(
                    f"Malformed OKX candle at index {index}"
                ) from exc

            if candle.timestamp in seen_timestamps:
                continue

            seen_timestamps.add(
                candle.timestamp
            )

            candles.append(candle)

        candles.sort(
            key=lambda candle: candle.timestamp
        )

        return candles

    # ================================================================
    # LATEST CANDLE
    # ================================================================

    def get_latest_candle(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
    ) -> Candle | None:
        """
        Return the latest available candle.
        """

        candles = self.get_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            limit=1,
        )

        if not candles:
            return None

        return candles[-1]

    # ================================================================
    # HEALTH CHECK
    # ================================================================

    def health_check(self) -> bool:
        """
        Check whether OKX public API is reachable.
        """

        try:
            self._get(
                self.SERVER_TIME_ENDPOINT,
            )

            return True

        except (
            requests.RequestException,
            RuntimeError,
            ValueError,
        ):
            return False

    # ================================================================
    # SYMBOL MAPPING
    # ================================================================

    @staticmethod
    def _to_okx_symbol(
        symbol: Symbol,
    ) -> str:
        """
        Convert:

            BTC/USDT

        into:

            BTC-USDT
        """

        return (
            symbol.value
            .replace("/", "-")
            .replace("_", "-")
            .upper()
        )

    # ================================================================
    # TIMEFRAME MAPPING
    # ================================================================

    @staticmethod
    def _to_okx_timeframe(
        timeframe: Timeframe,
    ) -> str:
        """
        Convert internal timeframe into OKX bar.
        """

        mapping = {
            Timeframe.FIFTEEN_MINUTES: "15m",
            Timeframe.ONE_HOUR: "1H",
            Timeframe.FOUR_HOURS: "4H",
            Timeframe.ONE_DAY: "1D",
        }

        try:
            return mapping[timeframe]

        except KeyError as exc:
            raise ValueError(
                f"Unsupported OKX timeframe: {timeframe}"
            ) from exc

    # ================================================================
    # TIMESTAMP
    # ================================================================

    @staticmethod
    def _to_timestamp_ms(
        value: datetime,
    ) -> int:
        """
        Convert datetime to Unix milliseconds.

        Naive datetimes are interpreted as UTC.
        """

        if value.tzinfo is None:
            value = value.replace(
                tzinfo=timezone.utc
            )

        return int(
            value.timestamp() * 1000
        )

    # ================================================================
    # CANDLE PARSING
    # ================================================================

    @staticmethod
    def _parse_candle(
        data: list,
        symbol: Symbol,
        timeframe: Timeframe,
    ) -> Candle:
        """
        Parse an OKX candle.

        OKX format:

        [
            ts,
            o,
            h,
            l,
            c,
            vol,
            volCcy,
            volCcyQuote,
            confirm
        ]
        """

        if not isinstance(data, list):
            raise ValueError(
                "OKX candle must be a list"
            )

        if len(data) < 6:
            raise ValueError(
                "OKX candle contains fewer than "
                "6 required fields"
            )

        # ------------------------------------------------------------
        # Timestamp
        # ------------------------------------------------------------

        try:
            timestamp_raw = data[0]

            if isinstance(
                timestamp_raw,
                bool,
            ):
                raise ValueError

            timestamp_ms = int(
                str(timestamp_raw)
            )

            timestamp = datetime.fromtimestamp(
                timestamp_ms / 1000,
                tz=timezone.utc,
            )

        except (
            TypeError,
            ValueError,
            OverflowError,
        ) as exc:

            raise ValueError(
                "Invalid candle timestamp"
            ) from exc

        # ------------------------------------------------------------
        # OHLCV
        # ------------------------------------------------------------

        try:
            open_price = Decimal(
                str(data[1])
            )

            high_price = Decimal(
                str(data[2])
            )

            low_price = Decimal(
                str(data[3])
            )

            close_price = Decimal(
                str(data[4])
            )

            volume = Decimal(
                str(data[5])
            )

        except (
            TypeError,
            ValueError,
            InvalidOperation,
        ) as exc:

            raise ValueError(
                "Invalid OKX candle values"
            ) from exc

        # ------------------------------------------------------------
        # Validation
        # ------------------------------------------------------------

        OKXExchange._validate_ohlcv(
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume,
        )

        return Candle(
            exchange="okx",
            symbol=symbol,
            timeframe=timeframe,
            timestamp=timestamp,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
        )

    # ================================================================
    # OHLCV VALIDATION
    # ================================================================

    @staticmethod
    def _validate_ohlcv(
        *,
        open_price: Decimal,
        high_price: Decimal,
        low_price: Decimal,
        close_price: Decimal,
        volume: Decimal,
    ) -> None:
        """
        Validate basic OHLCV relationships.
        """

        values = (
            open_price,
            high_price,
            low_price,
            close_price,
            volume,
        )

        for value in values:

            if not value.is_finite():
                raise ValueError(
                    "OHLCV values must be finite"
                )

        if open_price <= 0:
            raise ValueError(
                "Open price must be positive"
            )

        if high_price <= 0:
            raise ValueError(
                "High price must be positive"
            )

        if low_price <= 0:
            raise ValueError(
                "Low price must be positive"
            )

        if close_price <= 0:
            raise ValueError(
                "Close price must be positive"
            )

        if volume < 0:
            raise ValueError(
                "Volume cannot be negative"
            )

        if high_price < max(
            open_price,
            close_price,
        ):
            raise ValueError(
                "High price cannot be below "
                "open or close"
            )

        if low_price > min(
            open_price,
            close_price,
        ):
            raise ValueError(
                "Low price cannot be above "
                "open or close"
            )