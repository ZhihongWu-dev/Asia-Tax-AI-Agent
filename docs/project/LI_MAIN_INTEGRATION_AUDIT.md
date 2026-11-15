# Li-to-main integration audit (2026-11-15)

This is an inventory and compatibility check, not a production merge. The integration branch starts at `main` commit `78a037f`; Li is at `9a4abd5`.

## Data and rules

The two `database/clause.csv` blobs were read by immutable Git blob SHA and parsed as CSV. `main` has 6,037 clause records, and Li has approximately 37,627 data records (plus a BOM-prefixed header). The comparison found 107 IDs present only on `main`, approximately 31,697 present only on Li, and 25 shared IDs with different rows. The files must be merged by ID; replacing the main table would discard records. The conflicting rows require source and effective-date review before selection.

`database/doc.csv` has 220 rows on `main` and 285 on Li, with 25 main-only IDs and 90 Li-only IDs. Those metadata rows must be reconciled with clause IDs and source files.

`rule/rule.csv` has 191 rows on `main` and 201 on Li. Li has 10 new rule IDs and changes 18 existing IDs. The 176 distinct citation IDs used in Li's rule table were present in Li's clause table in this index-level check. This does not validate legal interpretation, rate accuracy, effective dates, or executable rule tests.

## Application boundary

Keep the current production `apps/api/main.py`, Supabase auth, React chat, and Render configuration until a separate integration test passes. Li's `apps/api/server.py`, altered React workspace, Codex CLI harness, and report pipeline are a distinct runtime. Do not replace the production paths as part of a data import.

## Security and transport

Li's branch tree includes `.env` and `key.md`; neither belongs in public `main`. Historical exposure requires credential rotation independently of this merge.

The local partial-clone transport repeatedly reset or stalled when fetching Li's large `database/clause.csv` blob. The GitHub connector successfully read that blob, so the file exists and is accessible; local Git and raw-file transfer remain unverified. Do not commit a merged database or deploy until the complete files can be transferred, hashed, and tested locally.

## Remaining gates

1. Transfer and hash all relevant source tables and documents; reconcile main-only rows and shared-ID conflicts.
2. Rebuild the database and verify every rule citation and source file reference.
3. Run rule golden tests and existing main API/frontend tests.
4. Integrate Li's long-running workflow behind a separate entry point with user ownership, persisted state, and realistic Render resource tests.
5. Review the diff and merge the validated integration branch into `main`.
