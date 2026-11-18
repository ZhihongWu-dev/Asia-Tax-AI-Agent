"""Backend-only creation receipts survive case deletion and request retries."""
from alembic import op

revision = '0007_chat_case_creations'
down_revision = '0006_planning_runs'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''CREATE TABLE IF NOT EXISTS chat_case_creations (
        owner VARCHAR(64) NOT NULL,
        request_id VARCHAR(36) NOT NULL,
        case_id VARCHAR(36) NOT NULL,
        PRIMARY KEY (owner, request_id)
    )''')
    op.execute('ALTER TABLE chat_case_creations ENABLE ROW LEVEL SECURITY')
    op.execute('REVOKE ALL ON TABLE chat_case_creations FROM PUBLIC')
    op.execute("DO $$ DECLARE r text; BEGIN FOREACH r IN ARRAY ARRAY['anon','authenticated','service_role'] LOOP IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname=r) THEN EXECUTE format('REVOKE ALL ON TABLE chat_case_creations FROM %I',r); END IF; END LOOP; END $$")


def downgrade():
    # Losing receipts could recreate deleted cases on delayed retries.
    pass
