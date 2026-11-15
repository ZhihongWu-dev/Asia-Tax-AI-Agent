# Taxrora data and workflow integration design

## Outcome

The existing Taxrora account and chat remain the single product. A signed-in user can start a separate planning run from one of their cases, inspect its progress, and receive a report whose factual claims and legal citations resolve to a pinned library version. The current research chat remains available throughout rollout.

## Data boundary

The cloud `database` schema is the current Li library (38,152 clauses and 287 documents at the 2026-11-13 upload). `public.sources` and `public.legal_units` serve the existing research chat and are not automatically synchronized. The 107 clause IDs found only in `main` are absent from the Li cloud schema. The 25 shared IDs with different Git rows require source and effective-date review.

Keep `database` private and read it only from the backend through a read-only database role. Do not expose it directly through Supabase Data API. Do not rerun Li's destructive upload script during integration. The database is already about 404 MB, so avoid a full duplicate schema. Maintain a small, versioned overlay for accepted main-only records and amendments. Every read records the base library upload identifier and overlay revision; reject a run if the base upload changes unexpectedly. Publish an overlay row only after its document metadata, original source, applicability period, and citation have been checked. Store user cases separately from public law material.

## Application boundary

Keep `apps/api/main.py`, Supabase Auth, cloud case ownership, and the current frontend as the only production entry point. Adapt Li's planner as a separate backend service module behind the authenticated API, never launch its standalone local-user web host. Give each planning run an owner, case ID, immutable input snapshot, source version, status, events, and report artifact. Persist state in cloud storage so a Render restart or browser refresh cannot silently lose or reassign a run. Use bounded execution and explicit failure states; do not rely on an in-process child surviving Render sleep.

The frontend adds a planning view within the signed-in workspace. It reuses the current account and case list. The user can still send ordinary chat messages; starting a planning run is an explicit action. Planning progress and citations are displayed from server state. Never silently promote unconfirmed chat statements into confirmed case facts.

## Acceptance

1. The 107 main-only citations and all accepted Li additions resolve against the unified read layer; unresolved 25 conflicts remain flagged and cannot be silently selected.
2. Every enabled rule citation resolves to a document and source version; golden tests and representative cross-border cases pass.
3. Two accounts cannot read or change each other's cases, runs, or reports.
4. Restarting the web service during a run preserves a resumable, truthful status; a failed provider or unavailable source yields a visible error, not a fabricated report.
5. Existing chat, login, and Hong Kong research tests continue to pass. The planning route is enabled on `Zhihong-Wu` first; `main` changes only after live end-to-end validation.
