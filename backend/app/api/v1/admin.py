import logging
import math

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.security import CurrentUser, require_role
from app.schemas.admin import AdminUserListResponse, AdminUserOut, CreateUserRequest
from app.services import keycloak_admin
from app.services.keycloak_admin import DirectoryUser, KeycloakAdminError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])


def _out(user: DirectoryUser) -> AdminUserOut:
    return AdminUserOut(**user.__dict__)


@router.get("/ping")
def admin_ping(_: CurrentUser = Depends(require_role("admin"))) -> dict[str, str]:
    return {"status": "admin access ok"}


@router.get("/users", response_model=AdminUserListResponse)
def list_users(
    q: str | None = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: CurrentUser = Depends(require_role("admin")),
) -> AdminUserListResponse:
    try:
        users, total = keycloak_admin.list_users(q, (page - 1) * page_size, page_size)
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    return AdminUserListResponse(
        items=[_out(user) for user in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )


@router.post("/users", response_model=AdminUserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: CreateUserRequest, admin: CurrentUser = Depends(require_role("admin"))
) -> AdminUserOut:
    try:
        user = keycloak_admin.create_user(
            username=body.username,
            email=body.email,
            first_name=body.first_name,
            last_name=body.last_name,
            role=body.role,
            temporary_password=body.temporary_password.get_secret_value(),
        )
    except KeycloakAdminError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)
    logger.info("Admin %s created user %s with role %s", admin.sub, user.username, body.role)
    return _out(user)