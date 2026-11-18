# Combined Python regression and CI dependency repair

Baseline:19fff27. The all-tests command in the application virtualenv failed during collection with11 missing-PyMuPDF import errors. Li's database tooling already declares a separate pinned dependency set in `database/requirements.txt`; the existing CI job installed only the application `[dev]` extra but collected those tests too.

Changed CI to run database-tool tests in a separate Python3.11 job with that existing requirements file and pytest. The application job excludes only `tests/database`, which is covered by the new required-to-pass job. Fresh PostgreSQL migration and frontend/browser jobs remain unchanged. No dependency was installed into the running original optimizer environment.

Reference: https://github.com/actions/setup-python/blob/main/README.md — existing pinned action supports a distinct `cache-dependency-path` for the database requirements. No new action, copied code or dependency version upgrade.

Local verification:

- Dedicated database environment: `python -m pytest tests/database -q --tb=short` —76 passed in14.45 seconds.
- YAML parses into frontend, application, database-tools and migrations jobs; scoped diff check passes.
- `scripts/validate_fsie_package.py` passes:11 sources,6 rules,8 evidence requirements,10 synthetic cases;43 fact fields and26 evidence types.
- Application regression: `python -X utf8 -m pytest tests --ignore=tests/database -m 'not integration' -q --tb=short` remains running in session85115 at this checkpoint. Progress exceeded80%; no completion claim. Retrieve terminal output before reporting its final result.

The new GitHub-hosted job has not run remotely. Local Windows success is not proof of Linux CI, deployed account isolation, source migration, or final business acceptance. Original optimizer PID16760 also remains live, on unchanged inputs.
