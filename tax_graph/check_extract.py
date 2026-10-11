"""Checks of the extraction boundary without a live model: a scripted responder stands in for the LLM, and the
program's own guarantees are what is tested — field specs come from the rules, a quote must be found in the
document, values are typed and unit-checked, unsupported fields stay missing.

    python -m tax_graph.check_extract          (conda env "pytorch")
"""
import io
import json
import sys
from datetime import date

from .llm.extract import BOOL, DATE, ENUM, NUMBER, extract, field_specs

DOCS = {
    "cor-2026": "Certificate of Resident Status. This is to certify that Holdco Ltd is a resident of Hong Kong for the year 2026.",
    "loan": "Loan agreement dated 2026-03-31. Interest is payable annually on 31 March. The lender holds 100% of the borrower's shares.",
    "accounts": "Balance sheet 2025: related-party debt 4,000; equity 1,000. Receipt of the dividend was remitted to Singapore.",
}

SCRIPT = {   # what the stand-in model says; the checks below are about what the program does with it
    "payee.residence_cert": ({"doc": "cor-2026", "quote": "is a resident of Hong Kong for the year 2026"}, "yes"),
    "payer.related_party_debt_equity_ratio": ({"doc": "accounts", "quote": "related-party debt 4,000; equity 1,000"}, "400%"),
    "flow.receipt_kind": ({"doc": "accounts", "quote": "was remitted to Singapore"}, "REMITTED"),
    "flow.payable_on": ({"doc": "loan", "quote": "Interest is payable annually on 31 March"}, "2026-03-31"),
    "payee.bo_safe_harbour": ({"doc": "cor-2026", "quote": "this passage is not in the certificate"}, "true"),   # fabricated quote
    "flow.is_equipment_lease": ({"doc": "loan", "quote": "Loan agreement dated 2026-03-31"}, "maybe"),           # not a boolean
}


def responder(prompt: str) -> str:
    if prompt.startswith("For each field"):
        located = {}
        for key, (passage, _) in SCRIPT.items():
            if "- %s " % key in prompt:
                located[key] = [passage]
        return json.dumps(located)
    key = prompt.split("FIELD: ", 1)[1].splitlines()[0].strip()
    passage, value = SCRIPT[key]
    return json.dumps({"value": value, "doc": passage["doc"], "quote": passage["quote"]})


def main():
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    specs = field_specs()
    bad = 0

    def check(ok, text):
        nonlocal bad
        bad += 0 if ok else 1
        out.write("%-4s %s\n" % ("ok" if ok else "FAIL", text))

    check(specs["payee.residence_cert"].kind == BOOL, "residence_cert is typed bool from its is_true predicate")
    check(specs["payer.related_party_debt_equity_ratio"].kind == NUMBER, "debt/equity ratio is typed number from its le predicate")
    check(specs["flow.receipt_kind"].kind == ENUM and "REMITTED" in specs["flow.receipt_kind"].allowed,
          "receipt_kind is an enum whose values come from the param (%s)" % "/".join(specs["flow.receipt_kind"].allowed))
    check(specs["flow.payable_on"].kind == DATE, "payable_on is a date")
    check(all(s.hint for s in specs.values() if s.key.split(".", 1)[1] in ("residence_cert", "receipt_kind")),
          "evidence hints come from 信息收集.md")

    keys = list(SCRIPT) + ["flow.immovable_ratio"]            # the last one: no passage at all
    ex = extract(DOCS, keys, responder, specs)
    check(ex.facts.get(("payee", "residence_cert")) is True, "'yes' on a bool field becomes True, with its quote kept")
    check(ex.evidence.get(("payee", "residence_cert")) == ("cor-2026", "is a resident of Hong Kong for the year 2026"), "evidence = (doc, quote)")
    check(ex.facts.get(("payer", "related_party_debt_equity_ratio")) == 400.0, "'400%' becomes 400.0 (ratio facts are percent)")
    check(ex.facts.get(("flow", "receipt_kind")) == "REMITTED", "enum value accepted")
    check(ex.facts.get(("flow", "payable_on")) == date(2026, 3, 31), "ISO date parsed")
    check(("payee", "bo_safe_harbour") not in ex.facts and "payee.bo_safe_harbour" in ex.missing,
          "a quote not found in the document is not evidence: the field stays missing (P4)")
    check(("flow", "is_equipment_lease") not in ex.facts and any(k == "flow.is_equipment_lease" for k, _ in ex.rejected),
          "'maybe' on a bool field is rejected, not guessed")
    check("flow.immovable_ratio" in ex.missing, "a field without passages is missing, not invented")
    out.write("%d checks, %d failures\n" % (13, bad))
    out.flush()
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
