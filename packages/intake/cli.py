"""Natural-language case intake: description -> facts -> chain -> report.

Usage:
    python -m packages.intake.cli PATH/TO/description.txt [--case-id ID]

The LLM only proposes candidate facts (ai_candidate); everything downstream
is deterministic. Requires the model adapter to be configured (.env).
The analysis itself lives in packages.intake.service so the web API and this
CLI run exactly the same flow.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from packages.intake.service import INTAKE_FACT_STATUS, analyze_case, default_case_id
from packages.reporting.cli import REPORTS_DIR

__all__ = ["INTAKE_FACT_STATUS", "run_intake", "main"]

# Kept for callers of the previous private helper.
_default_case_id = default_case_id


def run_intake(description_path: Path, case_id: str | None = None) -> dict:
    text = description_path.read_text(encoding="utf-8").strip()
    result = analyze_case(text, case_id)

    report_dir = REPORTS_DIR / result["case_id"]
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{result['execution_batch'].replace(':', '-')}.md"
    report_path.write_text(result["report_markdown"], encoding="utf-8")

    return {
        "case_id": result["case_id"],
        "facts": result["raw_facts"],
        "terminal_state": result["terminal_state"],
        "blockers": result["blockers"],
        "report_path": str(report_path),
        "model": result["model"],
    }


def main(argv: list[str] | None = None) -> int:
    args = argparse.ArgumentParser(description="NL case intake for L0.")
    args.add_argument("description", help="path to a plain-text case description")
    args.add_argument("--case-id", default=None)
    parsed = args.parse_args(argv)

    result = run_intake(Path(parsed.description), parsed.case_id)
    print(f"case_id:    {result['case_id']}")
    print(f"model:      {result['model']}")
    print(f"facts:      {len(result['facts'])} 个候选事实（ai_candidate）")
    for k, v in sorted(result["facts"].items()):
        print(f"  - {k} = {v!r}")
    print(f"terminal:   {result['terminal_state']}")
    print(f"blockers:   {result['blockers']}")
    print(f"report:     {result['report_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
