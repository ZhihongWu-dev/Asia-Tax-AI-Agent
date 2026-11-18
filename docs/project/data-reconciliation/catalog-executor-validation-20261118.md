# Catalog transaction executor — local validation

Added scripts/catalog_executor.py as an explicit library function, not an
automatic deploy command. It owns a SERIALIZABLE transaction, locks the target
PostgreSQL catalogs and source-review table, checks the upload/revision and every
expected original row, performs bound SQLAlchemy writes, verifies exact target
rows, updates catalog_revision, and requires before/after validation callbacks
to return True. Any exception rolls back the entire transaction.

The existing reviewed-plan validation remains the input boundary. The executor
requires complete target columns and preserves uploaded_at and unrelated rows.
Caller validators must still prove deployed-reader compatibility, source review,
complete reference closure and other execution conditions in the migration plan.
No default validator or production CLI is provided.

Local SQLite transaction tests exercise real inserts/updates and rollback:
successful row/revision commit; stale before-row; stale revision; preflight
rejection; constraint failure after an earlier write; postflight rejection after
both data and revision writes. Together with migration tests,33 tests passed.
SQLite's BEGIN IMMEDIATE is only a local-test equivalent for writer exclusion.
PostgreSQL table locks, serialization races and actual hosted privileges still
require PostgreSQL acceptance before live use. No cloud writes were performed.

Implementation reference: SQLAlchemy's own begin-once transaction documentation,
https://github.com/sqlalchemy/sqlalchemy/blob/main/doc/build/core/connections.rst .
The existing SQLAlchemy dependency is reused; no external code was copied.
