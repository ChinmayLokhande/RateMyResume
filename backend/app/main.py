import logging

import redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1 import admin, analysis, dashboard, me, resume
from app.core.config import get_settings
from app.core.middleware import BodySizeLimitMiddleware, SecurityHeadersMiddleware
from app.db.session import engine

logger = logging.getLogger(__name__)
settings = get_settings()
is_production = settings.app_env == "production"

app = FastAPI(
    title="RateMyResume API",
    version="0.1.0",
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json",
)

# The last middleware added is the outermost, so CORS wraps everything. That way even
# a 413 response carries CORS headers and the browser shows the real error.
app.add_middleware(
    BodySizeLimitMiddleware,
    upload_limit=settings.max_upload_request_bytes,
    default_limit=settings.max_json_request_bytes,
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(me.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(resume.router, prefix="/api/v1")
app.include_router(analysis.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")


def _check_database() -> str:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        logger.exception("Database health check failed")
        return "unavailable"


def _check_redis() -> str:
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