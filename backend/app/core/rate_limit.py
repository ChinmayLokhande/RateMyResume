from fastapi import Depends, HTTPException

from app.auth.security import CurrentUser, get_current_user
from app.core.cache import KEY_VERSION, rate_limit_hit
from app.core.config import get_settings


def rate_limit(name: str, limit: int, window_seconds: int):
    """Dependency factory: at most `limit` calls per user per window. Fails open if Redis is down."""

    def dependency(user: CurrentUser = Depends(get_current_user)) -> None:
        if not get_settings().rate_limit_enabled:
            return
        result = rate_limit_hit(f"{KEY_VERSION}:rl:{name}:{user.sub}", window_seconds)
        if result is None:
            return
        count, seconds_left = result
        if count > limit:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please slow down and try again shortly.",
                headers={"Retry-After": str(max(seconds_left, 1))},
            )

    return dependency