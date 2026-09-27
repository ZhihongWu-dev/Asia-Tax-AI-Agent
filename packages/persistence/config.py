"""Runtime configuration.

Values come from environment variables (prefix FSIE_) or an optional local .env.
No secrets are committed; .env is git-ignored, .env.example is the template.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from pydantic import field_validator

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Deployment must explicitly configure its database; no local fallback.
    database_url: str = ""

    @field_validator('database_url')
    @classmethod
    def psycopg_url(cls, value: str) -> str:
        if value.startswith('postgresql://'):
            return value.replace('postgresql://', 'postgresql+psycopg://', 1)
        return value

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / '.env',
        env_prefix="FSIE_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
