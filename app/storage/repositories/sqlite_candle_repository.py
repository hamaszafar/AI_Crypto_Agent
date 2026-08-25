from datetime import datetime
from decimal import Decimal

from app.storage.database import SQLiteDatabase
from app.storage.models import StoredCandle
from app.storage.repositories.candle_repository import CandleRepository


class SQLiteCandleRepository(CandleRepository):
    """Persistent SQLite implementation of CandleRepository."""

    def __init__(
        self,
        database: SQLiteDatabase,
    ) -> None:
        self.database = database
        self.database.initialize()

    def save_candle(
        self,
        candle: StoredCandle,
    ) -> None:
        """Persist a single candle."""

        self.database.connection.execute(
            """
            INSERT INTO candles (
                exchange,
                symbol,
                timeframe,
                timestamp,
                open,
                high,
                low,
                close,
                volume
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (
                exchange,
                symbol,
                timeframe,
                timestamp
            )
            DO UPDATE SET
                open = excluded.open,
                high = excluded.high,
                low = excluded.low,
                close = excluded.close,
                volume = excluded.volume
            """,
            (
                candle.exchange,
                candle.symbol,
                candle.timeframe,
                candle.timestamp.isoformat(),
                str(candle.open),
                str(candle.high),
                str(candle.low),
                str(candle.close),
                str(candle.volume),
            ),
        )

        self.database.connection.commit()

    def save_candles(
        self,
        candles: list[StoredCandle],
    ) -> None:
        """Persist multiple candles."""

        for candle in candles:
            self.save_candle(candle)

    def get_candles(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
    ) -> list[StoredCandle]:
        """Retrieve candles for a market/timeframe."""

        if limit is not None and limit < 0:
            raise ValueError("limit cannot be negative")

        query = """
            SELECT
                exchange,
                symbol,
                timeframe,
                timestamp,
                open,
                high,
                low,
                close,
                volume
            FROM candles
            WHERE exchange = ?
              AND symbol = ?
              AND timeframe = ?
        """

        parameters: list[object] = [
            exchange,
            symbol,
            timeframe,
        ]

        if start_time is not None:
            query += " AND timestamp >= ?"
            parameters.append(start_time.isoformat())

        if end_time is not None:
            query += " AND timestamp <= ?"
            parameters.append(end_time.isoformat())

        query += " ORDER BY timestamp ASC"

        if limit is not None:
            query += " LIMIT ?"
            parameters.append(limit)

        rows = self.database.connection.execute(
            query,
            parameters,
        ).fetchall()

        return [
            self._row_to_candle(row)
            for row in rows
        ]

    def get_latest_candle(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
    ) -> StoredCandle | None:
        """Retrieve the latest candle."""

        row = self.database.connection.execute(
            """
            SELECT
                exchange,
                symbol,
                timeframe,
                timestamp,
                open,
                high,
                low,
                close,
                volume
            FROM candles
            WHERE exchange = ?
              AND symbol = ?
              AND timeframe = ?
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            (
                exchange,
                symbol,
                timeframe,
            ),
        ).fetchone()

        if row is None:
            return None

        return self._row_to_candle(row)

    def count_candles(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
    ) -> int:
        """Return the number of candles for a market/timeframe."""

        row = self.database.connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM candles
            WHERE exchange = ?
              AND symbol = ?
              AND timeframe = ?
            """,
            (
                exchange,
                symbol,
                timeframe,
            ),
        ).fetchone()

        return int(row["count"])

    def count_all(
        self,
        exchange: str | None = None,
        symbol: str | None = None,
        timeframe: str | None = None,
    ) -> int:
        """
        Count candles with optional filters.

        If no filters are supplied, return the total
        number of stored candles.
        """

        query = "SELECT COUNT(*) AS count FROM candles"

        conditions: list[str] = []
        parameters: list[object] = []

        if exchange is not None:
            conditions.append("exchange = ?")
            parameters.append(exchange)

        if symbol is not None:
            conditions.append("symbol = ?")
            parameters.append(symbol)

        if timeframe is not None:
            conditions.append("timeframe = ?")
            parameters.append(timeframe)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        row = self.database.connection.execute(
            query,
            parameters,
        ).fetchone()

        return int(row["count"])

    @staticmethod
    def _row_to_candle(row: object) -> StoredCandle:
        """Convert a SQLite row into a StoredCandle."""

        return StoredCandle(
            exchange=row["exchange"],
            symbol=row["symbol"],
            timeframe=row["timeframe"],
            timestamp=datetime.fromisoformat(
                row["timestamp"]
            ),
            open=Decimal(row["open"]),
            high=Decimal(row["high"]),
            low=Decimal(row["low"]),
            close=Decimal(row["close"]),
            volume=Decimal(row["volume"]),
        )