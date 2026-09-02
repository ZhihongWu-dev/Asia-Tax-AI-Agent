"""The chain runner must reproduce every golden case exactly."""

from __future__ import annotations

import pytest

from packages.knowledge_loader import parser
from packages.rule_engine.runner import (
    CaseExpectation,
    ChainRule,
    check_expectation,
    run_chain,
)


@pytest.fixture(scope="module")
def chain_rules() -> list[ChainRule]:
    return [ChainRule.from_payload(r) for r in parser.load_rules_payload()["rules"]]


@pytest.fixture(scope="module")
def golden_cases() -> list[dict]:
    return parser.load_cases_payload()["cases"]


def test_all_golden_cases_reproduce_exactly(chain_rules, golden_cases):
    for case in golden_cases:
        outcome = run_chain(case["case_id"], case["facts"], chain_rules)
        assert outcome.terminal_state == case["expected_state"], case["case_id"]
        assert set(outcome.blockers) == set(case["expected_blockers"]), case["case_id"]


def test_check_expectation_scores_golden_cases(chain_rules, golden_cases):
    for case in golden_cases:
        outcome = run_chain(case["case_id"], case["facts"], chain_rules)
        expectation = CaseExpectation(
            expected_state=case["expected_state"],
            expected_blockers=tuple(case["expected_blockers"]),
        )
        assert check_expectation(outcome, expectation) is True, case["case_id"]


def test_run_is_deterministic(chain_rules, golden_cases):
    for case in golden_cases:
        first = run_chain(case["case_id"], case["facts"], chain_rules)
        second = run_chain(case["case_id"], case["facts"], chain_rules)
        assert first == second


def test_human_gate_does_not_dominate_the_terminal_state(chain_rules):
    """Only the gate fires human_review_required; analytic nodes stay
    unknown/satisfied -> terminal must remain research_only_output."""
    facts = {
        "entity_hk_business_status": "yes",
        "mne_group_status": "yes",
        "income_type": "dividend",
        "receipt_location": "received_in_hk",
    }
    outcome = run_chain("GATE-ONLY", facts, chain_rules)
    gate = next(o for o in outcome.node_outcomes if o.node == "human_gate")
    assert gate.output == "human_review_required"
    assert outcome.terminal_state == "research_only_output"


def test_conflict_pierces_short_circuit(chain_rules):
    """Scope unsettled + a conflicting fact -> stop_and_escalate, not research."""
    facts = {
        "entity_hk_business_status": "yes",
        "mne_group_status": "unknown",
        "income_type": "dividend",
        "receipt_location": "conflict",
    }
    outcome = run_chain("CONFLICT-PIERCE", facts, chain_rules)
    assert outcome.terminal_state == "stop_and_escalate"
    assert outcome.blockers == ("receipt_location",)


def test_six_nodes_are_executed_per_run(chain_rules, golden_cases):
    outcome = run_chain("NODE-COUNT", golden_cases[0]["facts"], chain_rules)
    assert len(outcome.node_outcomes) == 6
    assert [o.node for o in outcome.node_outcomes][0] == "human_gate"
