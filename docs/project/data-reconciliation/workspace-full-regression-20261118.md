# Workspace regression checkpoint

Base application commit: ba8404c. Local Windows/Edge run, two browser workers.

- Full Playwright suite: 113 passed, 3 skipped, 6.4 minutes. The three skips
  explicitly require FSIE_TAX_ENGINE_RELEASE_DIR; this is not 116 passing tests.
- Chat and planning API/store backend suite: 180 passed, 1 skipped in 133.65
  seconds. The skip requires the legacy Word converter unavailable locally.
- Browser authentication and model responses use deterministic fixtures;
  API, SQLite persistence and configured rules execute locally. These results
  do not establish hosted account isolation or live provider acceptance.

The subsequent structure-only run enabled installed pinned engine release
771e4524961bcc36718db1c9331e7a5f4cda0ce7. It exposed two stale test interactions:
the question controls now live inside a collapsed details element. The first
run had three passes and two failures. Tests now expand the visible summary
before answering unknown or inspecting English action controls, preserving
the existing report persistence/export and localization assertions.

The corrected pinned-engine structure run passed all five tests in 42.3
seconds with no skips. Together with the full suite, all 116 distinct browser
tests have passing evidence across the two configurations; this was not a
single 116-test pinned-engine run.

Research: the official Playwright locator guidance supports using visible
text/role interactions (https://github.com/microsoft/playwright/blob/main/docs/src/locators.md).
No dependency or external implementation code was adopted.

CI push filters now include the delivery branch Zhihong-Wu alongside main,
following GitHub's official workflow syntax examples
(https://github.com/github/docs/blob/main/content/actions/reference/workflows-and-actions/workflow-syntax.md).
This is a local configuration change, not evidence of a successful hosted CI run.

Long-running repaired and original rule validations, source admission,
remaining income-tax business requirements and hosted acceptance remain open.
