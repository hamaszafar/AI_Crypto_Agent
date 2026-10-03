"""FastAPI application exposing signal and health endpoints.

The API is intentionally lightweight – it uses the existing
``SignalRepository`` for data access and provides JSON responses.
"""

from __future__ import annotations

import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from app.api.routes.signals import router as signals_router
from app.api.routes.health import router as health_router
from app.core.metrics import API_REQUESTS, REQUEST_LATENCY
from app.core.logging import setup_logging
from app.core.exceptions import TradingSignalException, ValidationError

setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    import app.api.routes.signals as signals_module
    try:
        # Re-initialize for test isolation
        signals_module._repo = type(signals_module._repo)()
        _repo = signals_module._repo
        # Check SQLite DB readiness
        _repo._db.connection.execute("SELECT 1").fetchone()
        logger.info("SignalRepository initialized successfully on startup.")
    except Exception as e:
        logger.critical(f"Failed to initialize SignalRepository during startup: {e}")
        raise RuntimeError(f"Startup dependency failure: {e}") from e

    yield

    try:
        _repo.close()
        logger.info("SignalRepository closed successfully on shutdown.")
    except Exception as e:
        logger.error(f"Error closing SignalRepository on shutdown: {e}")

app = FastAPI(title="Trading Signal Agent API", version="0.1.0", lifespan=lifespan)

@app.exception_handler(TradingSignalException)
async def trading_signal_exception_handler(request: Request, exc: TradingSignalException):
    logger.error(f"Application error: {exc.message}", exc_info=exc.original_exception or exc)
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(exc, ValidationError):
        status_code = status.HTTP_400_BAD_REQUEST
    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message}
    )

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    if request.url.path != "/metrics":
        method = request.method
        endpoint = request.url.path
        status_code = str(response.status_code)
        
        API_REQUESTS.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)
        
    return response

app.include_router(signals_router)
app.include_router(health_router)
