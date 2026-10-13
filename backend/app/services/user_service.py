from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.security import CurrentUser
from app.models import UserProfile


def get_or_create_profile(db: Session, user: CurrentUser) -> UserProfile:
    query = select(UserProfile).where(UserProfile.keycloak_sub == user.sub)
    profile = db.scalar(query)
    if profile is not None:
        return profile

    profile = UserProfile(
        keycloak_sub=user.sub, email=user.email, display_name=user.display_name
    )
    db.add(profile)
    try:
        db.commit()
    except IntegrityError:
        # Two first requests raced; the other one won, so load its row
        db.rollback()
        return db.scalars(query).one()
    db.refresh(profile)
    return profile