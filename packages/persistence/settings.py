"""L0 system settings (DS-06). Seeded idempotently; secrets never stored."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.persistence.models import SystemSetting

L0_SETTINGS: dict[str, tuple[object, str]] = {
    "release_level": ("L0", "PRD s.3.4 delivery tier; L1 requires expert + security gates"),
    "jurisdiction_package": (
        {"jurisdiction": "HK", "package": "fsie"},
        "The single deep MVP package in L0",
    ),
    "legal_coverage_cutoff": (
        "2026-09-01",
        "source_manifest legal coverage cutoff; later changes go through drift review",
    ),
    "research_watermark_required": (
        True,
        "Hard-coded in the renderer; this setting documents the policy, it cannot switch it off",
    ),
    "professional_validation": (
        {"status": "no_expert", "validator_enforced": True},
        "Contract validator refuses verified rules/sources until the expert machinery exists",
    ),
    "model_adapter": (
        {"wire": "openai-compatible", "credentials": "env:FSIE_MODEL_*", "l0_data_policy": "synthetic-only"},
        "Vendor-neutral adapter; D-002: only synthetic data may reach any model in L0",
    ),
}


def seed_system_settings(session: Session) -> int:
    written = 0
    for key, (value, description) in L0_SETTINGS.items():
        existing = session.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        ).scalar_one_or_none()
        if existing is None:
            session.add(SystemSetting(key=key, value=value, description=description))
            written += 1
        else:
            existing.value = value
            existing.description = description
    session.flush()
    return written
