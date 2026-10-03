"""Add region catalog metadata without changing existing HK source rows."""

from alembic import op
import sqlalchemy as sa


revision = "0005_source_catalog_metadata"
down_revision = "0004_cloud_chat_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sources", sa.Column("topic_tags", sa.JSON(), nullable=True))
    op.add_column("sources", sa.Column("publication_date", sa.Date(), nullable=True))
    op.add_column("sources", sa.Column("effective_from", sa.Date(), nullable=True))
    op.add_column("sources", sa.Column("effective_to", sa.Date(), nullable=True))
    op.add_column("sources", sa.Column("version_note", sa.Text(), nullable=True))
    op.add_column("sources", sa.Column("coverage_note", sa.Text(), nullable=True))
    op.create_index("ix_sources_jurisdiction", "sources", ["jurisdiction"])


def downgrade() -> None:
    op.drop_index("ix_sources_jurisdiction", table_name="sources")
    for column in ("coverage_note", "version_note", "effective_to", "effective_from", "publication_date", "topic_tags"):
        op.drop_column("sources", column)
