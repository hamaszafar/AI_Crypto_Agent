import re
from app.market_data.exceptions import InvalidSymbolError

# Common quote assets in crypto markets, ordered by length descending to match longest quote first
DEFAULT_QUOTE_ASSETS = (
    "USDT",
    "USDC",
    "BUSD",
    "TUSD",
    "USD",
    "EUR",
    "GBP",
    "BTC",
    "ETH",
)

# Known base asset aliases across exchanges (e.g. Kraken uses XBT for BTC)
BASE_ALIASES = {
    "XBT": "BTC",
}

# Explicit symbol overrides for exchange specific formats
EXPLICIT_SYMBOL_MAP = {
    "XBTUSD": "BTC/USD",
    "XBT-USD": "BTC/USD",
    "XBT/USD": "BTC/USD",
    "XBTUSDT": "BTC/USDT",
    "XBT-USDT": "BTC/USDT",
    "XBT/USDT": "BTC/USDT",
}


def normalize_symbol(
    symbol: object,
    quote_assets: tuple[str, ...] = DEFAULT_QUOTE_ASSETS,
) -> str:
    """
    Normalize a market symbol into canonical BASE/QUOTE format.

    Examples:
        BTCUSDT -> BTC/USDT
        BTC-USDT -> BTC/USDT
        BTC_USDT -> BTC/USDT
        btc/usdt -> BTC/USDT
        BTC-USD -> BTC/USD
        XBT/USD -> BTC/USD

    Raises:
        InvalidSymbolError: If the symbol is non-string, empty, or malformed.
    """
    if not isinstance(symbol, str):
        raise InvalidSymbolError(
            f"Symbol must be a string, got {type(symbol).__name__}"
        )

    raw = symbol.strip().upper()
    if not raw:
        raise InvalidSymbolError("Symbol cannot be empty")

    if raw in EXPLICIT_SYMBOL_MAP:
        return EXPLICIT_SYMBOL_MAP[raw]

    # Handle explicit delimiters: '/', '-', '_'
    if "/" in raw:
        parts = raw.split("/")
        if len(parts) == 2 and parts[0] and parts[1]:
            base = BASE_ALIASES.get(parts[0], parts[0])
            quote = parts[1]
            _validate_symbol_parts(base, quote)
            return f"{base}/{quote}"
        raise InvalidSymbolError(f"Malformed symbol with slash: {symbol!r}")

    if "-" in raw:
        parts = raw.split("-")
        if len(parts) == 2 and parts[0] and parts[1]:
            base = BASE_ALIASES.get(parts[0], parts[0])
            quote = parts[1]
            _validate_symbol_parts(base, quote)
            return f"{base}/{quote}"
        raise InvalidSymbolError(f"Malformed symbol with hyphen: {symbol!r}")

    if "_" in raw:
        parts = raw.split("_")
        if len(parts) == 2 and parts[0] and parts[1]:
            base = BASE_ALIASES.get(parts[0], parts[0])
            quote = parts[1]
            _validate_symbol_parts(base, quote)
            return f"{base}/{quote}"
        raise InvalidSymbolError(f"Malformed symbol with underscore: {symbol!r}")

    # Compact symbol without delimiter (e.g. BTCUSDT, ETHUSD)
    for quote in quote_assets:
        if raw.endswith(quote) and len(raw) > len(quote):
            base_raw = raw[: -len(quote)]
            base = BASE_ALIASES.get(base_raw, base_raw)
            _validate_symbol_parts(base, quote)
            return f"{base}/{quote}"

    raise InvalidSymbolError(
        f"Unable to parse base/quote pair for symbol: {symbol!r}"
    )


def _validate_symbol_parts(base: str, quote: str) -> None:
    pattern = r"^[A-Z0-9]{2,10}$"
    if not re.match(pattern, base) or not re.match(pattern, quote):
        raise InvalidSymbolError(
            f"Invalid base/quote characters in symbol parts: base={base!r}, quote={quote!r}"
        )
