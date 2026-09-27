"""Cloud chat table and deny-by-default Data API access.

Only the trusted backend database owner accesses these tables. This does not
replace application authentication or organization authorization.
"""
from alembic import op
import sqlalchemy as sa

revision = '0004_cloud_chat_rls'
down_revision = '0003_system_settings'
branch_labels = None
depends_on = None

TABLES = ('rule_sets', 'rule_nodes', 'evaluation_cases', 'organizations', 'cases',
          'facts', 'fact_versions', 'rule_executions', 'evaluation_runs',
          'evaluation_results', 'audit_events', 'sources', 'legal_units',
          'system_settings', 'chat_cases')


def upgrade():
    # Adopt chat tables that earlier versions created at runtime, preserving rows.
    op.execute(sa.text('''CREATE TABLE IF NOT EXISTS chat_cases (
        id VARCHAR(36) PRIMARY KEY, owner VARCHAR(64) NOT NULL,
        revision INTEGER NOT NULL, document JSON NOT NULL
    )'''))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_chat_cases_owner ON chat_cases (owner)'))
    for table in TABLES:
        op.execute(sa.text(f'ALTER TABLE {table} ENABLE ROW LEVEL SECURITY'))


def downgrade():
    # Retain chat records and RLS on downgrade: never silently expose or erase data.
    pass
