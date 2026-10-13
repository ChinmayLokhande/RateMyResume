from fastapi import APIRouter, Depends

from app.auth.security import CurrentUser, require_role

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/ping")
def admin_ping(_: CurrentUser = Depends(require_role("admin"))) -> dict[str, str]:
    return {"status": "admin access ok"}