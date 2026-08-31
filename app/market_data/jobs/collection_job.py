from dataclasses import dataclass


@dataclass(frozen=True)
class CollectionJob:
    """
    Immutable description of a single market-data collection job.

    A job identifies exactly what market data should be collected.
    """

    exchange: str
    symbol: str
    timeframe: str
    page_size: int = 100

    def __post_init__(self) -> None:
        if not isinstance(self.exchange, str) or not self.exchange.strip():
            raise ValueError("exchange must not be empty")

        if not isinstance(self.symbol, str) or not self.symbol.strip():
            raise ValueError("symbol must not be empty")

        if not isinstance(self.timeframe, str) or not self.timeframe.strip():
            raise ValueError("timeframe must not be empty")

        if self.page_size <= 0:
            raise ValueError("page_size must be greater than zero")

        exchange = self.exchange.strip().lower()
        symbol = self.symbol.strip().upper()
        timeframe = self.timeframe.strip().lower()

        object.__setattr__(self, "exchange", exchange)
        object.__setattr__(self, "symbol", symbol)
        object.__setattr__(self, "timeframe", timeframe)

    @property
    def key(self) -> tuple[str, str, str]:
        """
        Unique logical identity of this collection job.
        """
        return (
            self.exchange,
            self.symbol,
            self.timeframe,
        )

    @property
    def key_str(self) -> str:
        """
        Stable string key representation of this collection job.
        Example: binance:BTC/USDT:15m
        """
        return f"{self.exchange}:{self.symbol}:{self.timeframe}"