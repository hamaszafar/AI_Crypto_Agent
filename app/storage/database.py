import sqlite3
from pathlib import Path


class SQLiteDatabase:
    """Small SQLite database wrapper."""

    def __init__(self, path: str | Path = "data/market_data.db") -> None:
        self.path = Path(path)

        if self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)

        self.connection = sqlite3.connect(
            self.path,
            check_same_thread=False,
        )

        self.connection.row_factory = sqlite3.Row

    def initialize(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS candles (
                exchange TEXT NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp TEXT NOT NULL,

                open TEXT NOT NULL,
                high TEXT NOT NULL,
                low TEXT NOT NULL,
                close TEXT NOT NULL,
                volume TEXT NOT NULL,

                PRIMARY KEY (
                    exchange,
                    symbol,
                    timeframe,
                    timestamp
                )
            )
            """
        )

        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_candles_lookup
            ON candles (
                exchange,
                symbol,
                timeframe,
                timestamp
            )
            """
        )

        self.connection.commit()

    def close(self) -> None:
        self.connection.close()