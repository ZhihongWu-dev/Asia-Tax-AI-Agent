"""Idempotently load the Git FSIE knowledge package into the database.

Safety rule: the cross-file contract validator must pass before anything is
loaded. Rule nodes are replaced within their (jurisdiction, package, version)
set, so re-running after an edit converges to the Git content instead of
creating duplicates.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from packages.knowledge_loader import parser
from packages.persistence.models import (
    AuditEvent,
    EvaluationCase,
    RuleNode,
    RuleSet,
)


def validate_package_or_raise() -> None:
    result = subprocess.run(
        [sys.executable, str(parser.VALIDATOR_PATH)],
        cwd=parser.REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Contract validation failed; refusing to load the knowledge package.\n"
            f"{result.stdout}{result.stderr}"
        )


@dataclass
class LoadResult:
    rule_set_id: int
    rule_set_version: str
    rules_loaded: int
    cases_loaded: int

    def as_dict(self) -> dict[str, object]:
        return {
            "rule_set_id": self.rule_set_id,
            "rule_set_version": self.rule_set_version,
            "rules_loaded": self.rules_loaded,
            "cases_loaded": self.cases_loaded,
        }


def persist_knowledge(session: Session, *, run_validation: bool = True) -> LoadResult:
    if run_validation:
        validate_package_or_raise()

    rules_payload = parser.load_rules_payload()
    cases_payload = parser.load_cases_payload()

    jurisdiction = "HK"
    package = "fsie"
    version = rules_payload["rule_package_version"]

    rule_set = session.execute(
        select(RuleSet).where(
            RuleSet.jurisdiction == jurisdiction,
            RuleSet.package == package,
            RuleSet.version == version,
        )
    ).scalar_one_or_none()

    if rule_set is None:
        rule_set = RuleSet(
            jurisdiction=jurisdiction,
            package=package,
            version=version,
            git_commit=parser.current_git_commit(),
            professional_validation_status=rules_payload.get("status", "unverified"),
            lifecycle_status="candidate",
        )
        session.add(rule_set)
        session.flush()
    else:
        rule_set.git_commit = parser.current_git_commit()

    # Replace nodes within this set for idempotency.
    session.execute(delete(RuleNode).where(RuleNode.rule_set_id == rule_set.id))
    rules_loaded = 0
    for rule in rules_payload["rules"]:
        session.add(
            RuleNode(
                rule_set_id=rule_set.id,
                rule_id=rule["rule_id"],
                node=rule["node"],
                ordinal=rule["ordinal"],
                title=rule["title"],
                purpose=rule.get("purpose"),
                required_facts=rule.get("required_facts", []),
                required_evidence=rule.get("required_evidence", []),
                depends_on_nodes=rule.get("depends_on_nodes", []),
                source_ids=rule.get("source_ids", []),
                thresholds=rule.get("thresholds"),
                outputs=rule.get("outputs", []),
                human_review_required=bool(rule.get("human_review_required", True)),
                status=rule.get("status", "unverified"),
                effective_from=rule.get("effective_from"),
                effective_to=rule.get("effective_to"),
            )
        )
        rules_loaded += 1

    cases_loaded = 0
    for case in cases_payload["cases"]:
        existing = session.execute(
            select(EvaluationCase).where(EvaluationCase.case_id == case["case_id"])
        ).scalar_one_or_none()
        if existing is None:
            session.add(
                EvaluationCase(
                    dataset_version=cases_payload["dataset_version"],
                    case_id=case["case_id"],
                    synthetic=case["synthetic"],
                    description=case["description"],
                    facts=case.get("facts", {}),
                    expected_state=case["expected_state"],
                    expected_blockers=case.get("expected_blockers", []),
                    scenario_tag=case.get("scenario_tag"),
                    applicable_date=case.get("applicable_date"),
                    notes=case.get("notes"),
                )
            )
        else:
            existing.dataset_version = cases_payload["dataset_version"]
            existing.synthetic = case["synthetic"]
            existing.description = case["description"]
            existing.facts = case.get("facts", {})
            existing.expected_state = case["expected_state"]
            existing.expected_blockers = case.get("expected_blockers", [])
            existing.notes = case.get("notes")
        cases_loaded += 1

    session.add(
        AuditEvent(
            organization_id=None,
            actor="knowledge_loader",
            action="load",
            entity_type="rule_set",
            entity_id=str(rule_set.id),
            payload={"version": version, "rules": rules_loaded, "cases": cases_loaded},
        )
    )
    session.flush()

    return LoadResult(
        rule_set_id=rule_set.id,
        rule_set_version=version,
        rules_loaded=rules_loaded,
        cases_loaded=cases_loaded,
    )
