"""Deterministic orchestration of the FSIE judgement chain (pure, no DB).

The runner executes every node of the loaded rule package in ordinal order,
derives the run terminal state, and curates the run-level blocker list by
terminal mode (reviewed semantics, 2026-09-03):

- ``stop_and_escalate``  -> report the conflicting facts themselves;
- ``human_review_required`` -> report the facts a human must resolve (the
  escalation blockers of every escalated analytic node);
- ``research_only_output``  -> report the union of per-node primary blockers.

Node-level detail (all blockers per node) is preserved in the outcomes so the
persistence layer can keep a full audit trail regardless of the report mode.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from packages.rule_engine.evaluators import (
    FactView,
    NodeOutcome,
    evaluate_economic_substance,
    evaluate_human_gate,
    evaluate_income_characterisation,
    evaluate_participation_basic,
    evaluate_receipt,
    evaluate_scope,
)

# Terminal states (contract: CaseTerminalState).
RESEARCH_ONLY = "research_only_output"
HUMAN_REVIEW = "human_review_required"
ESCALATE = "stop_and_escalate"

# Nodes whose "satisfied" output progressively establishes the analytic chain.
CHAIN_GATE_NODES = ("scope", "income_characterisation", "receipt")
# The professional validation gate is recorded, never dominant.
GATE_NODE = "human_gate"


@dataclass(frozen=True)
class ChainRule:
    """Minimal, source-agnostic view of one rule node."""

    rule_id: str
    node: str
    ordinal: int
    thresholds: Mapping[str, float] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, rule: Mapping[str, Any]) -> "ChainRule":
        return cls(
            rule_id=rule["rule_id"],
            node=rule["node"],
            ordinal=rule["ordinal"],
            thresholds={t["name"]: t["value"] for t in rule.get("thresholds") or []},
        )


@dataclass(frozen=True)
class CaseExpectation:
    expected_state: str | None
    expected_blockers: tuple[str, ...] = ()


@dataclass(frozen=True)
class RunOutcome:
    case_id: str
    terminal_state: str
    blockers: tuple[str, ...]
    node_outcomes: tuple[NodeOutcome, ...]
    conflict_fields: tuple[str, ...]


def run_chain(
    case_id: str,
    facts: Mapping[str, Any],
    rules: Sequence[ChainRule],
) -> RunOutcome:
    """Execute the chain deterministically. Same input -> same output."""
    view = FactView(dict(facts))
    conflict_fields = view.conflict_fields()

    outcomes: list[NodeOutcome] = []
    chain_established = True

    for rule in sorted(rules, key=lambda r: (r.ordinal, r.node)):
        if rule.node == GATE_NODE:
            outcomes.append(evaluate_human_gate(view, rule.ordinal))
            continue
        if rule.node == "scope":
            outcome = evaluate_scope(view, rule.ordinal)
        elif rule.node == "income_characterisation":
            outcome = evaluate_income_characterisation(view, rule.ordinal)
        elif rule.node == "receipt":
            outcome = evaluate_receipt(view, rule.ordinal)
        elif rule.node == "economic_substance":
            outcome = evaluate_economic_substance(view, rule.ordinal, chain_established)
        elif rule.node == "participation_basic":
            outcome = evaluate_participation_basic(
                view, rule.ordinal, chain_established, rule.thresholds
            )
        else:
            outcome = NodeOutcome(
                rule.node, rule.ordinal, "unknown",
                detail={"note": f"no evaluator for node {rule.node!r} in L0"},
            )
        outcomes.append(outcome)
        if rule.node in CHAIN_GATE_NODES and outcome.output != "satisfied":
            chain_established = False

    analytic = [o for o in outcomes if o.node != GATE_NODE]

    if conflict_fields or any(o.output == "conflict" for o in analytic):
        terminal = ESCALATE
    elif any(o.output == "human_review_required" for o in analytic):
        terminal = HUMAN_REVIEW
    else:
        terminal = RESEARCH_ONLY

    if terminal == ESCALATE:
        blockers = conflict_fields
    elif terminal == HUMAN_REVIEW:
        merged: set[str] = set()
        for o in analytic:
            if o.output == "human_review_required":
                merged.update(o.escalation_blockers)
        blockers = tuple(sorted(merged))
    else:
        merged = set()
        for o in analytic:
            merged.update(o.blockers)
        blockers = tuple(sorted(merged))

    return RunOutcome(
        case_id=case_id,
        terminal_state=terminal,
        blockers=blockers,
        node_outcomes=tuple(outcomes),
        conflict_fields=conflict_fields,
    )


def check_expectation(outcome: RunOutcome, expectation: CaseExpectation | None) -> bool | None:
    """Compare against golden expectations; None when nothing to compare."""
    if expectation is None or expectation.expected_state is None:
        return None
    return (
        outcome.terminal_state == expectation.expected_state
        and set(outcome.blockers) == set(expectation.expected_blockers)
    )
