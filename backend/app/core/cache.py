import json
import logging
import uuid
from functools import lru_cache
from typing import Any

import redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
KEY_VERSION = "v1"  # bump to invalidate every old entry at once


@lru_cache
def _client() -> redis.Redis | None:
    settings = get_settings()
    if not settings.cache_enabled:
        return None
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=settings.redis_cache_db,
        socket_connect_timeout=1,
        socket_timeout=1,
        decode_responses=True,
    )


def dashboard_key(owner_id: uuid.UUID) -> str:
    return f"{KEY_VERSION}:dashboard:{owner_id}"


def analysis_key(owner_id: uuid.UUID, resume_id: uuid.UUID) -> str:
    return f"{KEY_VERSION}:analysis:{owner_id}:{resume_id}"


# Every function below is fail-open: a cache problem is logged and treated as a miss.
def cache_get(key: str) -> Any | None:
    client = _client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        return None if raw is None else json.loads(raw)
    except (redis.RedisError, ValueError):
        logger.warning("Cache read failed")
        return None


def cache_set(key: str, value: Any, ttl_seconds: int) -> None:
    client = _client()
    if client is None:
        return
    try:
        client.set(key, json.dumps(value), ex=ttl_seconds)
    except (redis.RedisError, TypeError, ValueError):
        logger.warning("Cache write failed")


def cache_delete(*keys: str) -> None:
    client = _client()
    if client is None:
        return
    try:
        client.delete(*keys)
    except redis.RedisError:
        logger.warning("Cache delete failed")