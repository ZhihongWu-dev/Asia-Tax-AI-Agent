# Database collection tools

This directory contains the reusable tools developed for the CSV-first tax
database package. It intentionally excludes source originals, generated text,
database snapshots, and credentials; those must be supplied through the
separate data package.

## Expected data-package layout

Place the following alongside this README before running the tools:

```text
database/
  jurisdiction.csv  doc.csv  files.csv  clause.csv  param.csv  decision.csv  treaty.csv
  raw/              text/    docs/
  tools/
```

The package specification is `docs/spec.zh.md`; the work plan is
`docs/task_sheet.zh.md`. The validation tool treats their stated data contract
as authoritative and never silently repairs records.

## Setup and use

Use the project’s Python 3.11 Conda environment and install the declared
dependencies:

```bash
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate tax
pip install -r database/requirements.txt
```

Typical local workflow:

```bash
python database/tools/fetch.py --help
python database/tools/build.py
python database/tools/build.py --jur id
python database/tools/find.py --jur id treaty
python database/tools/clause_diff.py --save
```

`build.py` materialises conservative whole-document clauses only for new or
explicitly refreshed originals, validates checksums and citations, and writes
the local SQLite/status artifacts. `find.py` is read-only; `clause_diff.py`
guards a later slicer change from invalidating existing citations.

## Supabase operations

`upload.py` is deliberately limited to the Supabase `database` schema and
Storage bucket. Configure credentials locally in a git-ignored `.env` file
either at the repository root or in this directory. It accepts the existing
`database_url`/`DATABASE_URL`, `supabase_url`/`SUPABASE_URL`, and
`supabase_key`/`SUPABASE_KEY` names. Never commit the file.

```bash
python database/tools/upload.py --partial --resume
python database/tools/upload.py --partial --verify
```

The schema uploader loads through a staging schema and swaps it in a single
transaction. The storage verifier has a retry-safe curl fallback for transient
TLS failures. `pull_database.py` is a read-only inspection/downloader, and
`audit_download.py` performs supplementary local integrity/coverage checks;
neither replaces `build.py` acceptance.
