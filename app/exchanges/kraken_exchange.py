from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import requests

from app.exchanges.base import BaseExchange
from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe


class KrakenExchange(BaseExchange):
    """
    Production Kraken public market-data exchange implementation.

    Responsibilities:
    - Fetch Kraken Spot market data.
    - Convert internal symbols/timeframes to Kraken format.
    - Validate API responses.
    - Validate OHLCV candle data.
    - Remove duplicate candles.
    - Return normalized Candle objects.
    """

    BASE_URL = "https://api.kraken.com"

    KLINE_ENDPOINT = "/0/public/OHLC"
    SERVER_TIME_ENDPOINT = "/0/public/Time"

    MAX_KLINE_LIMIT = 720

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
        return "kraken"

    # ================================================================
    # HTTP
    # ================================================================

    def _get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute a GET request against Kraken.

        Kraken returns API errors in the `error` list.
        A successful response normally contains:

            {
                "error": [],
                "result": {...}
            }
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
                "Kraken returned invalid JSON"
            ) from exc

        if not isinstance(data, dict):
            raise RuntimeError(
                "Invalid Kraken API response"
            )

        errors = data.get("error")

        if errors is not None:
            if not isinstance(errors, list):
                raise RuntimeError(
                    "Invalid Kraken API error response"
                )

            if errors:
                raise RuntimeError(
                    f"Kraken API error: {', '.join(map(str, errors))}"
                )

        return data

    # ================================================================
    # SYMBOLS
    # ================================================================

    def get_symbols(self) -> list[Symbol]:
        """
        Return supported Kraken Spot symbols.

        Only symbols represented by the internal Symbol enum
        are returned.
        """

        endpoint = "/0/public/AssetPairs"

        data = self._get(endpoint)

        result = data.get("result")

        if not isinstance(result, dict):
            raise RuntimeError(
                "Invalid Kraken AssetPairs response"
            )

        supported_symbols = {
            self._to_kraken_symbol(symbol): symbol
            for symbol in Symbol
        }

        available: list[Symbol] = []

        for key, item in result.items():

            if not isinstance(item, dict):
                continue

            candidates = (
                item.get("altname"),
                item.get("wsname"),
                key,
            )

            matched_symbol: Symbol | None = None

            for candidate in candidates:

                if not isinstance(candidate, str):
                    continue

                normalized = (
                    candidate
                    .replace("/", "")
                    .replace("-", "")
                    .upper()
                )

                symbol = supported_symbols.get(
                    normalized
                )

                if symbol is not None:
                    matched_symbol = symbol
                    break

            if matched_symbol is not None:
                available.append(matched_symbol)

        # Remove duplicates while preserving order.
        return list(dict.fromkeys(available))

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
        Retrieve Kraken Spot OHLCV candles.

        Kraken OHLC format:

        [
            time,
            open,
            high,
            low,
            close,
            vwap,
            volume,
            count
        ]

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
            "pair": self._to_kraken_symbol(symbol),
            "interval": self._to_kraken_timeframe(timeframe),
        }

        if start_time is not None:
            params["since"] = self._to_timestamp_seconds(
                start_time
            )

        data = self._get(
            self.KLINE_ENDPOINT,
            params=params,
        )

        result = data.get("result")

        if not isinstance(result, dict):
            raise RuntimeError(
                "Invalid Kraken OHLC response"
            )

        # Kraken uses a dynamic pair key inside result.
        raw_list: Any = None

        for key, value in result.items():

            if key == "last":
                continue

            if isinstance(value, list):
                raw_list = value
                break

        if raw_list is None:
            return []

        if not isinstance(raw_list, list):
            raise RuntimeError(
                "Kraken OHLC candle data must be a list"
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
                    f"Malformed Kraken candle at index {index}"
                ) from exc

            # Respect end_time locally because Kraken's
            # `since` parameter only provides a lower bound.
            if (
                end_time is not None
                and candle.timestamp > self._normalize_datetime(
                    end_time
                )
            ):
                continue

            if candle.timestamp in seen_timestamps:
                continue

            seen_timestamps.add(
                candle.timestamp
            )

            candles.append(candle)

        candles.sort(
            key=lambda candle: candle.timestamp
        )

        # Kraken may return more candles than requested.
        if len(candles) > limit:
            candles = candles[-limit:]

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
        Check whether Kraken's public API is reachable.
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
    def _to_kraken_symbol(
        symbol: Symbol,
    ) -> str:
        """
        Convert internal symbol into Kraken pair format.

        Examples:

            BTC/USDT -> BTCUSDT
            ETH/USDT -> ETHUSDT
        """

        value = (
            symbol.value
            .replace("/", "")
            .replace("-", "")
            .replace("_", "")
            .upper()
        )

        # Kraken historically uses XBT for Bitcoin in
        # several API contexts. Keep the conversion centralized.
        if value.startswith("BTC"):
            value = "XBT" + value[3:]

        return value

    # ================================================================
    # TIMEFRAME MAPPING
    # ================================================================

    @staticmethod
    def _to_kraken_timeframe(
        timeframe: Timeframe,
    ) -> int:
        """
        Convert internal timeframe into Kraken interval minutes.
        """

        mapping = {
            Timeframe.FIFTEEN_MINUTES: 15,
            Timeframe.ONE_HOUR: 60,
            Timeframe.FOUR_HOURS: 240,
            Timeframe.ONE_DAY: 1440,
        }

        try:
            return mapping[timeframe]

        except KeyError as exc:
            raise ValueError(
                f"Unsupported Kraken timeframe: {timeframe}"
            ) from exc

    # ================================================================
    # TIMESTAMP
    # ================================================================

    @staticmethod
    def _normalize_datetime(
        value: datetime,
    ) -> datetime:
        """
        Normalize datetime to UTC.

        Naive datetimes are interpreted as UTC.
        """

        if value.tzinfo is None:
            return value.replace(
                tzinfo=timezone.utc
            )

        return value.astimezone(
            timezone.utc
        )

    @staticmethod
    def _to_timestamp_seconds(
        value: datetime,
    ) -> int:
        """
        Convert datetime to Unix seconds.

        Naive datetimes are interpreted as UTC.
        """

        value = KrakenExchange._normalize_datetime(
            value
        )

        return int(
            value.timestamp()
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
        Parse a Kraken OHLC candle.

        Kraken format:

        [
            timestamp,
            open,
            high,
            low,
            close,
            vwap,
            volume,
            count
        ]
        """

        if not isinstance(data, list):
            raise ValueError(
                "Kraken candle must be a list"
            )

        if len(data) < 7:
            raise ValueError(
                "Kraken candle contains fewer than "
                "7 required fields"
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

            timestamp_seconds = int(
                str(timestamp_raw)
            )

            timestamp = datetime.fromtimestamp(
                timestamp_seconds,
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
                str(data[6])
            )

        except (
            TypeError,
            ValueError,
            InvalidOperation,
        ) as exc:

            raise ValueError(
                "Invalid Kraken candle values"
            ) from exc

        # ------------------------------------------------------------
        # Validation
        # ------------------------------------------------------------

        KrakenExchange._validate_ohlcv(
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
            exchange="kraken",
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