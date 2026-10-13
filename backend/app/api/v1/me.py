from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.schemas.user import MeResponse
from app.services.user_service import get_or_create_profile

router = APIRouter(tags=["users"])


@router.get("/me", response_model=MeResponse)
def read_me(
    user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)
) -> MeResponse:
    profile = get_or_create_profile(db, user)
    return MeResponse(
        id=profile.id,
        keycloak_sub=profile.keycloak_sub,
        username=user.username,
        email=profile.email,
        display_name=profile.display_name,
        roles=sorted(user.roles & {"admin", "user"}),
    )