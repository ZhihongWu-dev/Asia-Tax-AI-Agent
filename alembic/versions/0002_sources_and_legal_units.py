"""sources and legal_units — knowledge pipeline layer (S5)

Revision ID: 0002_sources_legal_units
Revises: 0001_l0_first_slice
Create Date: 2026-09-04

Explicit incremental migration (per the 0001 baseline note): later schema
changes are deliberate DDL, not metadata snapshots.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_sources_legal_units"
down_revision: str | None = "0001_l0_first_slice"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(64), nullable=False, unique=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("publisher", sa.String(128), nullable=True),
        sa.Column("source_type", sa.String(32), nullable=True),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("structured_data_url", sa.String(1024), nullable=True),
        sa.Column("jurisdiction", sa.String(8), nullable=False, server_default="HK"),
        sa.Column("language", sa.String(8), nullable=False, server_default="en"),
        sa.Column("manifest_sha256", sa.String(64), nullable=True),
        sa.Column("actual_sha256", sa.String(64), nullable=True),
        sa.Column("content_bytes", sa.Integer(), nullable=True),
        sa.Column("content_type", sa.String(255), nullable=True),
        sa.Column("snapshot_path", sa.String(512), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("l0_in_scope", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("parse_status", sa.String(32), nullable=False, server_default="registered"),
        sa.Column("units_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("professional_validation_status", sa.String(32), nullable=False, server_default="unverified"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "parse_status IN ('failed', 'out_of_scope', 'parsed', 'registered', 'snapshotted')",
            name="ck_source_parse_status",
        ),
    )
    op.create_table(
        "legal_units",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_db_id", sa.Integer(), sa.ForeignKey("sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("unit_ref", sa.String(128), nullable=False),
        sa.Column("statute_locator", sa.String(32), nullable=True),
        sa.Column("unit_type", sa.String(32), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("heading", sa.String(512), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("text_sha256", sa.String(64), nullable=False),
        sa.Column("language", sa.String(8), nullable=False, server_default="en"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source_db_id", "unit_ref", name="uq_legal_unit_ref"),
        sa.CheckConstraint(
            "unit_type IN ('example', 'faq_item', 'guidance_block', 'pdf_page', 'ruling_block', 'section', 'subsection')",
            name="ck_legal_unit_type",
        ),
    )
    op.create_index("ix_legal_units_source_db_id", "legal_units", ["source_db_id"])
    op.create_index("ix_legal_units_statute_locator", "legal_units", ["statute_locator"])


def downgrade() -> None:
    op.drop_index("ix_legal_units_statute_locator", table_name="legal_units")
    op.drop_index("ix_legal_units_source_db_id", table_name="legal_units")
    op.drop_table("legal_units")
    op.drop_table("sources")
