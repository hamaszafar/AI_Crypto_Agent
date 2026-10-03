"""Health endpoint for the Trading Signal Agent.

Provides a simple JSON payload describing the status of core components:
- exchange (via ``health_check``)
- database (via ``SignalRepository`` connection test)
- scheduler (always ``running`` when the service is up)
- orchestrator (basic sanity check)
"""

from __future__ import annotations

import logging
import os
from fastapi import APIRouter, Response, status
import redis

from app.signals.persistence import SignalRepository

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)

@router.get("/health", summary="Liveness probe")
async def health_check():
    """Liveness probe to verify the application process is running."""
    return {"status": "alive"}

@router.get("/ready", summary="Readiness probe")
async def ready_check(response: Response):
    """Readiness probe to verify dependencies (Database, Redis) are available."""
    dependencies = {
        "database": "down",
        "redis": "down"
    }
    is_ready = True
    
    # Check Database (SQLite via SignalRepository)
    try:
        repo = SignalRepository()
        repo._db.connection.execute("SELECT 1").fetchone()
        dependencies["database"] = "ok"
    except Exception as e:
        logger.error(f"Database readiness check failed: {e}")
        is_ready = False

    # Check Redis
    try:
        redis_host = os.environ.get("REDIS_HOST", "localhost")
        redis_port = int(os.environ.get("REDIS_PORT", "6379"))
        r = redis.Redis(host=redis_host, port=redis_port, db=0, socket_timeout=1)
        if r.ping():
            dependencies["redis"] = "ok"
    except Exception as e:
        logger.error(f"Redis readiness check failed: {e}")
        is_ready = False

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "not_ready",
        "dependencies": dependencies
    }
