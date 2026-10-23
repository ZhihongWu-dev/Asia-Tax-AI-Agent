# Dividend consultation and PDF brief

The existing sidebar, welcome page, conversation UI and composer are retained. New messages
use `/api/cases/{id}/brief/messages`. The default `FSIE_ACTIVE_WORKFLOW=brief` suspends the old
business mutation/research endpoints. Set `FSIE_ACTIVE_WORKFLOW=legacy` to restore the old flow.
Existing cases and messages remain at rest; the new consultation state is independent.

## Workflow

1. Extract quoted facts from chat or the existing attachment parser. Collect payer jurisdiction,
   amount, currency, date, direct holder, shareholding, ultimate beneficiary/residence, existing
   holding companies and the cash/reinvestment goal. Unknown is explicit, not inferred.
2. The server-owned `config/dividend_brief_skill.md` guides the bounded model/tool loop.
   The AI selects legal research, corporate calculations or material follow-up questions.
   Each tool result is observed before the next decision. Display-only evidence is excluded
   from model input. Engine questions are answered only with supporting user quotes.
3. When the AI decides intake is sufficient, the existing conversation receives a completion
   question and opens the report confirmation dialog. Either explicit chat consent or the
   dialog checkbox/button can authorize a PDF job. Merely completing intake cannot.
4. The server freezes the facts, tool results and analysis, generates five pages with ReportLab,
   validates the PDF page count and exposes progress. Downloads require the same case owner
   and unchanged snapshot. Cancel deletes the PDF and prevents a running worker from recreating it.

## Output and calculation scope

The report includes Current State, Alternative Options, Optimal Strategy, Tax Comparison,
Requirements, Implementation, sources, rule version and the input hash. It includes a current
structure diagram and tax comparison visualization. Numeric comparisons are calculated by the
server from compatible finite engine outputs, never model-invented rates or amounts. An unknown
or unsupported result is not represented as zero. Gaps produce a conditional report with next
steps instead of an unsupported claim that a global legal optimum has been established.

Current mapping supports direct corporate dividends among CN/HK/SG in CNY. Personal taxes,
other currencies, complex ownership and other jurisdictions are gaps unless a later verified
adapter is added. The report explicitly distinguishes corporate retention from personal receipt.
Ruling/library decisions are not auto-approved by the AI. No tax rates are hardcoded in this flow.

## Runtime

Install the project dependencies, build the frontend, then use the existing `scripts/run_chat.py`.
ReportLab is a project dependency. PDF output embeds a Chinese TrueType font; macOS automatically
uses Songti. On Linux set `FSIE_BRIEF_FONT_PATH` to an embeddable Chinese TTF/TTC, e.g.
`/usr/share/fonts/truetype/wqy/wqy-microhei.ttc` from the system `fonts-wqy-microhei` package.

Artifacts and minimal status manifests are in ignored `data/consultation_reports/`. Jobs use two
worker threads and an eight-job admission limit. A completed job is recoverable after refresh or
service restart; interrupted jobs become retryable failures. PDFs expire after 24 hours and are
removed on the next access. Cancellation removes the server copy, not an already downloaded file.

## Verification

```sh
.venv/bin/python -m pytest tests/consultation -q
cd apps/web
PLAYWRIGHT_CHANNEL=chrome FSIE_TEST_PYTHON=../../.venv/bin/python \
  npx playwright test --config=brief.playwright.config.ts
cd ../..
.venv/bin/python scripts/check_dividend_brief.py --live-model
```

The Python/browser tests isolate case storage in temporary SQLite and use explicit synthetic
model/calculation doubles; uploads, PDF generation, HTTP authorization, downloads and deletion are
real. The opt-in smoke check uses synthetic facts with the configured live model and actual tools,
without writing cloud case records. Professional validation of tax interpretations is separate.
