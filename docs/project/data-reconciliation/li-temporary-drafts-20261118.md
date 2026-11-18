# Temporary chat drafts integrated

The workspace now starts with a local temporary case when the account has no
stored cases. New chat reuses an existing temporary case, preserving its text,
rather than accumulating empty server cases or discarding the current draft.
Temporary IDs are not written into the URL. Removing the last stored case
returns to a local temporary case.

First send creates the server case before sending. A stable composer identity
survives the temporary-to-server ID transition so attachment state is retained.
Draft text, entry hints, working/error identity and retry identity move to the
server case. A failed model request can be retried without creating another
case. Renaming/archiving also materializes a temporary case. The existing
income and structure editors require a persisted UUID, so entering those panels
materializes the case before rendering their forms. Source browsing does not.

This is an in-memory unsent draft, not a durable browser-restart recovery
feature. The follow-up creation-receipt change closes the response-loss boundary:
the temporary UUID is sent as an owner-scoped request ID, and retries reuse the
stored case without resetting edits. Minimal creation receipts survive deletion
so a delayed retry cannot recreate a removed case. Legacy clients omitting the
request ID retain the original create-new behavior.

Migration 0007 adds the backend-only receipt table and denies direct Data API
access. Its downgrade preserves receipts and row-level security. It has not been
applied to the hosted database. Seven real PostgreSQL tests passed locally in
12.47 seconds, including both deletion/enqueue races, concurrent creation,
owner isolation, deleted-case replay and upgrade/downgrade/adoption. Four browser
draft tests passed in 30.7 seconds, including a committed creation whose HTTP
response was deliberately discarded. Six focused creation/deletion tests passed
in 7.23 seconds. Existing CI includes the new PostgreSQL checks.

The follow-up research inspected CPython's uuid implementation/tests as an
available standard-library reference. A stateless deterministic case ID alone
was not adopted because it cannot distinguish a deleted case from an uncreated
one. No dependency, external implementation or asset was added.

Validation: 10 browser tests passed across draft startup/first-send failure,
deletion and all attachment formats. Six follow-up browser tests passed,
including panel materialization, personal income detail save/reload, existing
case/draft isolation and preservation of a new draft during failed-send retry.
Production build passed; the pre-existing large JavaScript chunk warning remains.

References inspected before implementing: upstream Li commit
140a9efa53a4bce3f2899a20edfa77be8ec55e8b's temporary-case hook and React's official
state-preservation documentation, including its GitHub source. No new library
or external code was adopted. The stable composer key follows React's documented
identity behavior while preserving the current application's richer case shape.

- https://react.dev/learn/preserving-and-resetting-state
- https://github.com/reactjs/react.dev/blob/main/src/content/learn/preserving-and-resetting-state.md
