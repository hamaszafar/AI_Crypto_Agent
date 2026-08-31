from datetime import datetime, timezone
from decimal import Decimal

from app.market_data.exceptions import (
    InvalidExchangeError,
    InvalidOHLCError,
    InvalidSymbolError,
    InvalidTimeframeError,
    InvalidTimestampError,
    InvalidVolumeError,
)


def validate_candle_fields(
    exchange: str,
    symbol: str,
    timeframe: str,
    timestamp: datetime,
    open_price: Decimal,
    high_price: Decimal,
    low_price: Decimal,
    close_price: Decimal,
    volume: Decimal,
    strict_ohlc: bool = False,
) -> None:
    """
    Validation for normalized MarketCandle attributes.

    Raises specific CandleValidationError subclasses on failure.
    """
    # 1. Exchange
    if not isinstance(exchange, str) or exchange != exchange.lower() or not exchange.strip():
        raise InvalidExchangeError(f"Exchange name must be normalized lowercase: {exchange!r}")

    # 2. Symbol
    if not isinstance(symbol, str) or "/" not in symbol:
        raise InvalidSymbolError(f"Symbol must be canonical BASE/QUOTE format: {symbol!r}")

    # 3. Timeframe
    if timeframe not in ("15m", "1h", "4h", "1d"):
        raise InvalidTimeframeError(f"Unsupported canonical timeframe: {timeframe!r}")

    # 4. Timestamp
    if not isinstance(timestamp, datetime) or timestamp.tzinfo is None or timestamp.tzinfo != timezone.utc:
        raise InvalidTimestampError(f"Timestamp must be timezone-aware UTC datetime: {timestamp!r}")

    # 5. Type checking for numeric fields
    for name, val in [("open", open_price), ("high", high_price), ("low", low_price), ("close", close_price)]:
        if not isinstance(val, Decimal):
            raise InvalidOHLCError(f"Price {name} must be a Decimal: {val!r}")

    if not isinstance(volume, Decimal):
        raise InvalidVolumeError(f"Volume must be a Decimal: {volume!r}")

    if strict_ohlc:
        # Strict OHLC price sanity and relationship checks
        for name, val in [("open", open_price), ("high", high_price), ("low", low_price), ("close", close_price)]:
            if not val.is_finite() or val <= Decimal("0"):
                raise InvalidOHLCError(f"Price {name} must be a positive finite Decimal: {val!r}")

        if high_price < low_price:
            raise InvalidOHLCError(f"High price ({high_price}) cannot be lower than low price ({low_price})")
        if high_price < open_price:
            raise InvalidOHLCError(f"High price ({high_price}) cannot be lower than open price ({open_price})")
        if high_price < close_price:
            raise InvalidOHLCError(f"High price ({high_price}) cannot be lower than close price ({close_price})")
        if low_price > open_price:
            raise InvalidOHLCError(f"Low price ({low_price}) cannot be higher than open price ({open_price})")
        if low_price > close_price:
            raise InvalidOHLCError(f"Low price ({low_price}) cannot be higher than close price ({close_price})")

        # Volume sanity
        if not volume.is_finite() or volume < Decimal("0"):
            raise InvalidVolumeError(f"Volume must be a non-negative finite Decimal: {volume!r}")
