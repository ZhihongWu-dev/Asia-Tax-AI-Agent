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
feature. Server case creation itself still has the existing non-idempotent API:
a connection loss after creation commits but before its response arrives can
leave an empty server case. No stronger guarantee is claimed for that boundary.

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
