# Source closure inside the migration transaction

Added `read_planning_bundle_in_transaction` to the existing source reader.
Migration postflight callbacks can now read their own uncommitted catalog and
source changes through the same admission, version, complete-passage, catalog
and automatic dependency checks as ordinary planning reads. The function does
not open, begin, commit, roll back, or change isolation on the caller's connection.
It requires an active PostgreSQL REPEATABLE READ or SERIALIZABLE transaction
and rejects DBAPI autocommit, including when SQLAlchemy still reports an active
logical transaction. Ordinary reader entry points retain their read-only
REPEATABLE READ transaction ownership.

Validation: source-reader/library tests passed 43 checks (2.68 seconds). The
dedicated local PostgreSQL executor suite passed nine tests, with nine SQLite
variants deselected (12.06 seconds). New PostgreSQL checks insert a complete
source inside an uncommitted transaction: the caller sees it, another connection
does not, and intentional rollback removes it. An inserted parameter referencing
a missing source causes validation failure and rollback of both changes. Existing
commit, stale-state, rejection, constraint, rollback and concurrent-writer checks
also passed. The local PostgreSQL server was stopped after verification.

Implementation reference: [SQLAlchemy's official connection and transaction
examples](https://github.com/sqlalchemy/sqlalchemy/blob/main/doc/build/core/connections.rst).
The project's existing dependency is reused; no external code was copied.

This supplies a missing mechanism for transactional postflight validation. It
does not establish deployed-reader compatibility, legal approval of source
changes, completion of the optimizer suite, or execution of the hosted migration.
The frozen independent rule-validation worktree was not changed.
