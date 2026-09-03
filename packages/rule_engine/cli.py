"""Run the L0 synthetic evaluation cases end-to-end against the live database.

Usage:
    make run-eval
    .venv/bin/python -m packages.rule_engine.cli [CASE_ID ...]

Flow per case: upsert the research org / case / fact card, execute the
deterministic chain, persist rule_executions + evaluation_results + the
evaluation_run, then compare against the golden expectations carried by the
case itself. Exits non-zero when any case fails its expectation.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from packages.persistence.db import session_scope
from packages.persistence.models import (
    AuditEvent,
    CaseFile,
    EvaluationCase,
    EvaluationResult,
    EvaluationRun,
    Fact,
    FactVersion,
    Organization,
    RuleExecution,
    RuleNode,
    RuleSet,
)
from packages.rule_engine.runner import (
    CaseExpectation,
    ChainRule,
    RunOutcome,
    check_expectation,
    run_chain,
)

L0_ORG_NAME = "L0 Research Organisation"
TERMINAL_TO_CASE_STATUS = {
    "research_only_output": "pending_review",
    "human_review_required": "needs_human_judgment",
    "stop_and_escalate": "needs_human_judgment",
}


@dataclass
class CaseRunReport:
    case_id: str
    terminal_state: str
    expected_state: str | None
    blockers: tuple[str, ...]
    expected_blockers: tuple[str, ...]
    passed: bool | None
    execution_batch: str


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_research_org(session: Session) -> Organization:
    org = session.execute(
        select(Organization).where(Organization.name == L0_ORG_NAME)
    ).scalar_one_or_none()
    if org is None:
        org = Organization(name=L0_ORG_NAME, status="active")
        session.add(org)
        session.flush()
    return org


def latest_rule_set(session: Session) -> RuleSet:
    rule_set = session.execute(
        select(RuleSet)
        .where(RuleSet.jurisdiction == "HK", RuleSet.package == "fsie")
        .order_by(RuleSet.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if rule_set is None:
        raise SystemExit("No HK/fsie rule set loaded. Run `make load` first.")
    return rule_set


def upsert_case_file(session: Session, org: Organization, eval_case: EvaluationCase) -> CaseFile:
    case_file = session.execute(
        select(CaseFile).where(
            CaseFile.organization_id == org.id,
            CaseFile.external_ref == eval_case.case_id,
        )
    ).scalar_one_or_none()
    if case_file is None:
        case_file = CaseFile(
            organization_id=org.id,
            jurisdiction="HK",
            package="fsie",
            external_ref=eval_case.case_id,
            title=(eval_case.description or eval_case.case_id)[:255],
            case_status="analyzing",
            release_level="L0",
            applicable_date=eval_case.applicable_date,
        )
        session.add(case_file)
        session.flush()
    return case_file


def upsert_facts(session: Session, org: Organization, case_file: CaseFile, facts: dict) -> int:
    """Persist the synthetic fact card.

    Sentinel values become confirmation states, never fake data:
    "unknown" -> confirmation_status=unknown (value NULL),
    "conflict" -> confirmation_status=conflict (value NULL),
    anything else -> confirmation_status=client_statement.
    """
    count = 0
    for field_name, raw_value in sorted(facts.items()):
        if raw_value == "unknown":
            value, status = None, "unknown"
        elif raw_value == "conflict":
            value, status = None, "conflict"
        else:
            value, status = raw_value, "client_statement"

        fact = session.execute(
            select(Fact).where(Fact.case_id == case_file.id, Fact.field_name == field_name)
        ).scalar_one_or_none()
        if fact is None:
            fact = Fact(
                organization_id=org.id,
                case_id=case_file.id,
                field_name=field_name,
                value=value,
                confirmation_status=status,
                updated_by="synthetic_case_loader",
            )
            session.add(fact)
            session.flush()
            session.add(
                FactVersion(
                    organization_id=org.id,
                    fact_id=fact.id,
                    version_no=1,
                    value=value,
                    confirmation_status=status,
                    updated_by="synthetic_case_loader",
                )
            )
        elif fact.value != value or fact.confirmation_status != status:
            fact.value = value
            fact.confirmation_status = status
            fact.updated_by = "synthetic_case_loader"
            last_version = session.execute(
                select(FactVersion.version_no)
                .where(FactVersion.fact_id == fact.id)
                .order_by(FactVersion.version_no.desc())
                .limit(1)
            ).scalar_one()
            session.add(
                FactVersion(
                    organization_id=org.id,
                    fact_id=fact.id,
                    version_no=last_version + 1,
                    value=value,
                    confirmation_status=status,
                    updated_by="synthetic_case_loader",
                )
            )
        count += 1
    return count


def persist_run(
    session: Session,
    org: Organization,
    case_file: CaseFile,
    eval_case: EvaluationCase,
    rule_set: RuleSet,
    rule_nodes: dict[str, RuleNode],
    outcome: RunOutcome,
    passed: bool | None,
    execution_batch: str,
) -> EvaluationRun:
    run = EvaluationRun(
        organization_id=org.id,
        rule_set_id=rule_set.id,
        evaluation_case_id=eval_case.id,
        started_at=_utcnow(),
        finished_at=_utcnow(),
        terminal_state=outcome.terminal_state,
        passed=passed,
        summary={
            "execution_batch": execution_batch,
            "blockers": list(outcome.blockers),
            "expected_state": eval_case.expected_state,
            "expected_blockers": list(eval_case.expected_blockers or []),
            "conflict_fields": list(outcome.conflict_fields),
        },
    )
    session.add(run)
    session.flush()

    for node_outcome in outcome.node_outcomes:
        rule_node = rule_nodes.get(node_outcome.node)
        session.add(
            RuleExecution(
                organization_id=org.id,
                case_id=case_file.id,
                rule_set_id=rule_set.id,
                rule_node_id=rule_node.id if rule_node else None,
                execution_batch=execution_batch,
                node=node_outcome.node,
                ordinal=node_outcome.ordinal,
                output=node_outcome.output,
                inputs_snapshot={"facts": dict(eval_case.facts or {})},
                blockers=list(node_outcome.blockers),
            )
        )
        session.add(
            EvaluationResult(
                organization_id=org.id,
                evaluation_run_id=run.id,
                case_id=eval_case.case_id,
                node=node_outcome.node,
                ordinal=node_outcome.ordinal,
                output=node_outcome.output,
                blockers=list(node_outcome.blockers),
                detail={
                    "escalation_blockers": list(node_outcome.escalation_blockers),
                    **dict(node_outcome.detail),
                },
            )
        )

    case_file.case_status = TERMINAL_TO_CASE_STATUS[outcome.terminal_state]
    session.add(
        AuditEvent(
            organization_id=org.id,
            actor="rule_engine",
            action="run_evaluation",
            entity_type="evaluation_run",
            entity_id=str(run.id),
            payload={
                "case_id": eval_case.case_id,
                "execution_batch": execution_batch,
                "terminal_state": outcome.terminal_state,
                "passed": passed,
            },
        )
    )
    return run


def run_all(session: Session, case_ids: list[str] | None = None) -> list[CaseRunReport]:
    org = ensure_research_org(session)
    rule_set = latest_rule_set(session)
    rule_node_rows = session.execute(
        select(RuleNode).where(RuleNode.rule_set_id == rule_set.id)
    ).scalars().all()
    rule_nodes = {n.node: n for n in rule_node_rows}
    chain_rules = [
        ChainRule(
            rule_id=n.rule_id,
            node=n.node,
            ordinal=n.ordinal,
            thresholds={t["name"]: t["value"] for t in (n.thresholds or [])},
        )
        for n in rule_node_rows
    ]

    query = select(EvaluationCase).order_by(EvaluationCase.case_id)
    if case_ids:
        query = query.where(EvaluationCase.case_id.in_(case_ids))
    eval_cases = session.execute(query).scalars().all()
    if not eval_cases:
        raise SystemExit("No evaluation cases found. Run `make load` first.")

    reports: list[CaseRunReport] = []
    for eval_case in eval_cases:
        case_file = upsert_case_file(session, org, eval_case)
        upsert_facts(session, org, case_file, dict(eval_case.facts or {}))
        outcome = run_chain(eval_case.case_id, dict(eval_case.facts or {}), chain_rules)
        expectation = CaseExpectation(
            expected_state=eval_case.expected_state,
            expected_blockers=tuple(eval_case.expected_blockers or ()),
        )
        passed = check_expectation(outcome, expectation)
        execution_batch = f"{eval_case.case_id}:{uuid.uuid4().hex[:12]}"
        persist_run(
            session, org, case_file, eval_case, rule_set, rule_nodes,
            outcome, passed, execution_batch,
        )
        reports.append(
            CaseRunReport(
                case_id=eval_case.case_id,
                terminal_state=outcome.terminal_state,
                expected_state=eval_case.expected_state,
                blockers=outcome.blockers,
                expected_blockers=tuple(eval_case.expected_blockers or ()),
                passed=passed,
                execution_batch=execution_batch,
            )
        )
    return reports


def main(argv: list[str] | None = None) -> int:
    args = argparse.ArgumentParser(description="Run L0 synthetic evaluation cases.")
    args.add_argument("case_ids", nargs="*", help="optional case id filter")
    parsed = args.parse_args(argv)

    with session_scope() as session:
        reports = run_all(session, parsed.case_ids or None)

    print(f"{'case':<16} {'terminal':<24} {'expected':<24} result")
    print("-" * 76)
    all_passed = True
    for r in reports:
        if r.passed is None:
            verdict = "no-expectation"
        elif r.passed:
            verdict = "PASS"
        else:
            all_passed = False
            verdict = "FAIL"
        print(f"{r.case_id:<16} {r.terminal_state:<24} {str(r.expected_state):<24} {verdict}")
        if not r.passed:
            print(f"  blockers:   {sorted(r.blockers)}")
            print(f"  expected:   {sorted(r.expected_blockers)}")
        print(f"  batch:      {r.execution_batch}")
    print("-" * 76)
    print("All cases passed." if all_passed else "Some cases FAILED their expectations.")
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
