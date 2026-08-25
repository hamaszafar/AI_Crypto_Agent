from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

import requests

from app.exchanges.base import BaseExchange
from app.exchanges.models import Candle
from app.exchanges.types import Symbol, Timeframe


class BinanceExchange(BaseExchange):
    """
    Production Binance public market-data exchange implementation.

    Responsibilities:
    - Fetch Binance Spot market data.
    - Convert internal symbols/timeframes to Binance format.
    - Validate API responses.
    - Validate OHLCV candle data.
    - Remove duplicate candles.
    - Return normalized Candle objects.
    """

    BASE_URL = "https://api.binance.com"

    KLINES_ENDPOINT = "/api/v3/klines"
    EXCHANGE_INFO_ENDPOINT = "/api/v3/exchangeInfo"
    PING_ENDPOINT = "/api/v3/ping"

    MAX_KLINE_LIMIT = 1000

    def __init__(self, timeout: int = 10) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        self.timeout = timeout

    @property
    def name(self) -> str:
        return "binance"

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    def _get(
        self,
        endpoint: str,
        params: dict | None = None,
    ):
        """
        Execute a Binance GET request.

        HTTP errors are propagated as requests exceptions.
        Binance API-level errors are converted into RuntimeError.
        """

        response = requests.get(
            f"{self.BASE_URL}{endpoint}",
            params=params,
            timeout=self.timeout,
        )

        response.raise_for_status()

        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError(
                "Binance returned invalid JSON"
            ) from exc

        # Binance API errors normally look like:
        #
        # {
        #     "code": -1121,
        #     "msg": "Invalid symbol."
        # }
        if isinstance(data, dict) and "code" in data:
            raise RuntimeError(
                f"Binance API error "
                f"{data.get('code')}: "
                f"{data.get('msg', 'Unknown error')}"
            )

        return data

    # ------------------------------------------------------------------
    # Symbols
    # ------------------------------------------------------------------

    def get_symbols(self) -> list[Symbol]:
        """
        Return supported Binance trading symbols.

        Only symbols currently in TRADING status are returned.
        """

        data = self._get(self.EXCHANGE_INFO_ENDPOINT)

        if not isinstance(data, dict):
            raise RuntimeError(
                "Invalid Binance exchangeInfo response"
            )

        raw_symbols = data.get("symbols")

        if not isinstance(raw_symbols, list):
            raise RuntimeError(
                "Binance exchangeInfo response is missing 'symbols'"
            )

        available_symbols: list[Symbol] = []

        supported_symbols = {
            symbol.value
            for symbol in Symbol
        }

        for item in raw_symbols:
            if not isinstance(item, dict):
                continue

            if item.get("status") != "TRADING":
                continue

            base_asset = item.get("baseAsset")
            quote_asset = item.get("quoteAsset")

            if not base_asset or not quote_asset:
                continue

            symbol_value = (
                f"{base_asset}/{quote_asset}"
            )

            if symbol_value in supported_symbols:
                available_symbols.append(
                    Symbol(symbol_value)
                )

        return available_symbols

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
        """
        Retrieve Binance OHLCV candles.

        Binance allows a maximum of 1000 candles per request.
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

        params: dict = {
            "symbol": self._to_binance_symbol(symbol),
            "interval": self._to_binance_timeframe(timeframe),
            "limit": limit,
        }

        if start_time is not None:
            params["startTime"] = self._to_timestamp_ms(
                start_time
            )

        if end_time is not None:
            params["endTime"] = self._to_timestamp_ms(
                end_time
            )

        data = self._get(
            self.KLINES_ENDPOINT,
            params=params,
        )

        if data is None:
            return []

        if not isinstance(data, list):
            raise RuntimeError(
                "Binance kline response must be a list"
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
            except (ValueError, InvalidOperation, TypeError) as exc:
                raise RuntimeError(
                    f"Malformed Binance candle "
                    f"at index {index}"
                ) from exc

            # Deduplicate by candle timestamp.
            if candle.timestamp in seen_timestamps:
                continue

            seen_timestamps.add(candle.timestamp)
            candles.append(candle)

        # Always return chronological data.
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

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def health_check(self) -> bool:
        """
        Check whether Binance's public API is reachable.
        """

        try:
            self._get(self.PING_ENDPOINT)
            return True

        except (
            requests.RequestException,
            RuntimeError,
            ValueError,
        ):
            return False

    # ------------------------------------------------------------------
    # Symbol mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _to_binance_symbol(
        symbol: Symbol,
    ) -> str:
        """
        Convert internal symbol:

            BTC/USDT

        to Binance:

            BTCUSDT
        """

        return (
            symbol.value
            .replace("/", "")
            .replace("-", "")
            .upper()
        )

    # ------------------------------------------------------------------
    # Timeframe mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _to_binance_timeframe(
        timeframe: Timeframe,
    ) -> str:
        """
        Convert internal timeframe to Binance interval.
        """

        mapping = {
            Timeframe.FIFTEEN_MINUTES: "15m",
            Timeframe.ONE_HOUR: "1h",
            Timeframe.FOUR_HOURS: "4h",
            Timeframe.ONE_DAY: "1d",
        }

        try:
            return mapping[timeframe]

        except KeyError as exc:
            raise ValueError(
                f"Unsupported Binance timeframe: {timeframe}"
            ) from exc

    # ------------------------------------------------------------------
    # Timestamp
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Candle parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_candle(
        data: list,
        symbol: Symbol,
        timeframe: Timeframe,
    ) -> Candle:
        """
        Convert a Binance kline into a Candle.

        Binance kline format:

        [
            open_time,
            open,
            high,
            low,
            close,
            volume,
            close_time,
            quote_volume,
            trades,
            ...
        ]
        """

        if not isinstance(data, list):
            raise ValueError(
                "Binance candle must be a list"
            )

        if len(data) < 6:
            raise ValueError(
                "Binance candle contains fewer than "
                "6 required fields"
            )

        try:
            timestamp_ms = data[0]

            if not isinstance(
                timestamp_ms,
                (int, float),
            ):
                raise ValueError(
                    "Invalid candle timestamp"
                )

            timestamp = datetime.fromtimestamp(
                timestamp_ms / 1000,
                tz=timezone.utc,
            )

            open_price = Decimal(str(data[1]))
            high_price = Decimal(str(data[2]))
            low_price = Decimal(str(data[3]))
            close_price = Decimal(str(data[4]))
            volume = Decimal(str(data[5]))

        except (
            TypeError,
            ValueError,
            InvalidOperation,
        ) as exc:
            raise ValueError(
                "Invalid Binance candle values"
            ) from exc

        BinanceExchange._validate_ohlcv(
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume,
        )

        return Candle(
            exchange="binance",
            symbol=symbol,
            timeframe=timeframe,
            timestamp=timestamp,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
        )

    # ------------------------------------------------------------------
    # OHLCV validation
    # ------------------------------------------------------------------

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