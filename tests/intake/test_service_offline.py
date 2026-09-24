"""Shape of the structured analysis, offline (deterministic chain only)."""

from __future__ import annotations

from packages.contracts.enums import JUDGEMENT_CHAIN
from packages.intake.service import _chain_rows, _fact_rows
from packages.knowledge_loader import parser
from packages.rule_engine.runner import ChainRule, run_chain

RULES = parser.load_rules_payload()["rules"]
CHAIN_RULES = [ChainRule.from_payload(r) for r in RULES]
META = {r["node"]: (r["rule_id"], tuple(r["source_ids"]), ()) for r in RULES}


def test_chain_rows_list_every_canonical_node_with_the_gate_last():
    outcome = run_chain("T", {"income_type": "dividend"}, CHAIN_RULES)
    rows = _chain_rows(outcome, META)
    assert [r["node"] for r in rows][-1] == "human_gate"
    assert [r["ordinal"] for r in rows[:-1]] == list(range(1, 11))
    assert {r["node"] for r in rows} == set(JUDGEMENT_CHAIN)


def test_nodes_without_a_rule_are_reported_as_not_implemented():
    outcome = run_chain("T", {}, CHAIN_RULES)
    rows = {r["node"]: r for r in _chain_rows(outcome, META)}
    loaded = {r["node"] for r in RULES}
    for node, row in rows.items():
        assert row["implemented"] is (node in loaded), node
        if not row["implemented"]:
            assert row["output"] is None and row["rule_id"] is None


def test_fact_rows_separate_values_from_sentinel_states():
    rows = {r["field"]: r for r in _fact_rows({"income_type": "dividend", "receipt_location": "conflict",
                                               "mne_group_status": "unknown"})}
    assert rows["income_type"] == rows["income_type"] | {"value": "dividend", "status": "ai_candidate"}
    assert rows["receipt_location"]["value"] is None and rows["receipt_location"]["status"] == "conflict"
    assert rows["mne_group_status"]["status"] == "unknown"
    assert rows["receipt_location"]["statute_locator"] == "s.15I"
