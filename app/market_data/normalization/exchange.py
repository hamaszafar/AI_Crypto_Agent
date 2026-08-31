from app.market_data.exceptions import InvalidExchangeError


def normalize_exchange_name(name: object) -> str:
    """
    Normalize exchange name to canonical form (lowercase, trimmed).

    Requirements:
    - Must be a non-empty string
    - Trim whitespace
    - Lowercase
    - Reject non-string or empty inputs
    """
    if not isinstance(name, str):
        raise InvalidExchangeError(
            f"Exchange name must be a string, got {type(name).__name__}"
        )

    normalized = name.strip().lower()
    if not normalized:
        raise InvalidExchangeError("Exchange name cannot be empty")

    return normalized
