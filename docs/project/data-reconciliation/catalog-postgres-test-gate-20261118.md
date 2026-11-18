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
- Subsequent real PostgreSQL execution: **7 passed, 7 deselected in 6.77s**
  on PostgreSQL 16.16, Windows x64, loopback port 55439, in a newly initialized
  dedicated `catalog_executor_test` database. This verifies the seven PostgreSQL
  cases; it does not validate a production migration.
- Remote CI has not run for this change. Production catalog migration and
  deployed-reader verification remain outstanding.

Neither this gate nor SQLite transaction tests prove PostgreSQL runtime behavior
or legal-source admission. Existing publication preconditions still apply.

The PostgreSQL result above supplies runtime evidence for transaction rollback
and competing-writer exclusion. The server log independently records the intended
NOT NULL violation and competing-writer lock timeout. Binary download provenance:
official EDB Windows archive linked from its PostgreSQL binaries page,
`postgresql-16.16-1-windows-x64-binaries.zip`, 378078504 bytes; locally recorded
SHA-256 `5c0d06f3d26a929ecb36dd931409f1e51a4181355794a259b90aae8bffc57a9f`.
The digest records the downloaded artifact, not a vendor-signature verification.
