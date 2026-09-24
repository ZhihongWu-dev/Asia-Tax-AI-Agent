"""Structured case analysis shared by the intake CLI and the web API.

The model proposes candidate facts (ai_candidate); the dictionary contract
rejects anything outside the vocabulary; the deterministic chain decides;
facts, executions and provenance are persisted. The result is a plain,
JSON-ready dict: the CLI renders it to Markdown, the web API returns it as is.
"""

from __future__ import annotations

import hashlib
import threading
import time
import uuid
from functools import lru_cache
from typing import Any

from sqlalchemy import select

from packages.contracts.enums import JUDGEMENT_CHAIN
from packages.intake.extraction import ExtractionResult, extract_facts
from packages.intake.prompting import PROMPT_VERSION, field_catalog
from packages.knowledge_loader.parser import current_git_commit
from packages.persistence.db import session_scope
from packages.persistence.models import AuditEvent, Fact, FactVersion, LegalUnit, RuleNode
from packages.reporting.assemble import report_input_from_outcome
from packages.reporting.cli import source_catalog
from packages.reporting.renderer import RESEARCH_WATERMARK, render_markdown
from packages.rule_engine.cli import (
    ensure_research_org,
    latest_rule_set,
    persist_execution_records,
    upsert_case_file,
)
from packages.rule_engine.runner import EVALUATED_NODES, ChainRule, run_chain

INTAKE_FACT_STATUS = "ai_candidate"

# The org/case upserts check before inserting and the tables have no unique
# constraint on those keys, so two concurrent web requests for the same case
# could insert duplicates. Serialise the short database phase; the slow model
# call stays outside the lock.
_DB_LOCK = threading.Lock()


@lru_cache(maxsize=1)
def engine_commit() -> str | None:
    """The code commit that runs the chain. The rule package version alone
    does not pin evaluator behaviour, so every run records this too."""
    return current_git_commit()


def default_case_id(text: str) -> str:
    return "NL-" + hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


class _IntakeCase:
    """Structural stand-in for EvaluationCase when upserting the case file."""

    def __init__(self, case_id: str, text: str):
        self.case_id = case_id
        self.description = text[:255]
        self.applicable_date = None


def _persist_candidate_facts(session, org, case_file, facts: dict[str, Any]) -> None:
    """Intake facts are AI candidates, never client statements; sentinel values
    become confirmation states with no stored value. Every change appends a
    FactVersion, as the evaluation harness does."""
    for field_name, value in sorted(facts.items()):
        if value == "unknown":
            stored_value, status = None, "unknown"
        elif value == "conflict":
            stored_value, status = None, "conflict"
        else:
            stored_value, status = value, INTAKE_FACT_STATUS
        fact = session.execute(
            select(Fact).where(Fact.case_id == case_file.id, Fact.field_name == field_name)
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
            last_version = session.execute(
                select(FactVersion.version_no)
                .where(FactVersion.fact_id == fact.id)
                .order_by(FactVersion.version_no.desc())
                .limit(1)
            ).scalar_one_or_none() or 0
            session.add(FactVersion(
                organization_id=org.id, fact_id=fact.id, version_no=last_version + 1,
                value=stored_value, confirmation_status=status, updated_by="intake_llm",
            ))


def _fact_rows(facts: dict[str, Any]) -> list[dict[str, Any]]:
    specs = {f["field_name"]: f for f in field_catalog()}
    rows = []
    for name, value in sorted(facts.items()):
        spec = specs.get(name, {})
        status = value if value in ("unknown", "conflict") else INTAKE_FACT_STATUS
        rows.append({
            "field": name,
            "value": None if value in ("unknown", "conflict") else value,
            "status": status,
            "domain": spec.get("domain"),
            "data_type": spec.get("data_type"),
            "blocking_level": spec.get("blocking_level"),
            "related_nodes": spec.get("related_nodes", []),
            "statute_locator": spec.get("statute_locator"),
        })
    return rows


def _chain_rows(outcome, rule_nodes_meta: dict[str, tuple]) -> list[dict[str, Any]]:
    """Every canonical node in chain order. A node counts as implemented only
    if this engine has an evaluator for it; the others are reported as not
    implemented rather than silently omitted."""
    executed = {o.node: o for o in outcome.node_outcomes}
    rows = []
    for node, ordinal in sorted(JUDGEMENT_CHAIN.items(), key=lambda kv: (kv[1] == 0, kv[1])):
        o = executed.get(node)
        implemented = o is not None and node in EVALUATED_NODES
        rule_id, source_ids, locators = rule_nodes_meta.get(node, (None, (), ()))
        detail = o.detail if implemented and isinstance(o.detail, dict) else {}
        rows.append({
            "node": node,
            "ordinal": ordinal,
            "implemented": implemented,
            "rule_id": rule_id if implemented else None,
            "output": o.output if implemented else None,
            "blockers": list(o.blockers) if implemented else [],
            "escalation_blockers": list(o.escalation_blockers) if implemented else [],
            "note": detail.get("note"),
            "source_ids": list(source_ids),
            "statute_locators": list(locators),
        })
    return rows


def analyze_case(
    text: str,
    case_id: str | None = None,
    *,
    extraction: ExtractionResult | None = None,
) -> dict[str, Any]:
    text = text.strip()
    case_id = case_id or default_case_id(text)
    started = time.monotonic()
    extraction = extraction or extract_facts(text)
    extracted = time.monotonic()
    facts = dict(extraction.facts)
    commit = engine_commit()

    with _DB_LOCK, session_scope() as session:
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

        case_file = upsert_case_file(session, org, _IntakeCase(case_id, text))
        _persist_candidate_facts(session, org, case_file, facts)

        outcome = run_chain(case_id, facts, chain_rules)
        execution_batch = f"{case_id}:{uuid.uuid4().hex[:12]}"
        persist_execution_records(
            session, org, case_file, rule_set, rule_nodes, outcome,
            execution_batch, actor="intake_llm", facts_snapshot=facts,
        )
        # What produced this run, so it can be audited later.
        session.add(AuditEvent(
            organization_id=org.id,
            actor="intake_llm",
            action="extract_facts",
            entity_type="case",
            entity_id=str(case_file.id),
            payload={
                "execution_batch": execution_batch,
                "model": extraction.model,
                "prompt_version": extraction.prompt_version or PROMPT_VERSION,
                "repair_rounds": extraction.repair_rounds,
                "rule_set_version": rule_set.version,
                "engine_commit": commit,
                "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "text_chars": len(text),
            },
        ))

        rule_nodes_meta = {
            n.node: (
                n.rule_id,
                tuple(n.source_ids or ()),
                tuple(t.get("statute_locator") for t in (n.thresholds or []) if t.get("statute_locator")),
            )
            for n in rule_node_rows
        }
        locators = {loc for meta in rule_nodes_meta.values() for loc in meta[2]}
        statute_units: dict[str, str] = {}
        if locators:
            statute_units = {
                u.statute_locator: u.text
                for u in session.execute(
                    select(LegalUnit).where(LegalUnit.statute_locator.in_(locators))
                ).scalars()
            }
        report_input = report_input_from_outcome(
            outcome,
            case_description=text[:255],
            execution_batch=execution_batch,
            organization_name=org.name,
            rule_set_version=rule_set.version,
            git_commit=rule_set.git_commit,
            rule_nodes_meta=rule_nodes_meta,
            statute_units=statute_units,
        )
        rule_set_version = rule_set.version
        rule_set_status = rule_set.professional_validation_status or "unverified"
        rule_package_commit = rule_set.git_commit

    catalog = source_catalog()
    used_sources = sorted({sid for meta in rule_nodes_meta.values() for sid in meta[1]})
    finished = time.monotonic()
    return {
        "case_id": case_id,
        "execution_batch": execution_batch,
        "model": extraction.model,
        "prompt_version": extraction.prompt_version or PROMPT_VERSION,
        "repair_rounds": extraction.repair_rounds,
        "rule_set_version": rule_set_version,
        "rule_set_status": rule_set_status,
        "git_commit": rule_package_commit,
        "engine_commit": commit,
        "facts": _fact_rows(facts),
        "raw_facts": facts,
        "terminal_state": outcome.terminal_state,
        "blockers": list(outcome.blockers),
        "conflict_fields": list(outcome.conflict_fields),
        "chain": _chain_rows(outcome, rule_nodes_meta),
        "statute_units": [
            {"locator": loc, "text": statute_units[loc]} for loc in sorted(statute_units)
        ],
        "sources": [
            {
                "source_id": sid,
                "title": catalog.get(sid, {}).get("title"),
                "url": catalog.get(sid, {}).get("url"),
            }
            for sid in used_sources
        ],
        "watermark": RESEARCH_WATERMARK,
        "timing_ms": {
            "extraction": round((extracted - started) * 1000),
            "total": round((finished - started) * 1000),
        },
        "report_markdown": render_markdown(report_input),
    }
