# PostgreSQL catalog transaction test gate

The catalog executor tests now run against SQLite and a dedicated local PostgreSQL
database. PostgreSQL cases cover successful atomic row/revision publication,
stale row and revision rejection, preflight rejection, rollback after a database
constraint failure, rollback after postflight rejection, and exclusion of a
competing writer (SQLSTATE 55P03). The fixture refuses nonlocal databases and any
database name other than `catalog_executor_test`; existing catalog schemas are
not reused.

CI provisions PostgreSQL 16 in an isolated service and explicitly selects the
seven PostgreSQL cases. This is a test gate, not a production migration job.

Validation on 2026-11-18:

- Executor and migration test modules: 33 passed, 8 skipped.
- PostgreSQL selection: 7 cases collected, 7 SQLite cases deselected.
- Targeted diff whitespace check passed.
- Local PostgreSQL execution remains unverified: no dedicated server was
  configured. The seven PostgreSQL cases were skipped, not passed.
- Remote CI has not run for this change. Production catalog migration and
  deployed-reader verification remain outstanding.

Neither this gate nor SQLite transaction tests prove PostgreSQL runtime behavior
or legal-source admission. Existing publication preconditions still apply.
