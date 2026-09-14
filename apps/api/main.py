"""Minimal FastAPI application shell for the L0 walking skeleton.

S1 only exposes a health/readiness probe; interview, case and report endpoints
are added by later slices.
"""

from __future__ import annotations

from fastapi import FastAPI

from packages.persistence.config import get_settings

app = FastAPI(title="Asia Tax AI Agent — HK FSIE L0", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "release_level": "L0", "database": get_settings().database_url}
