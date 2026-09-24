"""Structured case analysis shared by the intake CLI and the web API.

The model proposes candidate facts (ai_candidate); the dictionary contract
rejects anything outside the vocabulary; the deterministic chain decides;
facts and executions are persisted. The result is a plain, JSON-ready dict:
the CLI renders it to Markdown, the web API returns it as is.
"""

from __future__ import annotations

import hashlib
import time
import uuid
from typing import Any

from sqlalchemy import select

from packages.contracts.enums import JUDGEMENT_CHAIN
from packages.intake.extraction import ExtractionResult, extract_facts
from packages.intake.prompting import PROMPT_VERSION, field_catalog
from packages.persistence.db import session_scope
from packages.persistence.models import Fact, FactVersion, LegalUnit, RuleNode
from packages.reporting.assemble import report_input_from_outcome
from packages.reporting.cli import source_catalog
from packages.reporting.renderer import RESEARCH_WATERMARK, render_markdown
from packages.rule_engine.cli import (
    ensure_research_org,
    latest_rule_set,
    persist_execution_records,
    upsert_case_file,
)
from packages.rule_engine.runner import ChainRule, run_chain

INTAKE_FACT_STATUS = "ai_candidate"
GATE_NODE = "human_gate"


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
    become confirmation states with no stored value."""
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
    """Every canonical node in chain order; nodes without a rule in the loaded
    package are reported as not implemented rather than silently omitted."""
    executed = {o.node: o for o in outcome.node_outcomes}
    rows = []
    for node, ordinal in sorted(JUDGEMENT_CHAIN.items(), key=lambda kv: (kv[1] == 0, kv[1])):
        o = executed.get(node)
        rule_id, source_ids, locators = rule_nodes_meta.get(node, (None, (), ()))
        detail = o.detail if o is not None and isinstance(o.detail, dict) else {}
        rows.append({
            "node": node,
            "ordinal": ordinal,
            "implemented": o is not None,
            "rule_id": rule_id,
            "output": o.output if o is not None else None,
            "blockers": list(o.blockers) if o is not None else [],
            "escalation_blockers": list(o.escalation_blockers) if o is not None else [],
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

        case_file = upsert_case_file(session, org, _IntakeCase(case_id, text))
        _persist_candidate_facts(session, org, case_file, facts)

        outcome = run_chain(case_id, facts, chain_rules)
        execution_batch = f"{case_id}:{uuid.uuid4().hex[:12]}"
        persist_execution_records(
            session, org, case_file, rule_set, rule_nodes, outcome,
            execution_batch, actor="intake_llm", facts_snapshot=facts,
        )

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
        git_commit = rule_set.git_commit

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
        "rule_set_status": "unverified",
        "git_commit": git_commit,
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
