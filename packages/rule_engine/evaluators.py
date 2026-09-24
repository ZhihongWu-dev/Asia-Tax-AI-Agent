"""Pure per-node evaluators for the FSIE judgement chain (L0 candidate logic).

Every evaluator is a pure function: a fact view in, a node outcome out. No
database, no IO, no model calls. The encoded logic is *candidate engineering
logic* only; every rule stays ``unverified`` until a Hong Kong tax expert
reviews it (PRD s.3.3).

Design rules (reviewed 2026-09-03):

- The ``human_gate`` node (ordinal 0) is recorded but never dominates the run
  terminal state; it stamps every L0 run as professionally unvalidated.
- Conflicts pierce every short-circuit.
- Escalation to ``human_review_required`` from nodes ordinal >= 5 requires the
  analytic chain (scope -> income -> receipt) to be established first;
  otherwise the node degrades to ``unknown`` so the system never pretends to
  be close to a conclusion while scope is unsettled.
- Missing facts are never mapped to "not satisfied"; unknown stays unknown.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from packages.contracts.enums import NodeOutputStatus

# Sentinel fact values that never count as known answers.
UNRESOLVED_VALUES = {"unknown", "conflict"}

SCOPE_CORE_FACTS = ("entity_hk_business_status", "mne_group_status", "income_type")
RECEIPT_FACTS = ("receipt_location", "bank_or_account_path", "set_off_or_clearing_arrangement")
RECEIVED_IN_HK_VALUES = ("received_in_hk", "deemed_received_in_hk")
SUBSTANCE_FACTS = (
    "pure_equity_holding_entity_status",
    "entity_activity_profile",
    "hk_adequate_employees",
    "hk_adequate_premises",
    "hk_operating_expenditure_amount",
    "strategic_decision_making_location",
    "outsourcing_and_supervision",
)
PARTICIPATION_FACTS = (
    "direct_or_indirect_holding",
    "holding_percentage_pct",
    "continuous_holding_period_months",
    "investee_entity",
    "foreign_tax_on_dividend_or_underlying_profit",
    "main_purpose_tax_benefit_flag",
)
# Facts a human reviewer must resolve once the participation pathway is open
# (foreign-tax qualification under s.15N and the main-purpose judgement; the
# corresponding chain nodes 7-9 are not implemented in L0).
PARTICIPATION_JUDGEMENT_FACTS = (
    "foreign_tax_on_dividend_or_underlying_profit",
    "main_purpose_tax_benefit_flag",
)


@dataclass(frozen=True)
class FactView:
    """Read-only view of a case fact card (field name -> raw value)."""

    raw_facts: Mapping[str, Any]

    def raw(self, field_name: str) -> Any:
        return self.raw_facts.get(field_name)

    def is_conflict(self, field_name: str) -> bool:
        return self.raw_facts.get(field_name) == "conflict"

    def known(self, field_name: str) -> Any:
        """The value when it exists and is resolved; otherwise None."""
        value = self.raw_facts.get(field_name)
        if value is None or value in UNRESOLVED_VALUES:
            return None
        return value

    def conflict_fields(self) -> tuple[str, ...]:
        return tuple(sorted(f for f, v in self.raw_facts.items() if v == "conflict"))


@dataclass(frozen=True)
class NodeOutcome:
    """Structured result of one node evaluation."""

    node: str
    ordinal: int
    output: str  # NodeOutputStatus value
    blockers: tuple[str, ...] = ()
    escalation_blockers: tuple[str, ...] = ()
    detail: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        from packages.contracts.enums import values

        if self.output not in values(NodeOutputStatus):
            raise ValueError(f"output {self.output!r} is not a NodeOutputStatus")


def _conflicts_in(facts: FactView, fields: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(f for f in fields if facts.is_conflict(f))


def evaluate_human_gate(facts: FactView, ordinal: int = 0) -> NodeOutcome:
    """Professional validation gate. L0 has no expert, so it always flags
    human review; the runner records it but excludes it from terminal-state
    derivation (otherwise every L0 run would collapse into the same state)."""
    expert = facts.known("expert_decision_status")
    if expert == "satisfied":
        return NodeOutcome("human_gate", ordinal, "satisfied")
    return NodeOutcome(
        "human_gate",
        ordinal,
        "human_review_required",
        blockers=() if expert is not None else ("expert_decision_status",),
        detail={
            "note": "L0 has no Hong Kong tax expert; this gate stamps the run "
            "as professionally unvalidated. It is recorded, never dominant."
        },
    )


def evaluate_scope(facts: FactView, ordinal: int) -> NodeOutcome:
    conflicts = _conflicts_in(facts, SCOPE_CORE_FACTS)
    if conflicts:
        return NodeOutcome("scope", ordinal, "conflict", blockers=conflicts)
    entity = facts.known("entity_hk_business_status")
    mne = facts.known("mne_group_status")
    income = facts.known("income_type")
    if entity == "no" or mne == "no":
        return NodeOutcome(
            "scope", ordinal, "not_satisfied",
            detail={"note": "entity outside FSIE coverage (no HK business or not an MNE entity)"},
        )
    if income is not None and income != "dividend":
        return NodeOutcome(
            "scope", ordinal, "not_satisfied",
            detail={"note": f"income type {income!r} is outside the L0 dividend slice"},
        )
    missing = tuple(f for f in SCOPE_CORE_FACTS if facts.known(f) is None)
    if missing:
        return NodeOutcome("scope", ordinal, "unknown", blockers=missing)
    return NodeOutcome("scope", ordinal, "satisfied")


def evaluate_income_characterisation(facts: FactView, ordinal: int) -> NodeOutcome:
    conflicts = _conflicts_in(facts, ("income_type", "income_legal_character"))
    if conflicts:
        return NodeOutcome("income_characterisation", ordinal, "conflict", blockers=conflicts)
    income = facts.known("income_type")
    if income is None:
        return NodeOutcome("income_characterisation", ordinal, "unknown", blockers=("income_type",))
    if income != "dividend":
        return NodeOutcome(
            "income_characterisation", ordinal, "not_satisfied",
            detail={"income_type": income},
        )
    return NodeOutcome(
        "income_characterisation", ordinal, "satisfied",
        detail={
            "note": "supporting characterisation evidence is tracked at the "
            "evidence level (EV-INCOME-001), not chain-blocking in L0"
        },
    )


def evaluate_receipt(facts: FactView, ordinal: int) -> NodeOutcome:
    conflicts = _conflicts_in(facts, RECEIPT_FACTS)
    if conflicts:
        return NodeOutcome("receipt", ordinal, "conflict", blockers=conflicts)
    location = facts.known("receipt_location")
    if location is None:
        return NodeOutcome("receipt", ordinal, "unknown", blockers=("receipt_location",))
    # s.15I charges specified foreign-sourced income that is received, or
    # deemed received, in Hong Kong; both establish the receipt node.
    if location in RECEIVED_IN_HK_VALUES:
        return NodeOutcome("receipt", ordinal, "satisfied", detail={"receipt_location": location})
    return NodeOutcome(
        "receipt", ordinal, "not_satisfied",
        detail={"receipt_location": location, "note": "income not received in Hong Kong"},
    )


def evaluate_economic_substance(facts: FactView, ordinal: int, chain_established: bool) -> NodeOutcome:
    conflicts = _conflicts_in(facts, SUBSTANCE_FACTS)
    if conflicts:
        return NodeOutcome("economic_substance", ordinal, "conflict", blockers=conflicts)
    present = tuple(f for f in SUBSTANCE_FACTS if facts.known(f) is not None)
    if not present:
        # No substance information at all: report the representative
        # mandatory-evidence fact (EV-SUBSTANCE-001), nothing more.
        return NodeOutcome(
            "economic_substance", ordinal, "unknown",
            blockers=("hk_adequate_employees",),
            detail={"note": "no substance facts provided"},
        )
    missing = tuple(f for f in SUBSTANCE_FACTS if facts.known(f) is None)
    if not chain_established:
        return NodeOutcome("economic_substance", ordinal, "unknown", blockers=missing)
    # Sufficiency ("adequate") depends on the Commissioner's opinion (s.15K);
    # it is never mechanically provable in L0 -> escalate.
    return NodeOutcome(
        "economic_substance", ordinal, "human_review_required",
        escalation_blockers=missing,
        detail={"note": "substance sufficiency under s.15K is a human judgement"},
    )


def evaluate_participation_basic(
    facts: FactView, ordinal: int, chain_established: bool, thresholds: Mapping[str, float]
) -> NodeOutcome:
    conflicts = _conflicts_in(facts, PARTICIPATION_FACTS)
    if conflicts:
        return NodeOutcome("participation_basic", ordinal, "conflict", blockers=conflicts)

    min_pct = thresholds.get("minimum_holding_percentage_pct")
    min_months = thresholds.get("minimum_continuous_holding_period_months")
    if min_pct is None or min_months is None:
        return NodeOutcome(
            "participation_basic", ordinal, "unknown",
            detail={"note": "s.15M(2) thresholds missing from the rule package"},
        )

    pct = facts.known("holding_percentage_pct")
    months = facts.known("continuous_holding_period_months")
    if pct is None or months is None:
        missing = tuple(
            f for f, v in (("holding_percentage_pct", pct), ("continuous_holding_period_months", months)) if v is None
        )
        return NodeOutcome("participation_basic", ordinal, "unknown", blockers=missing)

    if pct < min_pct or months < min_months:
        return NodeOutcome(
            "participation_basic", ordinal, "condition_not_demonstrated",
            detail={
                "holding_percentage_pct": pct,
                "continuous_holding_period_months": months,
                "minimum_holding_percentage_pct": min_pct,
                "minimum_continuous_holding_period_months": min_months,
                "statute_locator": "s.15M(2)",
            },
        )

    # Thresholds met. The remaining conditions (foreign-tax qualification under
    # s.15N, anti-hybrid, main purpose) live in chain nodes 7-9, which L0 does
    # not implement; they are expert judgement territory either way.
    if chain_established:
        return NodeOutcome(
            "participation_basic", ordinal, "human_review_required",
            escalation_blockers=PARTICIPATION_JUDGEMENT_FACTS,
            detail={
                "note": "participation thresholds met; foreign-tax qualification "
                "(s.15N(2)/(7)) and main-purpose judgement (s.15N(4)) require "
                "human review; chain nodes 7-9 not implemented in L0",
                "statute_locator": "s.15M(2)",
            },
        )
    # Chain not established: stay unknown and report only the missing
    # mandatory-evidence fact (EV-TAX-001), not the full judgement set.
    return NodeOutcome(
        "participation_basic", ordinal, "unknown",
        blockers=("foreign_tax_on_dividend_or_underlying_profit",),
    )
