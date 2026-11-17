"""Durable backend-only planning jobs. Downgrades retain records and RLS."""
from alembic import op

revision = "0006_planning_runs"
down_revision = "0005_source_catalog_metadata"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("\nCREATE TABLE IF NOT EXISTS planning_runs (\n\tid VARCHAR(36) NOT NULL, \n\towner VARCHAR(64) NOT NULL, \n\tcase_id VARCHAR(36) NOT NULL, \n\tcase_revision INTEGER NOT NULL, \n\trequest_id VARCHAR(64) NOT NULL, \n\trequest_hash VARCHAR(64) NOT NULL, \n\tinput JSON NOT NULL, \n\tlibrary_snapshot JSON NOT NULL, \n\truntime_snapshot JSON NOT NULL, \n\tcase_snapshot JSON NOT NULL, \n\tstatus VARCHAR(16) NOT NULL, \n\tattempts INTEGER NOT NULL, \n\tlease_token VARCHAR(36), \n\tlease_until FLOAT, \n\tcreated_at FLOAT NOT NULL, \n\tupdated_at FLOAT NOT NULL, \n\tresult JSON, \n\terror VARCHAR(80), \n\tevents JSON NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT planning_runs_owner_request UNIQUE (owner, request_id), \n\tCONSTRAINT planning_runs_status CHECK (status IN ('queued', 'running', 'succeeded', 'failed')), \n\tCONSTRAINT planning_runs_attempts CHECK (attempts >= 0), \n\tCONSTRAINT planning_runs_lease CHECK ((status = 'running' AND lease_token IS NOT NULL AND lease_until IS NOT NULL) OR (status <> 'running' AND lease_token IS NULL AND lease_until IS NULL))\n)\n\n")
    op.execute('CREATE INDEX IF NOT EXISTS planning_runs_claim ON planning_runs (status, lease_until, created_at)')
    op.execute('CREATE INDEX IF NOT EXISTS planning_runs_owner_case ON planning_runs (owner, case_id, created_at)')
    op.execute('ALTER TABLE planning_runs ENABLE ROW LEVEL SECURITY')
    op.execute('REVOKE ALL ON TABLE planning_runs FROM PUBLIC')
    op.execute("DO $$ DECLARE r text; BEGIN FOREACH r IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname=r) THEN EXECUTE format('REVOKE ALL ON TABLE planning_runs FROM %I',r); END IF; END LOOP; END $$")


def downgrade():
    # Retain queued jobs, completed evidence, and access controls.
    pass
