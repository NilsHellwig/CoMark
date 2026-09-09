from __future__ import annotations

from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import Field, PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

_LOCAL_DB_HOSTS = {"localhost", "127.0.0.1", "::1", "postgres", "db"}
# libpq-style params that asyncpg's connect() does not accept.
_LIBPQ_ONLY_PARAMS = {"sslmode", "channel_binding", "target_session_attrs"}


def _normalize_async_dsn(url: str) -> str:
    """Make an external Postgres URL usable by SQLAlchemy's asyncpg driver.

    Neon (and most managed providers) hand out the libpq form
    ``postgres://user:pw@host/db?sslmode=require`` — rewrite the scheme to
    ``postgresql+asyncpg`` and drop query params asyncpg rejects.
    """
    parts = urlsplit(url)
    scheme = parts.scheme
    if scheme in ("postgres", "postgresql"):
        scheme = "postgresql+asyncpg"
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k not in _LIBPQ_ONLY_PARAMS
    ]
    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"
    project_name: str = "CoMark"

    # --- Security ---
    secret_key: str = "dev-secret-change-me-0123456789abcdef0123456789abcdef"
    access_token_lifetime_seconds: int = 3600
    guest_token_lifetime_seconds: int = 43_200

    # --- URLs ---
    public_base_url: str = "http://localhost:3000"
    backend_cors_origins: str = "http://localhost:3000"

    # --- PostgreSQL ---
    postgres_user: str = "comark"
    postgres_password: str = "comark"
    postgres_db: str = "comark"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    # Full override (used by tests / managed DBs). Takes precedence when set.
    database_url_override: str | None = Field(default=None, alias="DATABASE_URL")

    # --- Redis ---
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_url_override: str | None = Field(default=None, alias="REDIS_URL")

    # --- OAuth (Google) ---
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""

    # --- Collaboration ---
    collab_redis_bridge: bool = False
    collab_snapshot_debounce_seconds: float = 3.0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return _normalize_async_dsn(self.database_url_override)
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=self.postgres_user,
                password=self.postgres_password,
                host=self.postgres_host,
                port=self.postgres_port,
                path=self.postgres_db,
            )
        )

    @property
    def database_connect_args(self) -> dict[str, object]:
        """asyncpg connect kwargs — require TLS for non-local (managed) Postgres."""
        host = (urlsplit(self.database_url).hostname or "").lower()
        if host and host not in _LOCAL_DB_HOSTS:
            return {"ssl": True}
        return {}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def sync_database_url(self) -> str:
        """psycopg-free sync URL for Alembic (uses asyncpg via async engine in env.py)."""
        return self.database_url

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        if self.redis_url_override:
            return self.redis_url_override
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def google_oauth_enabled(self) -> bool:
        cid = self.google_oauth_client_id
        # "googleusercontent.com" guards against placeholder secret values
        # (e.g. "unset") used when Google login is not configured.
        return bool(cid and self.google_oauth_client_secret and "googleusercontent.com" in cid)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cookie_secure(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
