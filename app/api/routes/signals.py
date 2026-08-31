"""Signal endpoints for the Trading Signal Agent API.

Provides:
- GET /signals – list latest signal for each symbol/timeframe pair.
- GET /signals/{symbol} – list latest signals for a specific symbol.
- GET /signals/{symbol}/{timeframe} – latest signal for a specific pair.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.signals.persistence import SignalRepository

router = APIRouter(prefix="/signals", tags=["signals"])

_repo = SignalRepository()

@router.get("", summary="List latest signals for all symbol/timeframe pairs")
async def list_all_latest():
    cursor = _repo._db.connection.cursor()
    cursor.execute("SELECT * FROM signals ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    if not rows:
        return []
    return [_repo._row_to_signal(dict(row)) for row in rows]

@router.get("/{symbol}", summary="Latest signals for a symbol")
async def latest_by_symbol(symbol: str):
    cursor = _repo._db.connection.cursor()
    cursor.execute(
        "SELECT * FROM signals WHERE symbol = ? ORDER BY timestamp DESC",
        (symbol,),
    )
    rows = cursor.fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="No signals for symbol")
    return [_repo._row_to_signal(dict(row)) for row in rows]

@router.get("/{symbol}/{timeframe}", summary="Latest signal for a symbol/timeframe pair")
async def latest_by_pair(symbol: str, timeframe: str):
    signal = _repo.get_latest(symbol, timeframe)
    if signal is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal
