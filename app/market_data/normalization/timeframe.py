from app.market_data.exceptions import InvalidTimeframeError

CANONICAL_TIMEFRAMES = ("15m", "1h", "4h", "1d")

TIMEFRAME_MAP = {
    "15": "15m",
    "15m": "15m",
    "15min": "15m",
    "60": "1h",
    "60m": "1h",
    "1h": "1h",
    "1H": "1h",
    "240": "4h",
    "240m": "4h",
    "4h": "4h",
    "4H": "4h",
    "1440": "1d",
    "1440m": "1d",
    "1d": "1d",
    "1D": "1d",
    "d": "1d",
    "1day": "1d",
}


def normalize_timeframe(tf: object) -> str:
    """
    Normalize timeframe string or integer to canonical form: 15m, 1h, 4h, 1d.

    Examples:
        "15" -> "15m"
        "60" -> "1h"
        "240" -> "4h"
        "1440" -> "1d"
        "1H" -> "1h"
        "1D" -> "1d"

    Raises:
        InvalidTimeframeError: If timeframe is unrecognized or invalid type.
    """
    if isinstance(tf, int):
        tf_str = str(tf)
    elif isinstance(tf, str):
        tf_str = tf.strip()
    else:
        raise InvalidTimeframeError(
            f"Timeframe must be string or integer, got {type(tf).__name__}"
        )

    if not tf_str:
        raise InvalidTimeframeError("Timeframe cannot be empty")

    if tf_str in TIMEFRAME_MAP:
        return TIMEFRAME_MAP[tf_str]

    tf_lower = tf_str.lower()
    if tf_lower in TIMEFRAME_MAP:
        return TIMEFRAME_MAP[tf_lower]

    raise InvalidTimeframeError(f"Unsupported timeframe: {tf!r}")
