"""Reproduce conditional HK annual-composition counterexamples, not tax advice.

The candidate rate (tax after reduction / income before excess deduction) is
NOT established policy. This probe demonstrates why source reconciliation
alone cannot prove a correct annual settlement, even with exact arithmetic.
No production policy imports this diagnostic.
"""
import argparse
import json
import sys
from fractions import Fraction as F
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from packages.income_tax.hong_kong_credit_basis import _reconcile_source_caps


def tax(income, two_tier):
    lower = min(income, F(2_000_000)) if two_tier else F(0)
    gross = lower * F(165, 2000) + (income - lower) * F(165, 1000)
    return max(F(0), gross - 3000)


def ratio(value):
    return {"numerator": str(value.numerator), "denominator": str(value.denominator)}


def probe(name, domestic, sources, two_tier=False):
    total = F(domestic) + sum((F(income) for income, _ in sources), F(0))
    rate = tax(total, two_tier) / total
    rows = []
    for income, paid in sources:
        income, paid = F(income), F(paid)
        credit = min(paid, rate * (income - paid) / (1 - rate))
        rows.append({"income": income, "foreign_tax": paid, "credit": credit,
                     "deduction": paid - credit})
    credits = sum((row["credit"] for row in rows), F(0))
    deductions = sum((row["deduction"] for row in rows), F(0))
    recomputed = tax(total - deductions, two_tier)
    bands = ((F(2_000_000), F(165,2000)), (None,F(165,1000))) if two_tier else ((None,F(165,1000)),)
    source_result = _reconcile_source_caps(domestic_income=F(domestic),
        sources=[dict(source_id=f"source_{index+1}",income=row["income"],
            foreign_tax=row["foreign_tax"],rate=rate) for index,row in enumerate(rows)],
        bands=bands,reduction=F(3000))
    reconciled = source_result["aggregate"]
    return {"case": name, "two_tier": two_tier,
            "candidate_rate": ratio(rate),
            "sources": [{key: ratio(value) for key, value in row.items()} for row in rows],
            "tax_after_deduction_before_credit": ratio(recomputed),
            "aggregate_source_credit": ratio(credits),
            "candidate_final_tax": ratio(recomputed - credits),
            "conditional_joint_reconciliation": {key:ratio(value) for key,value in reconciled.items()},
            "conditional_source_allocation_required": source_result["allocation_required"],
            "conditional_source_credit_ranges": [
                {key:ratio(value) if isinstance(value,F) else value for key,value in row.items()}
                for row in source_result["source_credit_ranges"]],
            "violates_nonnegative_annual_tax": credits > recomputed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cases = [probe("single_source_flat_rate", 0, [(100_000, 20_000)]),
             probe("two_sources_flat_rate", 0, [(50_000, 10_000), (50_000, 10_000)]),
             probe("two_tier_crossing_after_deduction", 0, [(2_100_000, 600_000)], True)]
    # Arithmetic expectations, not assertions that the candidate is lawful.
    assert all(case["violates_nonnegative_annual_tax"] for case in cases)
    assert cases[0]["candidate_final_tax"] == ratio(F(-39000, 173))
    assert cases[0]["aggregate_source_credit"] == cases[1]["aggregate_source_credit"]
    assert all(case["conditional_joint_reconciliation"]["tax_after_credit"] == ratio(F(0)) for case in cases)
    assert cases[0]["conditional_joint_reconciliation"] == cases[1]["conditional_joint_reconciliation"]
    assert not cases[0]["conditional_source_allocation_required"]
    assert cases[1]["conditional_source_allocation_required"]
    assert not cases[2]["conditional_source_allocation_required"]
    result = {"status": "conditional_counterexamples_not_approved_tax_answers",
              "unverified_assumption": "Average rate uses annual tax after reduction divided by income before excess-tax deduction.",
              "finding": "Independent source reconciliation can exceed recomputed annual tax. Resolve Section50(4) aggregate cap jointly with Section50(5) deduction and Section100 reduction before enabling annual assessment.",
              "cases": cases}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {len(cases)} conditional counterexamples; annual policy remains unverified.")


if __name__ == "__main__":
    main()
