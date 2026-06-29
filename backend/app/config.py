"""Application settings — a single, validated source of configuration.

All configuration is read from the environment (12-factor) and validated once at
startup by pydantic-settings. Field names map case-insensitively to env vars, so
`JWT_SECRET` populates `jwt_secret`, `DATABASE_URL` populates `database_url`, etc.

`get_settings()` is cached so the env is parsed exactly once per process; tests
override individual values by clearing the cache and re-instantiating.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Core ──────────────────────────────────────────────────────────────────
    app_name: str = "Konstanta API"
    environment: str = "development"  # development | production | test
    debug: bool = False

    # ── Database ──────────────────────────────────────────────────────────────
    # Async SQLAlchemy URL. PostgreSQL (asyncpg) in production/docker-compose;
    # SQLite (aiosqlite) is used by the test suite (see tests/conftest.py).
    database_url: str = (
        "postgresql+asyncpg://konstanta:konstanta@localhost:5432/konstanta"
    )

    # ── Auth (JWT) ────────────────────────────────────────────────────────────
    jwt_secret: str = "change-me-in-production"
    jwt_alg: str = "HS256"
    staff_ttl_seconds: int = 8 * 3600
    candidate_ttl_seconds: int = 24 * 3600
    google_client_id: str | None = None

    # ── CORS ──────────────────────────────────────────────────────────────────
    allowed_origins: str = (
        "http://localhost:8000,http://127.0.0.1:5500,http://localhost:5500"
    )

    # ── Telegram bot (in-process; disabled when bot_token is unset) ───────────
    bot_token: str | None = None
    bot_provision_secret: str | None = None
    public_url: str = ""

    # ── AI assistant ──────────────────────────────────────────────────────────
    ai_provider: str = "openai"  # "openai" | "gemini"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # ── Email (Brevo transactional API) ───────────────────────────────────────
    brevo_api_key: str = ""
    mail_from: str = ""
    mail_from_name: str = "Konstanta"

    # ── Object storage (Cloudflare R2 / any S3-compatible) ────────────────────
    r2_endpoint: str | None = None
    r2_key: str | None = None
    r2_secret: str | None = None
    r2_bucket: str | None = None
    r2_public_url: str = ""

    # ── Derived helpers ───────────────────────────────────────────────────────
    @property
    def origins(self) -> list[str]:
        """CORS origin list, trimmed and without trailing slashes."""
        return [o.strip().rstrip("/") for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def public_base_url(self) -> str:
        """PUBLIC_URL normalized to an https origin (Koyeb may inject a bare host)."""
        url = (self.public_url or "").strip().rstrip("/")
        if url and not url.startswith(("http://", "https://")):
            url = "https://" + url
        return url

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def storage_configured(self) -> bool:
        return all([self.r2_endpoint, self.r2_key, self.r2_secret, self.r2_bucket, self.r2_public_url])


@lru_cache
def get_settings() -> Settings:
    """Process-wide settings singleton (env parsed once)."""
    return Settings()
