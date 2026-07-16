"""FastAPI application entrypoint.

Wires configuration, CORS, structured request logging, a global error handler that hides
internals behind a correlation id, and the four routers. The OpenAPI schema is generated
automatically and served at ``/docs``.
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import admin_router, asset_router, auth_router, game_router, save_router
from .config import get_settings
from .db import init_db

logging.basicConfig(
    level=logging.INFO,
    format='{"level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
)
logger = logging.getLogger("voidfall")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    logger.info("VOIDFALL backend started")
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="VOIDFALL",
        description="A Natural Language RPG Engine with an authoritative deterministic core.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def correlate_and_log(request: Request, call_next):
        correlation_id = uuid.uuid4().hex[:12]
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed = (time.perf_counter() - started) * 1000
            logger.exception(
                "unhandled error cid=%s %s %s in %.1fms",
                correlation_id, request.method, request.url.path, elapsed,
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "correlation_id": correlation_id},
            )
        elapsed = (time.perf_counter() - started) * 1000
        logger.info(
            "cid=%s %s %s -> %s in %.1fms",
            correlation_id, request.method, request.url.path, response.status_code, elapsed,
        )
        response.headers["X-Correlation-ID"] = correlation_id
        return response

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.environment}

    app.include_router(auth_router)
    app.include_router(game_router)
    app.include_router(save_router)
    app.include_router(admin_router)
    app.include_router(asset_router)
    return app


app = create_app()
