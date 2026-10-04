"""Run existing candidate rules; cite only manifest sources and stored legal units."""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
from uuid import uuid4

from packages.contracts.enums import JUDGEMENT_CHAIN
from packages.knowledge_loader.parser import FSIE_DIR, load_rules_payload
from packages.chat.knowledge import read_documents, rank_documents
from packages.rule_engine.runner import ChainRule, run_chain
from packages.chat.store import now


def retrieve_units(locators: list[str]) -> tuple[list[dict], str]:
    try:
        docs = read_documents(locators=locators)
        units = [d for d in docs if d['locator'] in locators]
        return units, "available" if units else "no_matching_units"
    except Exception:
        # No database details or credentials cross the API boundary.
        return [], "unavailable"


# These are review tasks, not additional tax rules or inferred conclusions.
REVIEW_FIELDS = {
    'financial_entity_exclusion': ['regulated_financial_entity_status', 'entity_activity_profile'],
    'foreign_tax_switchover': ['foreign_tax_on_dividend_or_underlying_profit', 'foreign_nominal_tax_rate_pct', 'foreign_tax_jurisdiction'],
    'anti_hybrid': ['hybrid_mismatch_arrangement', 'underlying_tax_deductible_status'],
    'main_purpose': ['main_purpose_tax_benefit_flag', 'commercial_rationale', 'restructuring_near_income_date'],
    'compliance_filing': ['receipt_date', 'foreign_tax_credit_available', 'evidence_inventory'],
}

# Navigation references checked against the ingested ordinance text; not new rules.
NODE_LOCATORS = {
    'scope': ['s.15H(1)', 's.15I(3)'],
    'income_characterisation': ['s.15H(1)', 's.15I(1)'],
    'receipt': ['s.15H(5)', 's.15H(6)', 's.15H(7)'],
    'economic_substance': ['s.15K(1)', 's.15K(2)', 's.15K(3)'],
    'participation_basic': ['s.15M(1)', 's.15M(2)', 's.15M(3)'],
    'financial_entity_exclusion': ['s.15H(1)'],
    'foreign_tax_switchover': ['s.15N(2)', 's.15N(3)', 's.15N(6)', 's.15N(7)'],
    'anti_hybrid': ['s.15N(3)'],
    'main_purpose': ['s.15N(4)'],
    'compliance_filing': ['s.15J', 's.15S(1)', 's.15S(2)', 's.15S(3)'],
}


def provider_related_rulings(provider, context):
    from packages.agent.contracts import SearchRequest
    from packages.agent.knowledge import retrieve, display_result
    return display_result(retrieve(provider, SearchRequest(request_id=str(uuid4()), trace_id=str(uuid4()),
        query='dividend', kind='ruling'), context))


def related_rulings(facts: dict) -> dict:
    try:
        documents = read_documents(kind='ruling')
        query = 'dividend'
        if facts.get('pure_equity_holding_entity_status') == 'yes':
            query += ' pure equity holding economic substance'
        if facts.get('foreign_tax_on_dividend_or_underlying_profit') == 'yes':
            query += ' qualifying similar tax'
        ranked = rank_documents(documents, query, 'ruling', 4)
        ids = list(dict.fromkeys(d['source_id'] for d in ranked))[:2]
        # Include the entire seven-section context, especially scope and dates.
        passages = [d for d in documents if d['source_id'] in ids]
        return {'status': 'available' if passages else 'no_matching_units', 'passages': passages,
                'method': 'keyword_reference_only'}
    except Exception:
        return {'status': 'unavailable', 'passages': [], 'method': 'keyword_reference_only'}


def analyze(case_id: str, facts: dict, confirmed_revision: int, *, provider=None, context=None) -> dict:
    package = load_rules_payload()
    rules = package["rules"]
    chain = [ChainRule.from_payload(r) for r in rules]
    outcome = run_chain(case_id, facts, chain)
    manifest = json.loads((FSIE_DIR / "source_manifest.json").read_text(encoding="utf-8"))
    source_ids = {s for rule in rules for s in rule.get("source_ids", [])}
    sources = [s for s in manifest["sources"] if s["source_id"] in source_ids]
    locators = sorted({t["statute_locator"] for r in rules for t in r.get("thresholds", []) if t.get("statute_locator")})
    locators = sorted(set(locators).union(*(set(refs) for refs in NODE_LOCATORS.values())))
    bundle = None
    if provider is not None:
        from packages.agent.contracts import SearchRequest
        from packages.agent.knowledge import retrieve
        from packages.agent.dialogue import query_date
        when, date_status = query_date(facts)
        bundle = retrieve(provider, SearchRequest(request_id=str(uuid4()), trace_id=str(uuid4()),
            query='香港境外股息 FSIE 适用规则', intent='case_analysis', locators=locators,
            applicable_date=when, date_status=date_status,
            entity_type=facts.get('recipient_type') if facts.get('recipient_type') in ('company', 'individual', 'unknown') else 'unknown',
            fact_filters=[{'field_name': key, 'value': facts[key]} for key in
                          ('income_type', 'source_analysis', 'entity_hk_business_status', 'receipt_location', 'recipient_type')
                          if isinstance(facts.get(key), str) and facts[key] not in ('unknown', 'conflict')]), context)
        units, retrieval_status = bundle['passages'], bundle['status']
    else:
        units, retrieval_status = retrieve_units(locators)
    units = [u for u in units if u["source_id"] in source_ids]
    if retrieval_status == "available" and not units:
        retrieval_status = "no_matching_units"
    by_node = {r["node"]: r for r in rules}
    nodes = [{**asdict(n), "rule_id": by_node[n.node]["rule_id"],
              "source_ids": by_node[n.node].get("source_ids", []),
              "required_evidence": by_node[n.node].get("required_evidence", []),
              "fact_keys": by_node[n.node].get("required_facts", []),
              "passage_ids": [u['unit_id'] for u in units if u.get('locator') in NODE_LOCATORS.get(n.node, []) or any(
                  t.get('statute_locator') == u.get('locator') for t in by_node[n.node].get('thresholds', []))],
              } for n in outcome.node_outcomes]
    missing = [node for node, ordinal in JUDGEMENT_CHAIN.items() if ordinal > 0 and node not in by_node]
    # Research rule outputs remain inspectable, but unsupported nodes cannot appear resolved.
    if bundle is not None:
        for node in nodes:
            node['candidate_output'] = node['output']
            required = set(NODE_LOCATORS.get(node['node'], []))
            found = {u['locator'] for u in units if u['unit_id'] in node['passage_ids'] and u.get('evidence_id') in bundle['verified_evidence_ids']}
            if node['node'] == 'human_gate' or node['output'] == 'human_review_required':
                node['workflow_status'] = 'pending_final_judgment'
            elif not required.issubset(found) or bundle['is_synthetic']:
                node['workflow_status'] = 'paused_gap'
                node['output'] = 'unknown'
            elif node['output'] == 'unknown':
                node['workflow_status'] = 'waiting_user'
            else:
                node['workflow_status'] = 'pending_final_review'
    result = {
        "id": str(uuid4()), "created_at": now(), "confirmed_revision": confirmed_revision,
        "facts_snapshot": facts, "rule_version": package["rule_package_version"],
        "rules_sha256": sha256(json.dumps(package, sort_keys=True).encode()).hexdigest(),
        "rules_snapshot": package, "source_manifest_sha256": sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
        "coverage_cutoff": manifest["legal_coverage_cutoff"], "professional_validation_status": "unverified",
        "terminal_state": outcome.terminal_state, "blockers": list(outcome.blockers), "nodes": nodes,
        "missing_nodes": missing, "sources": sources, "passages": units, "retrieval_status": retrieval_status,
        "related_rulings": (provider_related_rulings(provider, context) if provider is not None else related_rulings(facts)) if facts.get('income_type') == 'dividend' else
            {'status': 'not_applicable', 'passages': [], 'method': 'keyword_reference_only'},
        "review_tasks": [{"node": node, "status": "pending_final_judgment", "fact_keys": REVIEW_FIELDS[node],
                          "passage_ids": [u['unit_id'] for u in units if u.get('locator') in NODE_LOCATORS.get(node, [])],
                          "missing_facts": [key for key in REVIEW_FIELDS[node] if key not in facts or
                                            facts[key] in ('unknown', 'conflict', None)]} for node in missing],
        "citation_status": "review_required" if any(u.get('drift') for u in units) else
            ("retrieved_unverified" if units else "missing"),
        "missing_locators": sorted(set(locators) - {u['locator'] for u in units}),
        "citation_map_version": '2026-09-27',
        "stale": False,
    }

    if bundle is not None:
        result.update(provider=bundle['provider'], is_synthetic=bundle['is_synthetic'],
                      corpus_version=bundle['corpus_version'], retrieval_id=bundle['retrieval_id'],
                      evidence_gate=bundle['coverage']['status'], evidence_gaps=bundle['gaps'],
                      workflow_status='pending_final_review')
        # The UI must never label fixture passages as authoritative tax sources.
        if bundle['is_synthetic']:
            result['sources'] = []
            result['coverage_cutoff'] = 'synthetic_test_only'
        if bundle['reason_code'] != 'evidence_available' or result['missing_locators'] or any(n.get('workflow_status') == 'paused_gap' for n in nodes):
            result['evidence_gate'] = 'insufficient'
    return result
