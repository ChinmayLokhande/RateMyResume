import logging
import time
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class KeycloakAdminError(Exception):
    """A failed call to Keycloak. The message is safe to show to the admin."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class UserAlreadyExists(KeycloakAdminError):
    def __init__(self) -> None:
        super().__init__("A user with that username or email already exists", 409)


@dataclass(frozen=True)
class DirectoryUser:
    id: str
    username: str
    email: str | None
    first_name: str | None
    last_name: str | None
    enabled: bool
    roles: list[str]


_token: tuple[str, float] | None = None  # (access token, expiry time)


def _admin_base() -> str:
    settings = get_settings()
    return f"{settings.keycloak_url}/admin/realms/{settings.keycloak_realm}"


def _service_token(client: httpx.Client) -> str:
    global _token
    if _token and _token[1] > time.time() + 30:
        return _token[0]
    settings = get_settings()
    if settings.keycloak_admin_client_secret is None:
        raise KeycloakAdminError("User administration is not configured", 503)
    response = client.post(
        f"{settings.keycloak_issuer}/protocol/openid-connect/token",
        data={
            "grant_type": "client_credentials",
            "client_id": settings.keycloak_admin_client_id,
            "client_secret": settings.keycloak_admin_client_secret.get_secret_value(),
        },
    )
    if response.status_code != 200:
        logger.error("Keycloak service-account login failed with status %s", response.status_code)
        raise KeycloakAdminError("Could not sign in to the user directory", 502)
    body = response.json()
    _token = (body["access_token"], time.time() + float(body.get("expires_in", 60)))
    return _token[0]


def _request(method: str, path: str, *, expected: tuple[int, ...], **kwargs) -> httpx.Response:
    global _token
    try:
        with httpx.Client(timeout=10) as client:
            headers = {"Authorization": f"Bearer {_service_token(client)}"}
            response = client.request(method, f"{_admin_base()}{path}", headers=headers, **kwargs)
    except httpx.HTTPError as exc:
        logger.error("Keycloak admin request failed: %s", type(exc).__name__)
        raise KeycloakAdminError("The user directory is unavailable", 503) from exc
    if response.status_code == 401:
        _token = None  # force a fresh login next time
    if response.status_code not in expected:
        logger.error("Keycloak %s %s returned %s", method, path.split("?")[0], response.status_code)
        raise KeycloakAdminError("The user directory rejected the request", 502)
    return response


def _role_member_ids(role: str) -> set[str]:
    members = _request("GET", f"/roles/{role}/users", expected=(200,), params={"max": 1000}).json()
    return {member["id"] for member in members}


def list_users(search: str | None, first: int, limit: int) -> tuple[list[DirectoryUser], int]:
    params: dict[str, str | int] = {"first": first, "max": limit, "briefRepresentation": "true"}
    count_params: dict[str, str] = {}
    if search:
        params["search"] = search
        count_params["search"] = search
    users = _request("GET", "/users", expected=(200,), params=params).json()
    total = int(_request("GET", "/users/count", expected=(200,), params=count_params).json())
    admins, regular = _role_member_ids("admin"), _role_member_ids("user")
    return (
        [
            DirectoryUser(
                id=user["id"],
                username=user["username"],
                email=user.get("email"),
                first_name=user.get("firstName"),
                last_name=user.get("lastName"),
                enabled=user.get("enabled", False),
                roles=[r for r, ids in (("admin", admins), ("user", regular)) if user["id"] in ids],
            )
            for user in users
        ],
        total,
    )


def create_user(
    *, username: str, email: str, first_name: str, last_name: str, role: str, temporary_password: str
) -> DirectoryUser:
    payload = {
        "username": username,
        "email": email,
        "firstName": first_name,
        "lastName": last_name,
        "enabled": True,
        "emailVerified": True,
        "credentials": [{"type": "password", "value": temporary_password, "temporary": True}],
    }
    response = _request("POST", "/users", expected=(201, 409), json=payload)
    if response.status_code == 409:
        raise UserAlreadyExists
    user_id = response.headers["Location"].rsplit("/", 1)[-1]
    try:
        role_representation = _request("GET", f"/roles/{role}", expected=(200,)).json()
        _request(
            "POST", f"/users/{user_id}/role-mappings/realm", expected=(204,), json=[role_representation]
        )
    except KeycloakAdminError:
        try:  # never leave a user behind without a role
            _request("DELETE", f"/users/{user_id}", expected=(204,))
        except KeycloakAdminError:
            logger.error("Could not roll back partially created user %s", user_id)
        raise
    return DirectoryUser(user_id, username, email, first_name, last_name, True, [role])