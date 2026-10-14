import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cache import cache_get, cache_set, dashboard_key
from app.core.config import get_settings
from app.models import Resume
from app.schemas.dashboard import DashboardStats
from app.schemas.resume import ResumeSummary

RECENT_LIMIT = 5
COUNT_KEYS = ("total", "completed", "in_progress", "failed")


def _counts(db: Session, owner_id: uuid.UUID) -> dict[str, int]:
    key = dashboard_key(owner_id)
    cached = cache_get(key)
    if isinstance(cached, dict) and all(isinstance(cached.get(k), int) for k in COUNT_KEYS):
        return {k: cached[k] for k in COUNT_KEYS}

    total, completed, in_progress, failed = db.execute(
        select(
            func.count(),
            func.count().filter(Resume.extraction_status == "completed"),
            func.count().filter(Resume.extraction_status.in_(("queued", "processing"))),
            func.count().filter(Resume.extraction_status == "failed"),
        ).where(Resume.owner_id == owner_id)
    ).one()
    counts = {
        "total": total,
        "completed": completed,
        "in_progress": in_progress,
        "failed": failed,
    }
    cache_set(key, counts, get_settings().dashboard_cache_ttl_seconds)
    return counts


def get_stats(db: Session, owner_id: uuid.UUID) -> DashboardStats:
    counts = _counts(db, owner_id)
    # The recent list contains names and emails, so it is never cached
    recent = db.scalars(
        select(Resume)
        .where(Resume.owner_id == owner_id)
        .order_by(Resume.uploaded_at.desc(), Resume.id)
        .limit(RECENT_LIMIT)
    ).all()
    return DashboardStats(**counts, recent=[ResumeSummary.model_validate(row) for row in recent])