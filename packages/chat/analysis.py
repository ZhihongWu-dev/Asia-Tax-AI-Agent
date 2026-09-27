"""Run existing candidate rules; cite only manifest sources and stored legal units."""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
from uuid import uuid4

from sqlalchemy import create_engine, select

from packages.contracts.enums import JUDGEMENT_CHAIN
from packages.knowledge_loader.parser import FSIE_DIR, load_rules_payload
from packages.persistence.config import get_settings
from packages.persistence.models import LegalUnit, Source
from packages.rule_engine.runner import ChainRule, run_chain
from packages.chat.store import now


def retrieve_units(locators: list[str]) -> tuple[list[dict], str]:
    engine = None
    try:
        engine = create_engine(get_settings().database_url, connect_args={"connect_timeout": 3})
        with engine.connect() as connection:
            rows = connection.execute(select(
                LegalUnit.unit_ref, LegalUnit.statute_locator, LegalUnit.text,
                Source.source_id, Source.actual_sha256,
            ).join(Source, LegalUnit.source_db_id == Source.id).where(LegalUnit.statute_locator.in_(locators))).all()
        return [{"unit_id": r.unit_ref, "locator": r.statute_locator, "text": r.text,
                 "source_id": r.source_id, "snapshot_sha256": r.actual_sha256} for r in rows], "available" if rows else "no_matching_units"
    except Exception:
        # No database details or credentials cross the API boundary.
        return [], "unavailable"
    finally:
        if engine is not None:
            engine.dispose()


def analyze(case_id: str, facts: dict, confirmed_revision: int) -> dict:
    package = load_rules_payload()
    rules = package["rules"]
    chain = [ChainRule.from_payload(r) for r in rules]
    outcome = run_chain(case_id, facts, chain)
    manifest = json.loads((FSIE_DIR / "source_manifest.json").read_text(encoding="utf-8"))
    source_ids = {s for rule in rules for s in rule.get("source_ids", [])}
    sources = [s for s in manifest["sources"] if s["source_id"] in source_ids]
    locators = sorted({t["statute_locator"] for r in rules for t in r.get("thresholds", []) if t.get("statute_locator")})
    units, retrieval_status = retrieve_units(locators)
    units = [u for u in units if u["source_id"] in source_ids]
    if retrieval_status == "available" and not units:
        retrieval_status = "no_matching_units"
    by_node = {r["node"]: r for r in rules}
    nodes = [{**asdict(n), "rule_id": by_node[n.node]["rule_id"],
              "source_ids": by_node[n.node].get("source_ids", [])} for n in outcome.node_outcomes]
    missing = [node for node, ordinal in JUDGEMENT_CHAIN.items() if ordinal > 0 and node not in by_node]
    return {
        "id": str(uuid4()), "created_at": now(), "confirmed_revision": confirmed_revision,
        "facts_snapshot": facts, "rule_version": package["rule_package_version"],
        "rules_sha256": sha256(json.dumps(package, sort_keys=True).encode()).hexdigest(),
        "rules_snapshot": package, "source_manifest_sha256": sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
        "coverage_cutoff": manifest["legal_coverage_cutoff"], "professional_validation_status": "unverified",
        "terminal_state": outcome.terminal_state, "blockers": list(outcome.blockers), "nodes": nodes,
        "missing_nodes": missing, "sources": sources, "passages": units, "retrieval_status": retrieval_status,
        "stale": False,
    }
