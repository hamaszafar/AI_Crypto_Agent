from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import requests

from app.core.http_client import HTTPClient
from app.core.rate_limiter import RateLimiter
from app.core.retry.retry import RetryPolicy
from app.exchanges.base import BaseExchange
from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe


class BybitExchange(BaseExchange):
    """
    Bybit Spot public market-data exchange implementation.

    Responsibilities:
    - Fetch Bybit Spot market data.
    - Convert internal symbols/timeframes to Bybit format.
    - Validate API responses.
    - Validate OHLCV candle data.
    - Remove duplicate candles.
    - Return normalized Candle objects.
    - Provide a public API health check.
    """

    BASE_URL = "https://api.bybit.com"

    KLINE_ENDPOINT = "/v5/market/kline"
    SERVER_TIME_ENDPOINT = "/v5/market/time"

    MAX_KLINE_LIMIT = 1000

    def __init__(
        self,
        timeout: float = 10.0,
        http_client: HTTPClient | None = None,
    ) -> None:
        if timeout <= 0:
            raise ValueError(
                "timeout must be greater than zero"
            )

        self.timeout = timeout

        if http_client is not None:
            self.http_client = http_client
        else:
            self.http_client = HTTPClient(
                rate_limiter=RateLimiter(
                    max_requests=10,
                    window_seconds=1.0,
                ),
                retry_policy=RetryPolicy(
                    max_attempts=3,
                    backoff_factor=1.0,
                    max_backoff=30.0,
                ),
                timeout=timeout,
            )

    # ================================================================
    # BASIC PROPERTIES
    # ================================================================
    @property
    def name(self) -> str:
        return "bybit"

    # ================================================================
    # HTTP
    # ================================================================

    def _get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute a GET request against Bybit.

        IMPORTANT:
        This method goes through self.http_client so tests can
        monkeypatch exchange.http_client.get().
        """

        try:
            response = self.http_client.get(
                f"{self.BASE_URL}{endpoint}",
                params=params,
            )

        except requests.RequestException:
            raise

        except Exception:
            # Preserve unexpected HTTP-client errors.
            raise

        # ------------------------------------------------------------
        # Normalize HTTPClient response
        # ------------------------------------------------------------

        if isinstance(response, dict):
            data = response

        else:
            try:
                response.raise_for_status()
            except requests.RequestException:
                raise

            try:
                data = response.json()
            except ValueError as exc:
                raise RuntimeError(
                    "Bybit returned invalid JSON"
                ) from exc

        # ------------------------------------------------------------
        # Validate response type
        # ------------------------------------------------------------

        if not isinstance(data, dict):
            raise RuntimeError(
                "Invalid Bybit API response"
            )

        # ------------------------------------------------------------
        # Validate Bybit API return code
        # ------------------------------------------------------------

        ret_code = data.get("retCode")

        if ret_code is not None and ret_code != 0:
            ret_msg = data.get(
                "retMsg",
                "Unknown error",
            )

            raise RuntimeError(
                f"Bybit API error {ret_code}: {ret_msg}"
            )

        return data

    # ================================================================
    # SYMBOLS
    # ================================================================

    def get_symbols(self) -> list[Symbol]:
        """
        Return supported Bybit Spot symbols.

        Only symbols represented by the internal Symbol enum
        are returned.
        """

        endpoint = "/v5/market/instruments-info"

        data = self._get(
            endpoint,
            params={
                "category": "spot",
            },
        )

        result = data.get("result")

        if not isinstance(result, dict):
            raise RuntimeError(
                "Invalid Bybit instruments response"
            )

        raw_list = result.get("list")

        if not isinstance(raw_list, list):
            raise RuntimeError(
                "Bybit instruments response is missing 'list'"
            )

        supported_symbols = {
            symbol.value: symbol
            for symbol in Symbol
        }

        available: list[Symbol] = []

        for item in raw_list:

            if not isinstance(item, dict):
                continue

            status = item.get("status")

            if status not in (None, "Trading"):
                continue

            base_coin = item.get("baseCoin")
            quote_coin = item.get("quoteCoin")

            if not base_coin or not quote_coin:
                continue

            value = f"{base_coin}/{quote_coin}"

            symbol = supported_symbols.get(value)

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
        limit: int = 500,
    ) -> list[Candle]:
        """
        Retrieve Bybit Spot OHLCV candles.

        Bybit returns kline data in reverse chronological order.

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
            "category": "spot",
            "symbol": self._to_bybit_symbol(symbol),
            "interval": self._to_bybit_timeframe(timeframe),
            "limit": limit,
        }

        if start_time is not None:
            params["start"] = self._to_timestamp_ms(
                start_time
            )

        if end_time is not None:
            params["end"] = self._to_timestamp_ms(
                end_time
            )

        data = self._get(
            self.KLINE_ENDPOINT,
            params=params,
        )

        result = data.get("result")

        if not isinstance(result, dict):
            raise RuntimeError(
                "Invalid Bybit kline response"
            )

        raw_list = result.get("list")

        if raw_list is None:
            return []

        if not isinstance(raw_list, list):
            raise RuntimeError(
                "Bybit kline list must be a list"
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
                    f"Malformed Bybit candle at index {index}"
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

        Only one candle is requested from Bybit.
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
        Check whether Bybit's public API is reachable.
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
    def _to_bybit_symbol(
        symbol: Symbol,
    ) -> str:
        """
        Convert internal symbol:

            BTC/USDT

        into Bybit symbol:

            BTCUSDT
        """

        return (
            symbol.value
            .replace("/", "")
            .replace("-", "")
            .upper()
        )

    # ================================================================
    # TIMEFRAME MAPPING
    # ================================================================

    @staticmethod
    def _to_bybit_timeframe(
        timeframe: Timeframe,
    ) -> str:
        """
        Convert internal timeframe into Bybit interval.
        """

        mapping = {
            Timeframe.FIFTEEN_MINUTES: "15",
            Timeframe.ONE_HOUR: "60",
            Timeframe.FOUR_HOURS: "240",
            Timeframe.ONE_DAY: "D",
        }

        try:
            return mapping[timeframe]

        except KeyError as exc:
            raise ValueError(
                f"Unsupported Bybit timeframe: {timeframe}"
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
        Parse a Bybit kline.

        Bybit Spot format:

        [
            startTime,
            openPrice,
            highPrice,
            lowPrice,
            closePrice,
            volume,
            turnover
        ]
        """

        if not isinstance(data, list):
            raise ValueError(
                "Bybit candle must be a list"
            )

        if len(data) < 6:
            raise ValueError(
                "Bybit candle contains fewer than "
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
                raise ValueError(
                    "Boolean timestamp is invalid"
                )

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
                "Invalid Bybit candle values"
            ) from exc

        # ------------------------------------------------------------
        # Validation
        # ------------------------------------------------------------

        BybitExchange._validate_ohlcv(
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume,
        )

        # ------------------------------------------------------------
        # Candle
        # ------------------------------------------------------------

        return Candle(
            exchange="bybit",
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