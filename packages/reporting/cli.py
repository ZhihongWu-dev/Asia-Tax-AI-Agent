"""Rebuild L0 research reports from persisted execution records.

Usage:
    make report            # latest run of every evaluation case
    .venv/bin/python -m packages.reporting.cli CASE_ID ...
    .venv/bin/python -m packages.reporting.cli --all   # every run, not just latest

Reports are written to reports/{case_id}/{batch}.md (git-ignored runtime
artifacts). Rendering is deterministic: the same database state always
reproduces byte-identical reports, which is the point — the audit trail is
complete enough to rebuild any past report.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import select
from packages.knowledge_loader import parser as knowledge_parser
from packages.persistence.db import session_scope
from packages.persistence.models import (
    EvaluationCase,
    EvaluationResult,
    EvaluationRun,
    Organization,
    RuleNode,
    RuleSet,
)
from packages.reporting.renderer import NodeRow, ReportInput, render_markdown

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = REPO_ROOT / "reports"


def source_catalog() -> dict[str, dict[str, str]]:
    manifest = knowledge_parser._read_json(
        knowledge_parser.FSIE_DIR / "source_manifest.json"
    )
    return {s["source_id"]: s for s in manifest["sources"]}


def collect_report_inputs(
    session: Session, case_ids: list[str] | None = None, all_runs: bool = False
) -> list[ReportInput]:
    runs_query = (
        select(EvaluationRun)
        .join(EvaluationCase, EvaluationRun.evaluation_case_id == EvaluationCase.id)
        .order_by(EvaluationCase.case_id, EvaluationRun.id)
    )
    if case_ids:
        runs_query = runs_query.where(EvaluationCase.case_id.in_(case_ids))
    runs = session.execute(runs_query).scalars().all()
    if not runs:
        raise SystemExit("No evaluation runs found. Run `make run-eval` first.")

    if not all_runs:
        latest: dict[int, EvaluationRun] = {}
        for run in runs:
            latest[run.evaluation_case_id] = run  # ascending id -> last wins
        runs = list(latest.values())

    catalog = source_catalog()
    reports: list[ReportInput] = []
    for run in runs:
        eval_case = session.get(EvaluationCase, run.evaluation_case_id)
        org = session.get(Organization, run.organization_id)
        rule_set = session.get(RuleSet, run.rule_set_id)
        rule_nodes = {
            n.node: n
            for n in session.execute(
                select(RuleNode).where(RuleNode.rule_set_id == rule_set.id)
            ).scalars()
        }
        results = session.execute(
            select(EvaluationResult)
            .where(EvaluationResult.evaluation_run_id == run.id)
            .order_by(EvaluationResult.ordinal, EvaluationResult.node)
        ).scalars().all()

        node_rows = []
        for result in results:
            rule_node = rule_nodes.get(result.node)
            detail = dict(result.detail or {})
            node_rows.append(
                NodeRow(
                    node=result.node,
                    ordinal=result.ordinal,
                    rule_id=rule_node.rule_id if rule_node else None,
                    output=result.output,
                    blockers=tuple(result.blockers or ()),
                    escalation_blockers=tuple(detail.pop("escalation_blockers", []) or []),
                    note=detail.get("note"),
                    source_ids=tuple(rule_node.source_ids) if rule_node else (),
                )
            )

        summary = dict(run.summary or {})
        reports.append(
            ReportInput(
                case_id=eval_case.case_id,
                case_description=eval_case.description,
                synthetic=bool(eval_case.synthetic),
                execution_batch=_batch_of(run, eval_case.case_id),
                generated_at=run.finished_at.isoformat() if run.finished_at else "",
                organization_name=org.name if org else "",
                rule_set_version=rule_set.version,
                git_commit=rule_set.git_commit,
                terminal_state=run.terminal_state or "unknown",
                run_blockers=tuple(summary.get("blockers", [])),
                conflict_fields=tuple(summary.get("conflict_fields", [])),
                node_rows=tuple(node_rows),
                source_catalog=catalog,
            )
        )
    return reports


def _batch_of(run: EvaluationRun, case_id: str) -> str:
    """The batch id lives in the run summary (runs created before it was
    recorded fall back to a stable run-id label)."""
    batch = (run.summary or {}).get("execution_batch")
    return batch or f"{case_id}:run-{run.id}"


def write_reports(inputs: list[ReportInput], base_dir: Path | None = None) -> list[Path]:
    base = base_dir or REPORTS_DIR
    paths: list[Path] = []
    for report in inputs:
        target_dir = base / report.case_id
        target_dir.mkdir(parents=True, exist_ok=True)
        safe_batch = report.execution_batch.replace(":", "-").replace("/", "-")
        path = target_dir / f"{safe_batch}.md"
        path.write_text(render_markdown(report), encoding="utf-8")
        paths.append(path)
    return paths


def main(argv: list[str] | None = None) -> int:
    args = argparse.ArgumentParser(description="Rebuild L0 research reports from the DB.")
    args.add_argument("case_ids", nargs="*", help="optional case id filter")
    args.add_argument("--all", action="store_true", help="render every run, not just the latest")
    parsed = args.parse_args(argv)

    with session_scope() as session:
        inputs = collect_report_inputs(session, parsed.case_ids or None, all_runs=parsed.all)

    paths = write_reports(inputs)
    print(f"Rendered {len(paths)} report(s):")
    for path in paths:
        print(f"  {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
