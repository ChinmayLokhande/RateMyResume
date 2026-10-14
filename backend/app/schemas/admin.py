from typing import Literal

from pydantic import BaseModel, EmailStr, Field, SecretStr, field_validator


class AdminUserOut(BaseModel):
    id: str
    username: str
    email: str | None
    first_name: str | None
    last_name: str | None
    enabled: bool
    roles: list[str]


class AdminUserListResponse(BaseModel):
    items: list[AdminUserOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9._-]+$")
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    role: Literal["user", "admin"]
    temporary_password: SecretStr

    @field_validator("temporary_password")
    @classmethod
    def password_length(cls, value: SecretStr) -> SecretStr:
        if not 12 <= len(value.get_secret_value()) <= 128:
            raise ValueError("Password must be 12 to 128 characters")
        return value