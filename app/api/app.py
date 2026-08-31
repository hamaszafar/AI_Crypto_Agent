"""FastAPI application exposing signal and health endpoints.

The API is intentionally lightweight – it uses the existing
``SignalRepository`` for data access and provides JSON responses.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.api.routes.signals import router as signals_router
from app.api.routes.health import router as health_router

app = FastAPI(title="Trading Signal Agent API", version="0.1.0")

app.include_router(signals_router)
app.include_router(health_router)
