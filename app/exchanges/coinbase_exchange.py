from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import requests

from app.exchanges.base import BaseExchange
from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe


class CoinbaseExchange(BaseExchange):
    """
    Coinbase public market-data exchange implementation.

    Responsibilities:
    - Fetch Coinbase Spot market data.
    - Convert internal symbols/timeframes to Coinbase format.
    - Validate API responses.
    - Validate OHLCV candle data.
    - Remove duplicate candles.
    - Return normalized Candle objects.
    """

    BASE_URL = "https://api.exchange.coinbase.com"

    PRODUCTS_ENDPOINT = "/products"
    KLINE_ENDPOINT = "/products/{product_id}/candles"
    TIME_ENDPOINT = "/time"

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
        return "coinbase"

    # ================================================================
    # HTTP
    # ================================================================

    def _get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """
        Execute a GET request against Coinbase.
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
            return response.json()

        except ValueError as exc:
            raise RuntimeError(
                "Coinbase returned invalid JSON"
            ) from exc

    # ================================================================
    # SYMBOLS
    # ================================================================

    def get_symbols(self) -> list[Symbol]:
        """
        Return supported Coinbase Spot symbols.

        Only symbols represented by the internal Symbol enum
        are returned.
        """

        data = self._get(
            self.PRODUCTS_ENDPOINT
        )

        if not isinstance(data, list):
            raise RuntimeError(
                "Invalid Coinbase products response"
            )

        supported_symbols = {
            self._to_coinbase_symbol(symbol): symbol
            for symbol in Symbol
        }

        available: list[Symbol] = []

        for item in data:

            if not isinstance(item, dict):
                continue

            product_id = item.get("id")

            if not isinstance(product_id, str):
                continue

            symbol = supported_symbols.get(
                product_id.upper()
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
        Retrieve Coinbase Spot OHLCV candles.

        Coinbase returns candle rows in the form:

            [
                time,
                low,
                high,
                open,
                close,
                volume
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
            "granularity": self._to_coinbase_timeframe(
                timeframe
            ),
        }

        if start_time is not None:
            params["start"] = self._to_iso_timestamp(
                start_time
            )

        if end_time is not None:
            params["end"] = self._to_iso_timestamp(
                end_time
            )

        endpoint = self.KLINE_ENDPOINT.format(
            product_id=self._to_coinbase_symbol(symbol)
        )

        data = self._get(
            endpoint,
            params=params,
        )

        if data is None:
            return []

        if not isinstance(data, list):
            raise RuntimeError(
                "Coinbase candle response must be a list"
            )

        if not data:
            return []

        candles: list[Candle] = []

        seen_timestamps: set[datetime] = set()

        for index, item in enumerate(data):

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
                    f"Malformed Coinbase candle "
                    f"at index {index}"
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

        # Coinbase's API does not provide a limit parameter.
        # Apply the requested limit after normalization.
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
        Check whether Coinbase public API is reachable.
        """

        try:
            self._get(
                self.TIME_ENDPOINT
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
    def _to_coinbase_symbol(
        symbol: Symbol,
    ) -> str:
        """
        Convert internal symbol:

            BTC/USDT

        into Coinbase product format:

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
    def _to_coinbase_timeframe(
        timeframe: Timeframe,
    ) -> int:
        """
        Convert internal timeframe into Coinbase
        candle granularity in seconds.
        """

        mapping = {
            Timeframe.FIFTEEN_MINUTES: 900,
            Timeframe.ONE_HOUR: 3600,
            Timeframe.FOUR_HOURS: 14400,
            Timeframe.ONE_DAY: 86400,
        }

        try:
            return mapping[timeframe]

        except KeyError as exc:
            raise ValueError(
                f"Unsupported Coinbase timeframe: "
                f"{timeframe}"
            ) from exc

    # ================================================================
    # TIMESTAMP
    # ================================================================

    @staticmethod
    def _to_iso_timestamp(
        value: datetime,
    ) -> str:
        """
        Convert datetime to Coinbase ISO-8601 timestamp.

        Naive datetimes are interpreted as UTC.
        """

        if value.tzinfo is None:
            value = value.replace(
                tzinfo=timezone.utc
            )

        value = value.astimezone(
            timezone.utc
        )

        return value.isoformat().replace(
            "+00:00",
            "Z",
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
        Parse a Coinbase candle.

        Coinbase format:

        [
            time,
            low,
            high,
            open,
            close,
            volume
        ]
        """

        if not isinstance(data, list):
            raise ValueError(
                "Coinbase candle must be a list"
            )

        if len(data) < 6:
            raise ValueError(
                "Coinbase candle contains fewer than "
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
            low_price = Decimal(
                str(data[1])
            )

            high_price = Decimal(
                str(data[2])
            )

            open_price = Decimal(
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
                "Invalid Coinbase candle values"
            ) from exc

        # ------------------------------------------------------------
        # Validation
        # ------------------------------------------------------------

        CoinbaseExchange._validate_ohlcv(
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume,
        )

        return Candle(
            exchange="coinbase",
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