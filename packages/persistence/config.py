"""Runtime configuration.

Values come from environment variables (prefix FSIE_) or an optional local .env.
No secrets are committed; .env is git-ignored, .env.example is the template.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Default points at the local docker-compose PostgreSQL.
    database_url: str = "postgresql+psycopg://fsie:fsie@localhost:5432/fsie_l0"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="FSIE_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
