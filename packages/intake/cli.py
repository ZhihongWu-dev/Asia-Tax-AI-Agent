"""Natural-language case intake: description -> facts -> chain -> report.

Usage:
    python -m packages.intake.cli PATH/TO/description.txt [--case-id ID]

The LLM only proposes candidate facts (ai_candidate); everything downstream
is deterministic. Requires the model adapter to be configured (.env).
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import uuid
from pathlib import Path

from sqlalchemy import select

from packages.intake.extraction import extract_facts
from packages.persistence.db import session_scope
from packages.persistence.models import RuleNode, RuleSet
from packages.reporting.assemble import report_input_from_outcome
from packages.reporting.renderer import render_markdown
from packages.reporting.cli import REPORTS_DIR
from packages.rule_engine.cli import (
    ensure_research_org,
    latest_rule_set,
    upsert_case_file,
    upsert_facts,
    persist_execution_records,
)
from packages.rule_engine.runner import ChainRule, run_chain

INTAKE_FACT_STATUS = "ai_candidate"


def _default_case_id(text: str) -> str:
    return "NL-" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


def run_intake(description_path: Path, case_id: str | None = None) -> dict:
    text = description_path.read_text(encoding="utf-8").strip()
    case_id = case_id or _default_case_id(text)

    extraction = extract_facts(text)

    with session_scope() as session:
        org = ensure_research_org(session)
        rule_set = latest_rule_set(session)
        rule_node_rows = session.execute(
            select(RuleNode).where(RuleNode.rule_set_id == rule_set.id)
        ).scalars().all()
        rule_nodes = {n.node: n for n in rule_node_rows}
        chain_rules = [
            ChainRule(
                rule_id=n.rule_id, node=n.node, ordinal=n.ordinal,
                thresholds={t["name"]: t["value"] for t in (n.thresholds or [])},
            )
            for n in rule_node_rows
        ]

        class _IntakeCase:  # structural stand-in for EvaluationCase
            def __init__(self):
                self.case_id = case_id
                self.description = text[:255]
                self.applicable_date = None

        case_file = upsert_case_file(session, org, _IntakeCase())

        # Intake facts are AI candidates, not client statements.
        facts = dict(extraction.facts)
        from packages.persistence.models import Fact, FactVersion
        from sqlalchemy import select as _sel
        for field_name, value in sorted(facts.items()):
            if value == "unknown":
                stored_value, status = None, "unknown"
            elif value == "conflict":
                stored_value, status = None, "conflict"
            else:
                stored_value, status = value, INTAKE_FACT_STATUS
            fact = session.execute(
                _sel(Fact).where(Fact.case_id == case_file.id, Fact.field_name == field_name)
            ).scalar_one_or_none()
            if fact is None:
                fact = Fact(
                    organization_id=org.id, case_id=case_file.id, field_name=field_name,
                    value=stored_value, confirmation_status=status, updated_by="intake_llm",
                )
                session.add(fact)
                session.flush()
                session.add(FactVersion(
                    organization_id=org.id, fact_id=fact.id, version_no=1,
                    value=stored_value, confirmation_status=status, updated_by="intake_llm",
                ))
            elif fact.value != stored_value or fact.confirmation_status != status:
                fact.value, fact.confirmation_status = stored_value, status
                fact.updated_by = "intake_llm"

        outcome = run_chain(case_id, facts, chain_rules)
        execution_batch = f"{case_id}:{uuid.uuid4().hex[:12]}"
        persist_execution_records(
            session, org, case_file, rule_set, rule_nodes, outcome,
            execution_batch, actor="intake_llm", facts_snapshot=facts,
        )

        report_input = report_input_from_outcome(
            outcome,
            case_description=text[:255],
            execution_batch=execution_batch,
            organization_name=org.name,
            rule_set_version=rule_set.version,
            git_commit=rule_set.git_commit,
            rule_nodes_meta={
                n.node: (n.rule_id, tuple(n.source_ids or ())) for n in rule_node_rows
            },
        )

    report_dir = REPORTS_DIR / case_id
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{execution_batch.replace(':', '-')}.md"
    report_path.write_text(render_markdown(report_input), encoding="utf-8")

    return {
        "case_id": case_id,
        "facts": extraction.facts,
        "terminal_state": outcome.terminal_state,
        "blockers": list(outcome.blockers),
        "report_path": str(report_path),
        "model": extraction.model,
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
