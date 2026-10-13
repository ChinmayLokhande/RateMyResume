import logging
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.core.config import get_settings

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    sub: str
    username: str | None
    email: str | None
    display_name: str | None
    roles: frozenset[str]


@lru_cache
def _jwks_client() -> PyJWKClient:
    # Fetches and caches Keycloak's public signing keys
    return PyJWKClient(get_settings().keycloak_jwks_url)


def _unauthorized(detail: str = "Invalid or expired token") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise _unauthorized("Missing bearer token")

    settings = get_settings()
    token = credentials.credentials
    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.keycloak_api_audience,
            issuer=settings.keycloak_issuer,
            options={"require": ["exp", "iss", "sub", "aud"]},
        )
    except jwt.PyJWKClientConnectionError:
        logger.error("Could not reach Keycloak to fetch signing keys")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )
    except jwt.PyJWTError:
        logger.warning("Token validation failed")
        raise _unauthorized()

    return CurrentUser(
        sub=claims["sub"],
        username=claims.get("preferred_username"),
        email=claims.get("email"),
        display_name=claims.get("name") or claims.get("preferred_username"),
        roles=frozenset(claims.get("realm_access", {}).get("roles", [])),
    )


def require_role(role: str):
    """Dependency factory: allow only users holding the given realm role."""

    def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if role not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return checker