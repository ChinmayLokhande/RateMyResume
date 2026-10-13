import logging
import redis
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine
from app.api.v1 import admin, me, resume



logger = logging.getLogger(__name__)

# 1. Define the app instance FIRST
app = FastAPI(title="RateMyResume API", version="0.1.0")

# 2. THEN include your routers
app.include_router(me.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(resume.router, prefix="/api/v1")


def _check_database() -> str:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        logger.exception("Database health check failed")
        return "unavailable"


def _check_redis() -> str:
    settings = get_settings()
    try:
        client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            socket_connect_timeout=2,
        )
        client.ping()
        return "ok"
    except Exception:
        logger.exception("Redis health check failed")
        return "unavailable"


@app.get("/health")
def health() -> JSONResponse:
    checks = {"database": _check_database(), "redis": _check_redis()}
    healthy = all(result == "ok" for result in checks.values())
    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ok" if healthy else "degraded", "checks": checks},
    )