from __future__ import annotations

from typing import TYPE_CHECKING, Any
from app.market_data.exceptions import CandleValidationError
from app.market_data.normalization.candle import validate_candle_fields
from app.market_data.normalization.decimal import normalize_decimal
from app.market_data.normalization.exchange import normalize_exchange_name
from app.market_data.normalization.symbol import normalize_symbol
from app.market_data.normalization.timeframe import normalize_timeframe
from app.market_data.normalization.timestamp import normalize_timestamp

if TYPE_CHECKING:
    from app.market_data.models import MarketCandle


class MarketDataNormalizer:
    """
    Dedicated Normalization Service.

    Converts raw market inputs into canonical MarketCandle instances.
    Operates strictly on data without network or side-effects.
    """

    @staticmethod
    def normalize_candle(
        exchange: object,
        symbol: object,
        timeframe: object,
        timestamp: object,
        open_val: object,
        high_val: object,
        low_val: object,
        close_val: object,
        volume_val: object,
    ) -> MarketCandle:
        """
        Normalize individual candle attributes into a canonical MarketCandle.
        """
        from app.market_data.models import MarketCandle

        norm_exchange = normalize_exchange_name(exchange)
        norm_symbol = normalize_symbol(symbol)
        norm_timeframe = normalize_timeframe(timeframe)
        norm_timestamp = normalize_timestamp(timestamp)

        norm_open = normalize_decimal(open_val, field_name="open", allow_zero=False)
        norm_high = normalize_decimal(high_val, field_name="high", allow_zero=False)
        norm_low = normalize_decimal(low_val, field_name="low", allow_zero=False)
        norm_close = normalize_decimal(close_val, field_name="close", allow_zero=False)
        norm_volume = normalize_decimal(volume_val, field_name="volume", allow_zero=True)

        validate_candle_fields(
            exchange=norm_exchange,
            symbol=norm_symbol,
            timeframe=norm_timeframe,
            timestamp=norm_timestamp,
            open_price=norm_open,
            high_price=norm_high,
            low_price=norm_low,
            close_price=norm_close,
            volume=norm_volume,
            strict_ohlc=True,
        )

        return MarketCandle(
            exchange=norm_exchange,
            symbol=norm_symbol,
            timeframe=norm_timeframe,
            timestamp=norm_timestamp,
            open=norm_open,
            high=norm_high,
            low=norm_low,
            close=norm_close,
            volume=norm_volume,
        )

    @staticmethod
    def from_exchange_candle(candle: Any) -> MarketCandle:
        """
        Convert an exchange Candle model into a canonical MarketCandle.
        """
        symbol_str = candle.symbol.value if hasattr(candle.symbol, "value") else str(candle.symbol)
        tf_str = candle.timeframe.value if hasattr(candle.timeframe, "value") else str(candle.timeframe)
        return MarketDataNormalizer.normalize_candle(
            exchange=candle.exchange,
            symbol=symbol_str,
            timeframe=tf_str,
            timestamp=candle.timestamp,
            open_val=candle.open,
            high_val=candle.high,
            low_val=candle.low,
            close_val=candle.close,
            volume_val=candle.volume,
        )

    @staticmethod
    def normalize_raw_tuple(
        exchange: object,
        symbol: object,
        timeframe: object,
        raw_row: list | tuple,
    ) -> MarketCandle:
        """
        Normalize standard OHLCV array format [timestamp, open, high, low, close, volume].
        """
        if not isinstance(raw_row, (list, tuple)) or len(raw_row) < 6:
            raise CandleValidationError(
                f"Raw candle array must contain at least 6 elements, got {raw_row!r}"
            )

        return MarketDataNormalizer.normalize_candle(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            timestamp=raw_row[0],
            open_val=raw_row[1],
            high_val=raw_row[2],
            low_val=raw_row[3],
            close_val=raw_row[4],
            volume_val=raw_row[5],
        )

    @staticmethod
    def normalize_raw_dict(
        exchange: object,
        symbol: object,
        timeframe: object,
        raw_dict: dict[str, Any],
        field_map: dict[str, str] | None = None,
    ) -> MarketCandle:
        """
        Normalize dictionary-based candle formats.
        """
        if not isinstance(raw_dict, dict):
            raise CandleValidationError(
                f"Raw candle data must be a dict, got {type(raw_dict).__name__}"
            )

        f_map = {
            "timestamp": "timestamp",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
        }
        if field_map:
            f_map.update(field_map)

        try:
            ts_val = raw_dict[f_map["timestamp"]]
            o_val = raw_dict[f_map["open"]]
            h_val = raw_dict[f_map["high"]]
            l_val = raw_dict[f_map["low"]]
            c_val = raw_dict[f_map["close"]]
            v_val = raw_dict[f_map["volume"]]
        except KeyError as exc:
            raise CandleValidationError(f"Missing required candle field {exc} in raw dict: {raw_dict!r}") from exc

        return MarketDataNormalizer.normalize_candle(
            exchange=exchange,
            symbol=symbol,
            timeframe=timeframe,
            timestamp=ts_val,
            open_val=o_val,
            high_val=h_val,
            low_val=l_val,
            close_val=c_val,
            volume_val=v_val,
        )
