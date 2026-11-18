# Li case deletion integration

Adapted the deletion feature observed in upstream commit
140a9efa53a4bce3f2899a20edfa77be8ec55e8b to the existing authenticated API.
Deletion checks owner and expected revision, locks the case, and deletes both
the chat document and its durable planning jobs in one transaction. Income
workpapers and messages embedded in the document are removed with it. Late
worker writes lose their lease; late chat saves cannot recreate the case.
Planner enqueue now locks its selected case row to serialize PostgreSQL
enqueue against deletion. No production records were deleted.

The sidebar has a bilingual delete action and explicit irreversible-action
confirmation. Cancellation preserves the case. Revision conflicts preserve the
case, refresh its server state and show failure. A lost successful response may
be retried: a subsequent owner-scoped 404 removes the already absent local case.
Deleting the last case currently creates a new empty case, matching existing
initialization. Li's temporary unsaved case behavior remains to integrate.

Validation: 13 deletion/planning-store tests passed (SQLite), covering owner and
revision guards, associated-job removal, rollback after injected failure,
worker fencing, and the API. Two browser tests passed for cancellation,
confirmed deletion/reload and revision conflict. Production frontend build
passed with the existing large-bundle warning. PostgreSQL concurrency testing
of this new case-lock interaction and hosted acceptance remain outstanding.

Research before implementation: inspected Li's hook and the FastAPI official
template's ownership and associated-record deletion examples. Reviewed its
MIT license, release notes and issues page (no open results displayed).
No third-party dependency or template code was copied. The template uses
SQLModel; this implementation retains the application's SQLAlchemy Core tables.

- https://github.com/fastapi/full-stack-fastapi-template/blob/master/backend/app/api/routes/users.py
- https://github.com/fastapi/full-stack-fastapi-template/blob/master/LICENSE
- https://github.com/fastapi/full-stack-fastapi-template/releases
- https://github.com/fastapi/full-stack-fastapi-template/issues
