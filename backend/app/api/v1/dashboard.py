from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.security import CurrentUser, require_role
from app.db.session import get_db
from app.schemas.dashboard import DashboardStats
from app.services.dashboard import get_stats
from app.services.user_service import get_or_create_profile

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(
    user: CurrentUser = Depends(require_role("user")),
    db: Session = Depends(get_db),
) -> DashboardStats:
    profile = get_or_create_profile(db, user)
    return get_stats(db, profile.id)