import json
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from app.storage.database import SQLiteDatabase
from app.signals.models import (
    Signal,
    SignalDirection,
    SignalStrength,
    SignalConfidence,
)


@dataclass(frozen=True)
class StoredSignal:
    """Immutable representation of a persisted signal.

    The primary key is the combination (symbol, timeframe, timestamp).
    ``execution_id`` is a deterministic identifier for the run that
    produced the signal (e.g. a UUID or hash of the input data).
    """
    symbol: str
    timeframe: str
    timestamp: datetime
    direction: str  # store enum name
    strength: str
    confidence: str
    score: float
    regime: Optional[str] = None
    reasons: List[str] = field(default_factory=list)
    execution_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.utcnow())
    state: str = "generated"  # added lifecycle state
    """Immutable representation of a persisted signal.

    The primary key is the combination (symbol, timeframe, timestamp).
    ``execution_id`` is a deterministic identifier for the run that
    produced the signal (e.g. a UUID or hash of the input data).
    """

    symbol: str
    timeframe: str
    timestamp: datetime
    direction: str  # store enum name
    strength: str
    confidence: str
    score: float
    regime: Optional[str] = None
    reasons: List[str] = field(default_factory=list)
    execution_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.utcnow())

    @classmethod
    def from_signal(cls, signal: Signal, execution_id: Optional[str] = None) -> "StoredSignal":
        return cls(
            symbol=signal.context.symbol,
            timeframe=signal.context.timeframe,
            timestamp=signal.context.timestamp,
            direction=signal.direction.name,
            strength=signal.strength.name,
            confidence=signal.confidence.name,
            score=float(signal.score),
            regime=signal.context.market_regime.name if signal.context.market_regime else None,
            reasons=[e.reason.name for e in signal.evidences],
            execution_id=execution_id,
        )


class SignalRepository:
    """Thin SQLite‑based repository for ``StoredSignal``.

    The repository creates the ``signals`` table on first use if it does not
    exist. Primary key is ``symbol, timeframe, timestamp`` which gives us
    natural idempotency – attempts to insert a duplicate are ignored.
    """

    _CREATE_TABLE = """
    CREATE TABLE IF NOT EXISTS signals (
        symbol TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        direction TEXT NOT NULL,
        strength TEXT NOT NULL,
        confidence TEXT NOT NULL,
        score REAL NOT NULL,
        regime TEXT,
        reasons TEXT,
        execution_id TEXT,
        created_at TEXT NOT NULL,
        state TEXT NOT NULL DEFAULT 'generated',
        PRIMARY KEY (symbol, timeframe, timestamp)
    )
    """

    def __init__(self, db_path: str = "data/market_data.db") -> None:
        self._db = SQLiteDatabase(db_path)
        self._db.initialize()
        self._db.connection.execute(self._CREATE_TABLE)
        self._db.connection.commit()

    def save(self, stored: StoredSignal) -> None:
        """Insert a signal if it does not already exist.

        Duplicate insertions are silently ignored – this satisfies the
        idempotency requirement.
        """
        cursor = self._db.connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO signals (
                    symbol, timeframe, timestamp, direction, strength,
                    confidence, score, regime, reasons, execution_id, created_at, state
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stored.symbol,
                    stored.timeframe,
                    stored.timestamp.isoformat(),
                    stored.direction,
                    stored.strength,
                    stored.confidence,
                    stored.score,
                    stored.regime,
                    json.dumps(stored.reasons),
                    stored.execution_id,
                    stored.created_at.isoformat(),
                    stored.state,
                ),
            )
            self._db.connection.commit()
        except Exception:
            # Assume integrity error -> duplicate, ignore
            self._db.connection.rollback()

        """Insert a signal if it does not already exist.

        Duplicate insertions are silently ignored – this satisfies the
        idempotency requirement.
        """
        cursor = self._db.connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO signals (
                    symbol, timeframe, timestamp, direction, strength,
                    confidence, score, regime, reasons, execution_id, created_at, state
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stored.symbol,
                    stored.timeframe,
                    stored.timestamp.isoformat(),
                    stored.direction,
                    stored.strength,
                    stored.confidence,
                    stored.score,
                    stored.regime,
                    json.dumps(stored.reasons),
                    stored.execution_id,
                    stored.created_at.isoformat(),
                    stored.state,
                ),
            )
            self._db.connection.commit()
        except Exception:
            # Assume integrity error -> duplicate, ignore
            self._db.connection.rollback()

    def get_latest(self, symbol: str, timeframe: str) -> Optional[StoredSignal]:
        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            SELECT * FROM signals
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp DESC LIMIT 1
            """,
            (symbol, timeframe),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_signal(row)

        cursor = self._db.connection.cursor()
        cursor.execute(
            """
            SELECT * FROM signals
            WHERE symbol = ? AND timeframe = ?
            ORDER BY timestamp DESC LIMIT 1
            """,
            (symbol, timeframe),
        )
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_signal(row)

    def _row_to_signal(self, row) -> StoredSignal:
        return StoredSignal(
            symbol=row["symbol"],
            timeframe=row["timeframe"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            direction=row["direction"],
            strength=row["strength"],
            confidence=row["confidence"],
            score=row["score"],
            regime=row["regime"],
            reasons=json.loads(row["reasons"]),
            execution_id=row["execution_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            state=row["state"],
        )

    def exists(self, symbol: str, timeframe: str, timestamp: datetime) -> bool:
        """Return ``True`` if a signal with the given primary‑key exists."""
        cursor = self._db.connection.cursor()
        cursor.execute(
            "SELECT 1 FROM signals WHERE symbol = ? AND timeframe = ? AND timestamp = ?",
            (symbol, timeframe, timestamp.isoformat()),
        )
        return cursor.fetchone() is not None

    def update_state(self, symbol: str, timeframe: str, timestamp: datetime, new_state: str) -> None:
        """Update the ``state`` column for an existing signal.
        No validation of transition is performed here – callers should use
        :func:`app.signals.lifecycle.valid_transition`.
        """
        cursor = self._db.connection.cursor()
        cursor.execute(
            "UPDATE signals SET state = ? WHERE symbol = ? AND timeframe = ? AND timestamp = ?",
            (new_state, symbol, timeframe, timestamp.isoformat()),
        )
        self._db.connection.commit()
