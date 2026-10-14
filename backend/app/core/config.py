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
    cors_origins: list[str] = ["http://localhost:3000"]

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str
    postgres_user: str
    postgres_password: SecretStr

    # Redis / Celery
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_broker_db: int = 0

    # Keycloak
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "ratemyresume"
    keycloak_api_audience: str = "ratemyresume-api"
    keycloak_admin_client_id: str = "ratemyresume-admin-api"
    keycloak_admin_client_secret: SecretStr | None = None  # server-side only

    # Uploads and storage
    storage_dir: Path = PROJECT_ROOT / "storage"
    max_upload_bytes: int = 10 * 1024 * 1024
    max_bulk_files: int = 20

    # Redis cache (a separate Redis database from the Celery broker)
    cache_enabled: bool = True
    redis_cache_db: int = 1
    dashboard_cache_ttl_seconds: int = 30
    analysis_cache_ttl_seconds: int = 600

    # Request limits and rate limiting
    max_upload_request_bytes: int = 210 * 1024 * 1024  # 20 files x 10 MB plus form overhead
    max_json_request_bytes: int = 1024 * 1024
    rate_limit_enabled: bool = True

    # Local LLM (set LLM_ENABLED=false in .env for regex-only mode)
    llm_enabled: bool = True
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_timeout_seconds: float = 120.0

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

    @property
    def celery_broker_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_broker_db}"


@lru_cache
def get_settings() -> Settings:
    return Settings()