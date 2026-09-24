"""Node evaluators: candidate L0 logic, boundary values included."""

from __future__ import annotations

from packages.knowledge_loader import parser
from packages.rule_engine.evaluators import (
    FactView,
    evaluate_economic_substance,
    evaluate_human_gate,
    evaluate_income_characterisation,
    evaluate_participation_basic,
    evaluate_receipt,
    evaluate_scope,
)


def _thresholds() -> dict[str, float]:
    for rule in parser.load_rules_payload()["rules"]:
        if rule["node"] == "participation_basic":
            return {t["name"]: t["value"] for t in rule["thresholds"]}
    raise AssertionError("participation_basic rule missing")


def test_thresholds_are_data_driven_from_the_knowledge_package():
    thresholds = _thresholds()
    assert thresholds["minimum_holding_percentage_pct"] == 5
    assert thresholds["minimum_continuous_holding_period_months"] == 12


def test_scope_satisfied_when_core_facts_present():
    facts = FactView({"entity_hk_business_status": "yes", "mne_group_status": "yes", "income_type": "dividend"})
    assert evaluate_scope(facts, 1).output == "satisfied"


def test_scope_unknown_reports_the_missing_core_fact():
    facts = FactView({"entity_hk_business_status": "yes", "mne_group_status": "unknown", "income_type": "dividend"})
    outcome = evaluate_scope(facts, 1)
    assert outcome.output == "unknown"
    assert outcome.blockers == ("mne_group_status",)


def test_scope_not_satisfied_for_non_mne():
    facts = FactView({"entity_hk_business_status": "yes", "mne_group_status": "no", "income_type": "dividend"})
    assert evaluate_scope(facts, 1).output == "not_satisfied"


def test_scope_conflict_pierces():
    facts = FactView({"entity_hk_business_status": "conflict", "mne_group_status": "yes", "income_type": "dividend"})
    outcome = evaluate_scope(facts, 1)
    assert outcome.output == "conflict"
    assert outcome.blockers == ("entity_hk_business_status",)


def test_income_satisfied_for_dividend():
    assert evaluate_income_characterisation(FactView({"income_type": "dividend"}), 2).output == "satisfied"


def test_income_unknown_without_income_type():
    outcome = evaluate_income_characterisation(FactView({}), 2)
    assert outcome.output == "unknown"
    assert outcome.blockers == ("income_type",)


def test_receipt_satisfied_when_received_in_hk():
    assert evaluate_receipt(FactView({"receipt_location": "received_in_hk"}), 3).output == "satisfied"


def test_receipt_satisfied_when_deemed_received_in_hk():
    # s.15I read with s.15H(5): deemed receipt engages the charge like actual receipt.
    outcome = evaluate_receipt(FactView({"receipt_location": "deemed_received_in_hk"}), 3)
    assert outcome.output == "satisfied"


def test_receipt_not_satisfied_when_received_outside_hk():
    outcome = evaluate_receipt(FactView({"receipt_location": "received_outside_hk"}), 3)
    assert outcome.output == "not_satisfied"


def test_offshore_receipt_settled_by_set_off_goes_to_a_person():
    # s.15H(5)(b): a sum used to settle a Hong Kong trade debt is deemed
    # received in Hong Kong; a set-off alone cannot decide it.
    outcome = evaluate_receipt(
        FactView({"receipt_location": "received_outside_hk", "set_off_or_clearing_arrangement": "yes"}), 3
    )
    assert outcome.output == "human_review_required"
    assert set(outcome.escalation_blockers) == {"receipt_location", "set_off_or_clearing_arrangement"}


def test_offshore_receipt_without_set_off_is_not_received():
    outcome = evaluate_receipt(
        FactView({"receipt_location": "received_outside_hk", "set_off_or_clearing_arrangement": "no"}), 3
    )
    assert outcome.output == "not_satisfied"


def test_receipt_covers_every_dictionary_value():
    # Every non-sentinel enum value must map to a definite node output, so a
    # new dictionary value cannot silently fall into the wrong branch.
    import json

    dictionary = json.loads(
        (parser.REPO_ROOT / "packages/contracts/fact_dictionary/hk_fsie_fact_fields.v0.json").read_text(encoding="utf-8")
    )
    spec = next(f for f in dictionary["fields"] if f["field_name"] == "receipt_location")
    expected = {
        "received_in_hk": "satisfied",
        "deemed_received_in_hk": "satisfied",
        "received_outside_hk": "not_satisfied",
        "unknown": "unknown",
        "conflict": "conflict",
    }
    assert set(spec["enum_values"]) == set(expected)
    for value, output in expected.items():
        assert evaluate_receipt(FactView({"receipt_location": value}), 3).output == output, value


def test_receipt_conflict_reports_the_conflicting_fact():
    outcome = evaluate_receipt(FactView({"receipt_location": "conflict"}), 3)
    assert outcome.output == "conflict"
    assert outcome.blockers == ("receipt_location",)


def test_receipt_unknown_reports_receipt_location():
    outcome = evaluate_receipt(FactView({}), 3)
    assert outcome.output == "unknown"
    assert outcome.blockers == ("receipt_location",)


def test_substance_unknown_with_representative_blocker_when_no_facts():
    outcome = evaluate_economic_substance(FactView({}), 5, chain_established=True)
    assert outcome.output == "unknown"
    assert outcome.blockers == ("hk_adequate_employees",)


def test_substance_escalates_when_facts_present_and_chain_established():
    facts = FactView({"hk_adequate_employees": "yes"})
    outcome = evaluate_economic_substance(facts, 5, chain_established=True)
    assert outcome.output == "human_review_required"
    assert "hk_adequate_premises" in outcome.escalation_blockers


def test_substance_degrades_to_unknown_when_chain_not_established():
    facts = FactView({"hk_adequate_employees": "yes"})
    outcome = evaluate_economic_substance(facts, 5, chain_established=False)
    assert outcome.output == "unknown"


def test_participation_below_threshold_is_condition_not_demonstrated():
    facts = FactView({"holding_percentage_pct": 4.9, "continuous_holding_period_months": 18})
    outcome = evaluate_participation_basic(facts, 6, True, _thresholds())
    assert outcome.output == "condition_not_demonstrated"


def test_participation_short_period_is_condition_not_demonstrated():
    facts = FactView({"holding_percentage_pct": 15, "continuous_holding_period_months": 11})
    outcome = evaluate_participation_basic(facts, 6, True, _thresholds())
    assert outcome.output == "condition_not_demonstrated"


def test_participation_exact_thresholds_satisfy_the_numeric_gate():
    facts = FactView({"holding_percentage_pct": 5, "continuous_holding_period_months": 12})
    outcome = evaluate_participation_basic(facts, 6, True, _thresholds())
    assert outcome.output == "human_review_required"


def test_participation_escalation_lists_the_judgement_facts():
    facts = FactView({"holding_percentage_pct": 15, "continuous_holding_period_months": 18})
    outcome = evaluate_participation_basic(facts, 6, True, _thresholds())
    assert outcome.output == "human_review_required"
    assert outcome.escalation_blockers == (
        "foreign_tax_on_dividend_or_underlying_profit",
        "main_purpose_tax_benefit_flag",
    )


def test_participation_degrades_without_chain_and_reports_only_foreign_tax():
    facts = FactView({"holding_percentage_pct": 15, "continuous_holding_period_months": 18})
    outcome = evaluate_participation_basic(facts, 6, False, _thresholds())
    assert outcome.output == "unknown"
    assert outcome.blockers == ("foreign_tax_on_dividend_or_underlying_profit",)


def test_participation_unknown_when_threshold_facts_missing():
    outcome = evaluate_participation_basic(FactView({}), 6, True, _thresholds())
    assert outcome.output == "unknown"
    assert outcome.blockers == ("holding_percentage_pct", "continuous_holding_period_months")


def test_human_gate_flags_review_but_is_recorded_only():
    outcome = evaluate_human_gate(FactView({}), 0)
    assert outcome.output == "human_review_required"
    assert outcome.blockers == ("expert_decision_status",)
