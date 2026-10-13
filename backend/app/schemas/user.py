import uuid

from pydantic import BaseModel


class MeResponse(BaseModel):
    id: uuid.UUID
    keycloak_sub: str
    username: str | None
    email: str | None
    display_name: str | None
    roles: list[str]