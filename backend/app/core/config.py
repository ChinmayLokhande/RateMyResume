from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

# backend/app/core/config.py -> project root is three folders up
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )

    app_env: str = "development"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str
    postgres_user: str
    postgres_password: SecretStr

    redis_host: str = "localhost"
    redis_port: int = 6379

    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "ratemyresume"
    keycloak_api_audience: str = "ratemyresume-api"

    storage_dir: Path = PROJECT_ROOT / "storage"
    max_upload_bytes: int = 10 * 1024 * 1024
    max_bulk_files: int = 20

    @property
    def database_url(self) -> URL:
        # URL.create handles special characters in the password safely
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )

    @property
    def keycloak_issuer(self) -> str:
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}"

    @property
    def keycloak_jwks_url(self) -> str:
        return f"{self.keycloak_issuer}/protocol/openid-connect/certs"


@lru_cache
def get_settings() -> Settings:
    return Settings()