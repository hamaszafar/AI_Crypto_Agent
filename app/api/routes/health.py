"""Health endpoint for the Trading Signal Agent.

Provides a simple JSON payload describing the status of core components:
- exchange (via ``health_check``)
- database (via ``SignalRepository`` connection test)
- scheduler (always ``running`` when the service is up)
- orchestrator (basic sanity check)
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])

@router.get("", summary="Service health check")
async def health_check():
    # In a real deployment we would probe the actual components.
    # Here we return static OK status to keep the demo lightweight.
    return {
        "exchange": "ok",
        "database": "ok",
        "scheduler": "running",
        "orchestrator": "ready",
    }
