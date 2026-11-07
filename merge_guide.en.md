# Merge guide: make `main` the new model and deploy it

You are integrating this repository on your own machine. The project owner has decided that the new model on branch
`LiZiheng` replaces the old Taxrora application on `main`. Your job: set up the environment, make `main` one product
built on the new model, fix the bugs you find, point the cloud deployment at the new model, deploy it, and report.
Two things other people built must survive: the law library in `database/`, and the team's cloud setup (Render
deployment, Supabase sign-in, per-user data), which you keep only as far as the new model needs it.

## Where things stand

- `origin/main` holds three things at once: the old Taxrora production app (`packages/`, `apps/api/main.py`,
  `apps/knowledge_api/`, `alembic/`, `tests/`, `evals/`, `docs/`, `knowledge/`, its own `apps/web`, and so on); an
  older copy of the new model, merged on 2026-11-03 from commit `0973ce1`; and a database package from another
  collector, merged the same day ("Merge zijian-Luo tax database package").
- `origin/LiZiheng` holds the new model. Use its tip at the time you start and record the hash in your report. Several
  files that `main` still has were deleted on the branch on purpose because they were no longer used.
- The merge base is `0973ce1`, so a plain `git merge` conflicts wherever `main` changed that copy. Deciding path by path
  (branch version, main version, or delete) is clearer than resolving hunks.

## Steps

### 0. Environment and keys

- Fetch both branches. Work locally on `main` (from `origin/main`), commit as you go, and never force-push.
- Create the conda environment `tax` with Python 3.11 (if you already have one by that name, use it) and install the
  branch's root `requirements.txt` into it (`git show origin/LiZiheng:requirements.txt`). It pins PyTorch for CUDA 12.8; on a machine without an NVIDIA GPU,
  install the CPU (or Mac) build of the same version instead. From here on, run every Python command with this
  environment's interpreter, and point every config that names an interpreter at it.
- The keys are in `key.md` at the root of `LiZiheng`. This is a group assignment, not a product: the owner wants the
  keys in git so every member and the cloud get them from the repository. Bring `key.md` into your working tree and
  merge it into the `.env` you already have at the root; do not replace that file. Your `.env` holds keys of your own
  (very likely the Render API key and the team's Supabase settings): keep every line of it as it is. Add each
  `name=value` line of `key.md` whose name your `.env` lacks. Where a name is in both with different values, keep yours
  and list the name in the report. Lines of `key.md` that are not `name=value` (such as an account and its password)
  stay in `key.md` only. Commit both files. Remove `.env` from `.gitignore` (keep its other rules) so git tracks it
  normally. Never print a value; check keys by name.

### 1. Classify

List every path on `main` and on the branch and put each into one of four groups. Write the list into
`merge_report.md` at the root before you delete anything.

- **Branch wins:** everything the branch has, outside the two exceptions. Take the branch version.
- **Main only, superseded:** what only `main` has and belongs to the old application, including what the branch
  deleted. Remove it; it stays in git history.
- **`database/`, exception 1:** leave `database/` exactly as `main` has it. Do not edit, move, merge or rebuild any
  file in it. The owner is completing the library separately and will merge it themselves.
- **Cloud, exception 2:** what deployment, sign-in and cloud storage need: `render.yaml`, `scripts/render_build.sh`
  and what it calls, `.github/workflows/`, the Supabase sign-in in `apps/api/auth.py`, `alembic/` and the cloud case
  table, `config/`, `.env.example`, the deployment and auth docs in `docs/project/`. Keep them for now; step 4 decides
  what of them survives.

### 2. Overwrite

Apply the classification. The branch's root `requirements.txt` is the Python dependency list; retire `pyproject.toml`
and `requirements-b-agent.lock`. Merge the two `.gitignore` files (secret rules except `.env`, plus the branch's
`/cases/`, index and product rules).

### 3. Fix bugs

Run the checks in `AGENTS.md` and paste their real output into the report. Then look beyond them:

- imports of removed modules, references to deleted paths (code, configs, docs, CI);
- machine-specific paths: `.mcp.json`, `.claude/mcp/*.json` and `.claude/settings.json` name one machine's
  `C:/Coding/Anaconda/envs/tax/python.exe`. Make them portable and regenerate `.claude/` with
  `agent/tools/make_agents.py`;
- Windows-only assumptions (the Codex adapter looks for the app-bundled `codex.exe` under `%LOCALAPPDATA%\OpenAI\Codex\bin`
  when `TAX_CODEX_BIN` is unset, then for `codex` on PATH; the Claude path looks for `claude.exe` in the VS Code
  extension when `CLAUDE_BIN` is unset and `claude` is not on PATH);
- uploads: the host accepts `.doc`, `.docx`, `.xls` and `.xlsx` (`UPLOAD_TYPES` in `apps/api/server.py`), but
  `agent/tools/doc_parse.py` reads only PDFs and images, so a Word or Excel upload is never read. Make them readable
  (`openpyxl` is installed; a `.docx` is a zip of XML) or stop accepting them, and say which;
- the rule layer against the library: rules cite clause ids (`doc#clause`) that must exist in `database/clause.csv`.
  On today's `main`, 81 of the 173 ids cited in `rule/rule.csv` do not resolve, because `database/` there is the other
  package, and `database/tools/mcp_server.py`, which `.mcp.json` starts, is missing. Because `database/` is excepted,
  these stay broken: list them; do not fix them by editing `database/` or the rules.

Fix a bug when the fix is small and clearly right, and say what you changed. Leave legal content alone (`AGENTS.md`,
"Law content is not code"): a wrong-looking rate or citation is reported, not edited.

### 4. Point the cloud at the new model, and cut what it does not need

The cloud runs our web host (`apps/api/server.py`, serving the built `apps/web/dist`) and nothing else. One backend,
one UI: ours. Our UI already has sign-in pages (`apps/web/src/auth.tsx`, `components/AuthPage.tsx`). Cut the old UI,
`apps/knowledge_api/`, and every other fork of the old app; cut from the cloud group whatever the new model does not use
(the old build steps: `pip install .`, the RapidOCR/OpenCV swap, `install_tax_engine_release.py`, the legacy Word
reader, unless ours needs it; tables and migrations that no longer serve anything; the CI jobs of the old tests, which
become our checks). What our host does today, so you can see the gaps:

- It binds `127.0.0.1` with a fixed port, has no `/health`, and a single local user (a stub behind
  `/api/auth/session`, `login`, `logout`). On the cloud it needs `0.0.0.0:$PORT`, the deployment's trusted host, a
  health check, and the Supabase sign-in, with every case owned by the signed-in user.
- Cases are folders of files under `cases/`; the agents read and write those files, so keep the layout. They must
  survive deploys and restarts. A free Render service has no persistent disk, so sync the case folders to the team's
  cloud store (the Supabase project behind the sign-in) and restore them on start.
- Since 2026-11-07 the agents run on the Codex CLI (`agent/tools/orchestrate_codex.py`, configuration
  `agent/harness.json`; the web host's default, `TAX_HARNESS=claude` for the earlier Claude Code path). The build must
  install a Linux Codex CLI that talks to an OpenAI-compatible provider over the Responses API (the npm package
  `@openai/codex`; locally tested with 0.165.0-alpha.1.2, so check the cloud version against it) and set `TAX_CODEX_BIN`
  or put `codex` on PATH. Each agent call is a fresh process with its own `CODEX_HOME` under `.codex/runtime/`, which
  must be writable and grows with every call. Claude Code is needed only if the cloud runs with `TAX_HARNESS=claude`.
- The model key is read from `.env` only (`qwen_key`: `harness.process_env` in `agent/tools/harness.py` for the Codex
  path, `claude_env` in `agent/tools/orchestrate.py` for the Claude path); also read the process environment. The keys come from the committed `.env`; values that differ on the cloud (`site_url` = the
  deployment address, secure cookies) go into `render.yaml` and override `.env`.
- Two Supabase settings, not one. Sign-in and the cloud case store use the team's settings that `render.yaml` and
  `apps/api/auth.py` name (`FSIE_AUTH_*`, `FSIE_DATABASE_URL`). Our lowercase `supabase_url`, `supabase_key` and
  `database_url` are used only by `database/tools/upload.py`, for the law library's remote copy. Do not merge the two
  sets or point one at the other.
- The report PDF is typeset with xelatex and ctex (`agent/tools/render_pdf.py`); Render has no TeX. Install a small
  TeX engine in the build (for example Tectonic, or a minimal TeX Live with ctex and CJK fonts) or say what the cloud
  delivers instead.
- The cloud runs a light edition on the current Render plan (`free`: 512 MB, and it sleeps after 15 minutes without
  requests). Make it so:
  - No PyTorch on the cloud. Retrieval switches live in `agent/retrieval_settings.json` (`dense`, `rerank` per
    material); on the cloud turn `dense` and every `rerank` off, which leaves keyword (BM25) and graph search. OCR runs
    only when asked (`doc_parse.py --ocr`), so scanned uploads stay "needs OCR". Let the cloud override the settings
    file (for example an environment variable naming another file) rather than editing the local one, and install the
    cloud build without the PyTorch group of `requirements.txt` (torch, torchvision, transformers,
    sentence-transformers, tokenizers, safetensors). Check that nothing imports them at start-up.
  - A run (one to three hours) is a child process of the web service, and a sleeping service kills it. Keep the
    service awake while a run is in progress (the open page already polls the progress; make sure that polling counts,
    or have the run itself keep the service busy), and tell the client in the UI not to close the page during a run.
  - Measure the memory of one run on the cloud (the Codex CLI plus the MCP servers it starts; the review node runs two
    agents at once, the main check and the legal lane). If 512 MB is not enough, say so with the figure.
  In the report, list what the light edition loses against the local one, and which Render plan would run the full
  product. `README.md` has a section "Local and cloud editions" that says the cloud runs the light edition only; once
  deployed, make it true: the address, and the limits as you measured them.

### 5. Deploy

`render.yaml` deploys `main` on every commit, so pushing `main` deploys. Push once steps 1–4 are done and the checks
have run. Then watch the deploy. The Render dashboard may not be open to you, so use what you can reach:

- If your `.env` (or `key.md`) has a Render API key, read the deploys and their logs through the Render API.
- Else read the deploy status that Render reports on the GitHub commit (`gh api repos/{owner}/{repo}/commits/<sha>/status`
  or `.../check-runs`), if it reports one.
- In any case, test the public address yourself: `/health`, sign in, create a case, send a message, start a run.
  Until the owner merges their library into `database/` (step 3, the 81 ids), the computation part of a run is expected
  to fail or come out incomplete; test up to that point, and record where and how it failed, so the owner can check it
  again after the library merge.

Fix and push again until it works, or until what is left needs the owner (a log you cannot read, a paid plan, a setting
only they can change): then say exactly what they must do.

### 6. Report in `merge_report.md` (committed with the merge)

The classification; what was removed; what was cut from the cloud and why; the check output; bugs fixed and bugs left
open, each with file, line and how to reproduce it; the deploy result and what still needs the owner.

## Do not

- Print a key in the report, a log or the terminal output.
- Run `database/tools/upload.py` or anything that writes the shared Supabase database.
- Rewrite working code for style, rename things, or redesign the agents, specs or case format. Change what the
  integration, the deployment and a bug fix need.
- Add Baidu components (PaddleOCR, PaddlePaddle, MinerU, RapidOCR).
