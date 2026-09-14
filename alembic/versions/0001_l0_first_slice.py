"""L0 first-slice baseline schema

Revision ID: 0001_l0_first_slice
Revises:
Create Date: 2026-09-02

Baseline decision: this initial migration materialises the schema directly from
the SQLAlchemy metadata (the single structural source of truth translated from
packages/contracts). It also enables the pgvector extension so later legal-passage
migrations do not have to recreate the database. Later, incremental schema
changes must be explicit migrations (preferably autogenerate + manual review),
not edits to this baseline.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from packages.persistence.base import Base
from packages.persistence import models  # noqa: F401  (register every table)

revision: str = "0001_l0_first_slice"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
    op.execute("DROP EXTENSION IF EXISTS vector")
