"""battery: a grid of cases, run end to end, judged by invariants (范围.md 自进化). Not an oracle for the law — a
harness for the pipeline.

    python -m tax_graph.battery              generate cases/battery/*.json, run them, write out/battery_report.md
    python -m tax_graph.battery --run-only   run whatever is in cases/battery/ (hand-written or generated elsewhere)

Grid: template x jurisdictions of the fixed roles x fact completeness (full / sparse) x timing (open / paid / closed) x
years. Facts come from standard packs per (role, jurisdiction) and per income, so every case is a statement, never a
guess; the sparse variant drops the facts the rules most often read so that pending lists and relevance are exercised.

Beyond the grid (J8, J9, J7, J12): boundary values — every threshold a rule compares a stated or holding-derived number
with (params.csv) is tried just below, at and just above it, on a case where the rule fires, and reported live when the
outcome differs across it; a pairwise covering array — every two yes/no facts of a template's base case take every
pair of values (yes, no, unknown) in some case; the mutation score from tax_graph.mutation (how many seeded mistakes
in the rule layer the battery notices) replaces "rules fired" as the adequacy measure. Synthetic data, test-only.

Invariants per case: no exception; lo <= hi on every row; every group cost >= 0; the best row is not dominated; scaling
all amounts by k scales both bounds by k (open cases); role views sum to the group total; one income charge item per
(flow, jurisdiction); every non-zero item carries a cite; a settled item pins its flow and raises no PLAN item of its
own jurisdiction; claims obey 0 <= confirmed <= potential <= paid. Coverage: rules that fired (cites or pending
groups) across the battery, and the ones that never did.
"""
import io
import json
import sys
import traceback
from dataclasses import replace
from datetime import date
from itertools import product
from pathlib import Path

from .data.domain import ADJUSTABLE
from .engine import EX_ANTE, RULES, CaseCtx, Defect, Reject, bounds
from .ex_ante import ex_ante
from .model import CN, HK, JURISDICTIONS, SG
from .run import load_case
from .scenarios import BUYER, CLIENT, GROUP, HOLD, IPCO, LENDER, OP, SERVICER, TEMPLATES, ULT, views

OUT = Path("out")
DIR = Path("cases") / "battery"
ON = "2026-03-31"

ENTITY = {
    CN: {"managed_from": CN, "vat_general_taxpayer": True, "payee_is_government": False, "payee_is_financial_institution": False,
         "related_party_volume": 60000000.0, "tp_documentation_provided": True, "after_tax_profit": 8000000.0,
         "related_party_debt_equity_ratio": 1.5,
         "income_tax_other": 2666666.67,                                   # 25% on 10.67m: synthetic, test-only
         # Pillar Two figures of a Mainland entity (an IIR abroad computes the Mainland's top-up, 口径 D20): 25% covered
         # taxes, so the CbC simplified ETR meets the safe harbour; synthetic, test-only
         "globe_income": 10666666.67, "covered_taxes_other": 2666666.67, "payroll": 10000000.0, "tangible_assets": 20000000.0,
         "p2_qualified_cbcr_cn": True, "p2_tcsh_history_cn": True, "p2_cbcr_revenue_cn": 300000000.0, "p2_cbcr_pbt_cn": 10666666.67,
         "p2_cbcr_simplified_taxes_cn": 2666666.67, "p2_dm_avg_revenue_eur_cn": 37500000.0, "p2_dm_avg_income_eur_cn": 1333333.33},
    HK: {"managed_from": HK, "residence_cert": True, "bo_safe_harbour": False, "pure_equity_holding": True, "registration_filing_compliant": True,
         "payee_is_government": False, "payee_is_financial_institution": False, "fixed_place_in_sg": False, "fixed_place_in_cn": False,
         "sch17k_elected": False, "substance_ruled_adequate": False, "after_tax_profit": 6000000.0, "income_tax_other": 1185628.74,
         "revenue": 500000000.0,
         "total_assets": 400000000.0, "employees": 120, "accounting_period_end": "2026-12-31", "globe_income": 50000000.0,
         "covered_taxes_other": 2000000.0, "group_revenue_eur": 900000000.0, "payroll": 10000000.0, "tangible_assets": 20000000.0,
         "p2_qualified_cbcr_hk": True, "p2_tcsh_history_hk": True, "p2_cbcr_revenue_hk": 500000000.0, "p2_cbcr_pbt_hk": 50000000.0,
         "p2_cbcr_simplified_taxes_hk": 2000000.0, "p2_eur_rate": 0.125, "p2_eur_rate_2027": 0.125, "p2_dm_avg_revenue_eur_hk": 62500000.0,
         "p2_dm_avg_income_eur_hk": 6250000.0},                         # CbC figures: no safe harbour test met; synthetic, test-only
    SG: {"managed_from": SG, "residence_cert": True, "bo_safe_harbour": True, "payee_is_government": False, "payee_is_financial_institution": False,
         "is_excluded_entity": False, "fixed_place_in_sg": False, "fixed_place_in_cn": False, "fixed_place_in_hk": False,
         "gst_input_fully_recoverable": True, "loan_purpose_income_producing": True, "gross_revenue": 20000000.0, "return_due_on": "2027-11-30",
         "after_tax_profit": 6000000.0, "income_tax_other": 1228915.66, "globe_income": 50000000.0, "covered_taxes_other": 4000000.0,
         "group_revenue_eur": 900000000.0,
         "payroll": 10000000.0, "tangible_assets": 20000000.0,
         "p2_qualified_cbcr_sg": True, "p2_tcsh_history_sg": True, "p2_cbcr_revenue_sg": 20000000.0, "p2_cbcr_pbt_sg": 50000000.0,
         "p2_cbcr_simplified_taxes_sg": 4000000.0, "p2_eur_rate": 0.125, "p2_eur_rate_2027": 0.125, "p2_dm_avg_revenue_eur_sg": 62500000.0,
         "p2_dm_avg_income_eur_sg": 6250000.0},                         # CbC figures: no safe harbour test met; synthetic, test-only
}
FLOW = {
    "DIVIDEND": {"receipt_kind": "REMITTED", "foreign_taxed": True, "foreign_headline_rate": 25, "underlying_profits_taxed": True,
                 "deductible_at_payer": False, "reinvested_in_cn": False, "listed_market_trade": False},
    "INTEREST": {"receipt_kind": "REMITTED", "foreign_taxed": True, "foreign_headline_rate": 25, "interest_rate": 5.0, "benchmark_rate": 5.0,
                 "lender_interest_taxable_in_hk": False, "price_includes_vat": False, "unified_borrowing_relending": False},
    "ROYALTY": {"is_equipment_lease": False, "is_aircraft_or_ship_lease": False, "receipt_kind": "REMITTED", "foreign_taxed": True,
                "foreign_headline_rate": 25, "qualifying_rd_expenditure": 50.0, "non_qualifying_expenditure": 50.0, "ip_used_in_hk": False,
                "royalty_deductible_in_hk": False, "price_includes_vat": True},
    "SERVICE_FEE": {"service_location": None, "service_days_12m": 60, "service_kind": "MANAGEMENT", "profit_margin": 20, "receipt_kind": "REMITTED",
                    "foreign_taxed": True, "foreign_headline_rate": 25, "price_includes_vat": False},
    # the IP transfer step (口径 D22): a patent sold at 2000 with a tax basis of 500, no allowances claimed so far; the
    # case's amounts are yuan; the instrument is used in the Mainland (its patents); synthetic, test-only
    "IP_TRANSFER": {"amount": 2000.0, "ip_kind": "PATENT", "cost_basis": 500.0, "ip_allowances_claimed": 0.0, "price_includes_vat": False,
                    "technology_export_restricted": False, "cny_rate": 1.0, "instrument_used_in_cn": True, "receipt_kind": "REMITTED",
                    "qualifying_rd_expenditure": 50.0, "non_qualifying_expenditure": 50.0, "ip_useful_life_years": 10,
                    "ip_book_value": 500.0, "ip_book_amortization": 200.0},
    "SHARE_TRANSFER": {"immovable_ratio": 10, "listed_market_trade": False, "receipt_kind": "REMITTED", "foreign_taxed": True,
                       "foreign_headline_rate": 25, "underlying_profits_taxed": False, "deductible_at_payer": False, "cn_value_ratio": 90,
                       "cn_asset_ratio": 95, "cn_income_ratio": 95, "limited_functions_and_risks": True, "foreign_tax_lower_than_cn": True,
                       "intragroup_reorg_ratio": 0, "reorg_consideration_in_equity": False, "later_cn_tax_not_reduced": False},
    "DISTRIBUTION": {"receipt_kind": "REMITTED", "foreign_taxed": True, "foreign_headline_rate": 25, "underlying_profits_taxed": True,
                     "deductible_at_payer": False, "reinvested_in_cn": False, "accumulated_profits_share": 600.0, "reduced_capital_ratio": 50.0},
}
SPARSE_DROP = {"residence_cert", "bo_safe_harbour", "receipt_kind", "interest_rate", "benchmark_rate", "service_days_12m", "profit_margin",
               "accumulated_profits_share", "qualifying_rd_expenditure", "related_party_debt_equity_ratio", "managed_from",
               "income_tax_other", "p2_cbcr_pbt_hk", "p2_cbcr_pbt_sg", "p2_cbcr_pbt_cn", "ip_kind", "price_includes_vat", "cost_basis"}


def pack(loc, sparse):
    a = dict(ENTITY[loc])
    if sparse:
        a = {k: v for k, v in a.items() if k not in SPARSE_DROP}
    return a


def flowpack(kind, sparse, source):
    a = dict(FLOW[kind])
    if kind == "SERVICE_FEE":
        a["service_location"] = source
    if kind == "ROYALTY" and source == HK:
        a.update(ip_used_in_hk=True, royalty_deductible_in_hk=True)          # a Hong Kong payer: the IP is used here
    if sparse:
        a = {k: v for k, v in a.items() if k not in SPARSE_DROP}
    return a


VARIANTS = {
    "ip": [("lease", {"roy": {"is_equipment_lease": True}}), ("aircraft", {"roy": {"is_aircraft_or_ship_lease": True}}),
           ("prior_year_claim", {"roy": {"claim_is_for_prior_year": True, "as_at": "2026-10-07"}}),   # the clock is read as at a date
           ("before_vat_law", {"__on__": "2025-06-30"}),   # 口径 D30: before the VAT Law the CN VAT is outside the library
           ("book_transfer", {"__ult__": "CN"}),                  # OP and a new IPCO both under a Mainland parent (口径 D28)
           # the VAT conditions decided: a Mainland general taxpayer holding the input documents, and a trademark, which no
           # technology exemption covers (口径 D23, D22) — so a negated input-credit or IP-sale rule shows
           ("vat_decided", {"__cn_attrs__": {"vat_general_taxpayer": True}, "roy": {"input_vat_documents_kept": True},
                            "iptx": {"ip_kind": "TRADEMARK", "input_vat_documents_kept": True}})],
    "financing": [("government", {"__role__": {"LENDER": "GOVERNMENT"}}), ("bank", {"__role__": {"LENDER": "BANK_FI"}}),
                  ("before_vat_law", {"__on__": "2025-06-30"})],             # 口径 D30: an outside lender bears it — a note
    "holding": [("minority", {"__hold__": 20.0}), ("listed", {"exit": {"listed_market_trade": True}}),
                # a Mainland entity taxed well below 15% (incentive rate and super deduction): no safe harbour, so a
                # Hong Kong or Singapore parent's IIR charges its top-up (口径 D20); synthetic, test-only
                ("cn_low_etr", {"__cn_attrs__": {"covered_taxes_other": 500000.0, "p2_cbcr_simplified_taxes_cn": 500000.0}}),
                ("reorg", {"exit": {"intragroup_reorg_ratio": 100, "reorg_consideration_in_equity": True, "later_cn_tax_not_reduced": True}}),
                ("reinvest", {"__years__": 2,                   # the credit is used against the next year's withholding
                              "up1": {"reinvested_in_cn": True, "reinvestment_form": "capital_increase", "direct_payment": True,
                                      "reinvestment_from_distributed_profit": True, "investee_encouraged_industry": True, "planned_holding_months": 60}}),
                ("carryforward", {"__years__": 2,               # year 1 foreign tax above the Mainland limit, room in year 2
                                  "up2": {"underlying_tax_share": 45.0}, "up2@2027": {"underlying_tax_share": 5.0}})],
    "services": [("tp_adjusted", {"svc": {"tp_adjustment_tax": 50.0, "tp_adjustment_amount": 200.0, "tp_adjustment_paid_on": "2027-09-30",
                                          "pboc_benchmark_rate": 3.45}}),
                 ("before_vat_law", {"__on__": "2025-06-30"})],
    "inbound_services": [("partial_gst", {"__role__": {"SERVICER": None}, "__payer_attrs__": {"gst_input_fully_recoverable": False, "gst_recovery_ratio": 40.0}})],
}


ROLE_FACTS = {"GOVERNMENT": {"payee_is_government": True, "government_exempt_condition_met": True},
              "BANK_FI": {"payee_is_financial_institution": True}}
EXPECTED_SILENT = {"cn.wht.statutory": "displaced by cn.wht.reduced wherever both apply (实施条例 第九十一条)"}


def apply_variant(case, variant):
    name, spec = variant
    for fname, facts in spec.items():
        if fname == "__role__":
            for role, typ in facts.items():
                if typ:
                    if role not in case["roles"]:                 # a role the plan places: pin it where the present structure has it
                        loc = case["present"].get(role) or CN
                        case["roles"][role] = {"loc": loc, "attrs": pack(loc, False)}
                    case["roles"][role]["type"] = typ
                    case["roles"][role]["attrs"].update(ROLE_FACTS.get(typ, {}))   # the packs pin these flags; the type sets them
        elif fname == "__years__":
            case["event"]["years"] = facts
        elif fname == "__on__":                               # the flows' date (before the VAT Law: the 36号 rules)
            case["event"]["on"] = facts
        elif fname == "__ult__":                              # the parent's jurisdiction (口径 D28: a Mainland parent)
            case["roles"][ULT] = {"loc": facts, "attrs": pack(facts, False)}
        elif fname == "__hold__":
            for h in case["holds"]:
                h["ratio"] = facts
        elif fname == "__payer_attrs__":
            case["roles"]["CLIENT"]["attrs"].update(facts)
        elif fname == "__cn_attrs__":                         # every role the case places in the Mainland
            for rf in case["roles"].values():
                if rf["loc"] == CN:
                    rf["attrs"].update(facts)
        else:                                                 # a flow's facts, or a repeat's own facts ("up2@2027")
            case["flows"].setdefault(fname, {}).update(facts)
    case["notes"].append("variant: " + name)
    return case


def skeletons():
    """Every template with every placement of its fixed roles, two completeness levels, three timings, one or two years."""
    for tname in TEMPLATES:
        t = TEMPLATES[tname]
        fixed = [r for r in t.fixed]
        for locs in product(JURISDICTIONS, repeat=len(fixed)):
            if tname != "inbound_services" and len(set(locs)) < len(locs):
                continue                                           # fixed roles in one jurisdiction: domestic only, not this battery
            for sparse in (False, True):
                for timing in ("open", "paid", "closed"):
                    for years in (1, 2):
                        if (sparse or years == 2) and timing != "open":
                            continue                               # keep the settled variants to the full, single-year cases
                        yield tname, dict(zip(fixed, locs)), sparse, timing, years
            if tname in ("holding", "repatriation") and len(set(locs)) == len(locs):
                # the client's own holding company in the third jurisdiction: the plan may keep it, dissolve it or move
                # its role to a new company — the unwinding (口径 D19)
                third = [j for j in JURISDICTIONS if j not in locs][0]
                for sparse, timing in ((False, "open"), (True, "open"), (False, "paid")):
                    yield tname, dict(zip(fixed, locs), **{HOLD: third}), sparse, timing, 1


def unwinding_packs(sparse, src, own):
    """The two steps when the plan takes the client's HOLD out (口径 D19): HOLD's stake in OP at market value, HOLD's
    liquidation distribution. The amounts are synthetic, test-only; the sparse case leaves them out (the planner asks)."""
    unwind, wind = flowpack("SHARE_TRANSFER", sparse, src), flowpack("DISTRIBUTION", sparse, own)
    wind.pop("reduced_capital_ratio", None)
    if not sparse:
        unwind["amount"], wind["amount"] = 4000.0, 4000.0
    return {"unwind": unwind, "wind": wind}


def make_case(tname, locs, sparse, timing, years):
    roles = {r: {"loc": l, "attrs": pack(l, sparse)} for r, l in locs.items()}
    holds, flows, event, present, settled, closed = [], {}, {"on": ON, "years": years}, {}, {}, []
    src = locs.get(OP) or locs.get(CLIENT)
    own = locs.get(HOLD)                                   # the client's own holding company (口径 D19), or none
    if tname == "holding":
        holds = [{"holder": ULT, "held": OP, "ratio": 100.0, "since": "2020-01-01", "cost": 3000.0}]
        roles[BUYER] = {"loc": [j for j in JURISDICTIONS if j != locs[OP]][0], "attrs": {"managed_from": [j for j in JURISDICTIONS if j != locs[OP]][0]}}
        event.update(dividend=1000.0, onward=900.0, exit=5000.0, exit_on="2026-12-31")
        flows = {"up1": flowpack("DIVIDEND", sparse, src), "up2": flowpack("DIVIDEND", sparse, src), "exit": flowpack("SHARE_TRANSFER", sparse, src),
                 "reorg": dict(flowpack("SHARE_TRANSFER", sparse, src), amount=4000.0)}   # the restructuring step: OP's shares, consideration (synthetic, test-only)
        present = {HOLD: None, "financing": "EQUITY", "payment": False, "exit_route": "DIRECT"}
        if own:
            holds = [{"holder": ULT, "held": HOLD, "ratio": 100.0, "since": "2020-01-01", "cost": 3000.0},
                     {"holder": HOLD, "held": OP, "ratio": 100.0, "since": "2020-01-01", "cost": 3000.0}]
            flows.pop("reorg")
            flows.update(unwinding_packs(sparse, src, own))
            present[HOLD] = own
        if timing != "open":
            settled = {"up1": {locs[OP]: 100.0}}
            flows["up1"].update(tax_paid_on=ON)
    elif tname == "ip":
        holds = [{"holder": ULT, "held": OP, "ratio": 100.0, "since": "2020-01-01", "cost": 3000.0}]
        event.update(royalty=500.0)
        flows = {"roy": flowpack("ROYALTY", sparse, src), "iptx": flowpack("IP_TRANSFER", sparse, src)}   # the step when the IP moves
        present = {IPCO: None, "payment": False}
        if timing != "open":
            present = {IPCO: [j for j in JURISDICTIONS if j not in locs.values()][0], "payment": False}
            settled = {"roy": {locs[OP]: 50.0}}
            flows["roy"].update(tax_paid_on=ON)
    elif tname == "services":
        holds = [{"holder": ULT, "held": OP, "ratio": 100.0, "since": "2020-01-01", "cost": 3000.0}]
        event.update(service_fee=800.0)
        flows = {"svc": flowpack("SERVICE_FEE", sparse, src)}
        present = {SERVICER: [j for j in JURISDICTIONS if j not in locs.values()][0], "payment": False}
        if timing != "open":
            settled = {"svc": {locs[OP]: 80.0}}
            flows["svc"].update(tax_paid_on=ON)
    elif tname == "repatriation":
        holds = [{"holder": ULT, "held": OP, "ratio": 100.0, "since": "2020-01-01", "cost": 600.0}]
        event.update(dividend=1000.0, onward=900.0)
        flows = {"out": flowpack("DISTRIBUTION", sparse, src), "up2": flowpack("DIVIDEND", sparse, src),
                 "reorg": dict(flowpack("SHARE_TRANSFER", sparse, src), amount=4000.0)}   # the restructuring step: OP's shares, consideration (synthetic, test-only)
        present = {HOLD: None, "repatriation": "DIVIDEND", "payment": False}
        if own:
            holds = [{"holder": ULT, "held": HOLD, "ratio": 100.0, "since": "2020-01-01", "cost": 3000.0},
                     {"holder": HOLD, "held": OP, "ratio": 100.0, "since": "2020-01-01", "cost": 600.0}]
            flows.pop("reorg")
            flows.update(unwinding_packs(sparse, src, own))
            present[HOLD] = own
        if timing != "open":
            settled = {"out": {locs[OP]: 100.0}}
            flows["out"].update(tax_paid_on=ON)
    elif tname == "financing":
        holds = [{"holder": ULT, "held": OP, "ratio": 100.0, "since": "2020-01-01", "cost": 3000.0}]
        event.update(interest=1000.0)
        flows = {"int": flowpack("INTEREST", sparse, src)}
        present = {LENDER: [j for j in JURISDICTIONS if j != locs[OP]][0], "payment": False}
        if timing != "open":
            settled = {"int": {locs[OP]: 100.0}}
            flows["int"].update(tax_paid_on=ON)
    elif tname == "inbound_services":
        event.update(service_fee=1000.0)
        flows = {"fee": dict(flowpack("SERVICE_FEE", sparse, src), service_onshore_share=20.0)}
        flows["fee"].pop("service_location", None)
        present = {"payment": False}
        if timing != "open":
            settled = {"fee": {locs[CLIENT]: 100.0}}
            flows["fee"].update(tax_paid_on=ON)
    if timing != "open":
        for fname in settled:
            flows[fname].update(payable_on=ON, remitted_on="2026-04-07", first_notification_on="2026-06-01",
                                assessment_notice_on="2026-06-01", determination_on="2026-07-01", tax_paid_or_secured=True,
                                authority_action="assessment", as_at="2026-10-07", period_to=ON, date_of_payment=ON)
    if timing == "closed":
        event["as_at"] = "2040-01-01"
    elif timing == "paid":
        event["as_at"] = "2026-10-07"
    name = "%s_%s_%s_%s_y%d" % (tname, "-".join("%s%s" % (r[:2], l) for r, l in locs.items()), "sparse" if sparse else "full", timing, years)
    case = {"template": tname, "subject": GROUP if tname != "inbound_services" else SERVICER,
            "members": [SERVICER] if tname == "inbound_services" else None,
            "roles": roles, "holds": holds, "flows": flows, "present": present, "settled": settled, "closed": closed, "event": event,
            "notes": ["battery: generated from fact packs; %s facts; timing %s" % ("sparse" if sparse else "full", timing)]}
    return name, case


COMPOSITES = ("holding+ip", "holding+services", "ip+services")                 # several activities in one case (scenarios.composite)
COMPOSITE_PLACEMENTS = ({OP: CN, ULT: HK}, {OP: CN, ULT: SG}, {OP: HK, ULT: CN})


def make_composite(tname, locs):
    """The parts' single cases (full facts, open, one year) merged: one group, every part's flows and structure."""
    parts = [make_case(p, locs, False, "open", 1)[1] for p in tname.split("+")]
    case = parts[0]
    for c in parts[1:]:
        for r, v in c["roles"].items():
            case["roles"].setdefault(r, v)
        for h in c["holds"]:
            if not any((x["holder"], x["held"]) == (h["holder"], h["held"]) for x in case["holds"]):
                case["holds"].append(h)
        case["flows"].update(c["flows"])
        case["event"].update(c["event"])
        case["present"].update(c["present"])
    case["template"] = tname
    case["notes"] = ["battery: composite of %s from the fact packs; full facts; timing open" % tname]
    name = "%s_%s_full_open_y1" % (tname.replace("+", "-"), "-".join("%s%s" % (r[:2], l) for r, l in locs.items()))
    return name, case


def generate():
    DIR.mkdir(parents=True, exist_ok=True)
    for old in DIR.glob("*.json"):
        old.unlink()
    n = 0
    for sk in skeletons():
        name, case = make_case(*sk)
        (DIR / (name + ".json")).write_text(json.dumps(case, ensure_ascii=False, indent=1), encoding="utf-8")
        n += 1
        tname, locs, sparse, timing, years = sk
        if not sparse and timing == "open" and years == 1 and HOLD not in locs:   # variants on the base placements only
            for variant in VARIANTS.get(tname, []):
                vname, vcase = make_case(*sk)
                vcase = apply_variant(vcase, variant)
                (DIR / ("%s_%s.json" % (vname, variant[0]))).write_text(json.dumps(vcase, ensure_ascii=False, indent=1), encoding="utf-8")
                n += 1
    for tname in COMPOSITES:
        for locs in COMPOSITE_PLACEMENTS:
            name, case = make_composite(tname, dict(locs))
            (DIR / (name + ".json")).write_text(json.dumps(case, ensure_ascii=False, indent=1), encoding="utf-8")
            n += 1
    return n


def items_of(labels):
    """Every non-nil tax item as (flow, jurisdiction, levy, amount), and every deadline as (flow, clock, date)."""
    return (tuple(sorted((fid, it.jur or "", it.levy, round(lb.flow.amount * it.effective / 100.0, 2))
                         for fid, lb in labels.items() for it in lb.items if it.effective and not it.deferred)),
            tuple(sorted((fid, name, str(d)) for fid, lb in labels.items() for name, d in (lb.deadlines or {}).items())))


def check_case(path, fired, pairs=None, summary=None):
    """Returns a list of defect strings (empty = clean). `pairs` collects (rule, flow id, flow date) where a rule fired;
    `summary` the case's candidate table (for the boundary-value liveness)."""
    defects = []
    try:
        template, case, event, subject, ticks, notes = load_case(path)
        out = ex_ante(template, event, case, ticks=ticks or None, subject=subject)
    except (Defect, Reject) as e:
        return ["%s: %s" % (type(e).__name__, e)]
    except Exception as e:                                        # noqa: BLE001
        return ["EXCEPTION %s: %s | %s" % (type(e).__name__, e, traceback.format_exc().splitlines()[-3])]
    best = out.table[0]
    if summary is not None:
        summary[Path(path).stem] = sorted((str(sorted(r.cand.items())), r.b.lo, r.b.hi, items_of(r.b.L_lo), items_of(r.b.L_hi))
                                          for r in out.table)
    for r in out.table:
        if pairs is not None:
            for labels in (r.b.L_lo, r.b.L_hi):
                for fid, lb in labels.items():
                    for rid in set(lb.applied) | {c for it in lb.items for c in it.cites}:
                        stated = lb.flow is not None and lb.flow.payer in case.roles and lb.flow.payee in case.roles
                        pairs.add((rid, fid, lb.flow.on.isoformat() if lb.flow is not None and lb.flow.on else ON, stated))
            for g_ in r.b.groups:
                if isinstance(g_[1], str):
                    pairs.add((g_[0], g_[1], None, False))
        if r.b.lo > r.b.hi + 1e-9:
            defects.append("lo > hi on %s" % r.cand)
        if any(c < -1e-9 for c in r.b.cost.values()):
            defects.append("negative cost on %s: %s" % (r.cand, {g: c for g, c in r.b.cost.items() if c < -1e-9}))
        for labels in (r.b.L_lo, r.b.L_hi):
            for fid, lb in labels.items():
                charges = {}
                for it in lb.items:
                    for c in it.cites:
                        fired.add(c)
                    if it.effective != 0 and not it.cites and it.actual is None:
                        defects.append("item without cite on %s %s" % (r.cand, fid))
                    if it.levy == "income" and not it.deduction and it.effective > 0:
                        charges[it.jur] = charges.get(it.jur, 0) + 1
                dup = [j for j, k in charges.items() if k > 1]
                if dup:
                    defects.append("two income charges on %s %s for %s" % (r.cand, fid, dup))
                fired.update(lb.applied)
        for g in r.b.groups:
            fired.add(g[0])
    if best.dominated:
        defects.append("best row dominated")
    g = template.build(event, best.cand, case)
    b = best.b
    members = g.group()
    for i, total in ((0, b.lo), (1, b.hi)):
        parts = sum(views(b, role, g)[i] for role in sorted(members))
        if abs(parts - total) > 0.05:
            defects.append("role views sum %.2f != group %.2f" % (parts, total))
    for c in out.claims or []:
        if not (0 <= c.confirmed <= c.potential + 1e-9 <= c.actual + 1e-9):
            defects.append("claim order broken on %s/%s: %s %s %s" % (c.flow, c.jur, c.confirmed, c.potential, c.actual))
    if case.settled:
        for r in out.table:
            for name in case.settled:
                for gid, ns in r.b.groups.items():
                    rid, fid = gid
                    rule = next((x for x in RULES if x.id == rid), None)
                    if fid == name and rule is not None and rule.scope.taxing in case.settled[name] and any(n.source == "PLAN" for n in ns):
                        defects.append("PLAN item on a settled jurisdiction: %s" % (gid,))
    if not case.settled and (event.years or 1) == 1 and "__thr_" not in Path(path).stem:
        k = 2.0
        MONEY_ENTITY = {"after_tax_profit", "income_tax_other", "globe_income", "covered_taxes_other", "payroll", "tangible_assets", "revenue", "total_assets",
                        "related_party_volume", "gross_revenue", "sbie", "p2_cbcr_revenue_hk", "p2_cbcr_pbt_hk", "p2_cbcr_simplified_taxes_hk",
                        "p2_cbcr_revenue_sg", "p2_cbcr_pbt_sg", "p2_cbcr_simplified_taxes_sg", "p2_carry_back_topup",
                        "p2_cbcr_revenue_cn", "p2_cbcr_pbt_cn", "p2_cbcr_simplified_taxes_cn"}
        PER_UNIT = {"p2_eur_rate", "p2_eur_rate_2027", "cny_rate"}  # EUR / yuan per unit of the case's amounts: scale inversely
        MONEY_FLOW = {"accumulated_profits_share", "arms_length_max", "tp_adjustment_tax", "tp_adjustment_amount", "consideration", "cost_basis",
                      "amount", "ip_allowances_claimed", "ip_book_value", "ip_book_amortization"}
        scaled_case = replace(case, holds={key: replace(h, cost=h.cost * k if h.cost else h.cost) for key, h in case.holds.items()},
                              flows={n: {kk: (v * k if kk in MONEY_FLOW else v / k if kk in PER_UNIT else v) for kk, v in fx.items()}
                                     for n, fx in case.flows.items()},
                              roles={r: replace(rf, attrs={kk: (v * k if kk in MONEY_ENTITY and v is not None else
                                                                 v / k if kk in PER_UNIT and v is not None else v) for kk, v in rf.attrs.items()})
                                     for r, rf in case.roles.items()})
        ev2 = replace(event, **{f: (getattr(event, f) * k if getattr(event, f) else None) for f in ("dividend", "onward", "exit", "royalty", "service_fee", "interest")})
        try:
            out2 = ex_ante(template, ev2, scaled_case, ticks=ticks or None, subject=subject)
            pairs = {tuple(sorted(r.cand.items())): r for r in out2.table}
            for r in out.table:
                rk = pairs.get(tuple(sorted(r.cand.items())))
                tol = lambda a, b: abs(a - b) > 0.05 + 1e-6 * max(abs(a), abs(b))
                if rk is None or tol(rk.b.lo, k * r.b.lo) or tol(rk.b.hi, k * r.b.hi):
                    defects.append("scaling broken on %s: (%.2f, %.2f) vs k x (%.2f, %.2f)" % (r.cand, rk.b.lo if rk else -1, rk.b.hi if rk else -1, r.b.lo, r.b.hi))
                    break
        except Exception as e:                                    # noqa: BLE001
            defects.append("scaling run failed: %s" % e)
    return defects


# ---------------------------------------------------------------- boundary values (J8, J9)
HOLD_RATIO = {"direct_ratio", "ratio", "max_ratio_12m"}          # derived from the holding edge
DERIVED = {"cfc_tax_burden_ratio", "cfc_profit_total", "onpay_ratio_12m"}   # derived from other facts: check_scope tests them


def numeric_thresholds():
    """param -> (field, kind, rule ids) for every rule leaf comparing a number with a params.csv threshold."""
    from .rules.model import Leaf, leaves
    out = {}
    for r in RULES:
        try:
            ls = leaves(r.cond)
        except TypeError:
            continue
        for x in ls:
            if isinstance(x, Leaf) and x.param and x.pred.name in ("ge", "gt", "le", "lt"):
                kind = ("hold_ratio" if x.field in HOLD_RATIO else "hold_months" if x.field == "holding_months"
                        else "derived" if x.field in DERIVED else "role" if x.on in ("payer", "payee") else "flow")
                f, k, rids = out.get(x.param, (x.field, kind, set()))
                out[x.param] = (f, k, rids | {r.id})
    return out


def _make(c, want):
    """Ticks (judgements) and yes/no facts ("FACT:on.field") that make condition c evaluate to `want`; numeric facts
    other than the threshold under test stay as the case states them."""
    from .rules.model import And, Discretion, Leaf, Not, Or
    if isinstance(c, Discretion):
        return {"DISCRETION:%s.%s" % (c.on, c.key): want}
    if isinstance(c, Leaf) and c.pred.name in ("is_true", "is_false"):
        return {"FACT:%s.%s" % (c.on, c.field): want if c.pred.name == "is_true" else not want}
    if isinstance(c, Not):
        return _make(c.x, not want)
    if isinstance(c, (And, Or)):
        out = {}
        for x in c.xs:
            out.update(_make(x, want))
        return out
    return {}


def decisive_ticks(c, target):
    """MC/DC: ticks under which the leaf `target` alone decides c — the other members of every And on its path made
    True, of every Or made False. None when target is not in c."""
    from .rules.model import And, Not, Or
    if c is target:
        return {}
    if isinstance(c, Not):
        return decisive_ticks(c.x, target)
    if isinstance(c, (And, Or)):
        for i, x in enumerate(c.xs):
            got = decisive_ticks(x, target)
            if got is not None:
                for j, y in enumerate(c.xs):
                    if j != i:
                        got.update(_make(y, isinstance(c, And)))
                return got
    return None


def threshold_ticks(pid, rids):
    """The ticks for one threshold: decisive for each rule reading it, and the denials overriding those rules off."""
    from .rules.model import Leaf, leaves
    ticks = {}
    for r in RULES:
        if r.id in rids:
            for x in leaves(r.cond):
                if isinstance(x, Leaf) and x.param == pid:
                    ticks.update(decisive_ticks(r.cond, x) or {})
    for d in RULES:
        if d.effect.name == "DENY" and d.overrides & set(rids):
            ticks.update(_make(d.cond, False))
    return ticks


def _months_before(iso, n):
    d = date.fromisoformat(iso)
    y, m = divmod(d.month - 1 - int(n), 12)
    import calendar
    yy, mm = d.year + y, m + 1
    return date(yy, mm, min(d.day, calendar.monthrange(yy, mm)[1])).isoformat()


def threshold_cases(pairs_by_case):
    """For every threshold: the first open single-year grid case where one of its rules fires, tried at thr - d, thr
    and thr + d (d = 1, or 0.1 below 10). Returns ({param: [case names]}, {param: why not exercised})."""
    from .params import Params
    P = Params()
    made, skipped = {}, {}
    grid = sorted(n for n in pairs_by_case if "__" not in n and "_open_y1" in n
                  and "-" not in n.split("_")[0])                # single-template cases: a composite's other activities mask
    for pid, (field_, kind, rids) in sorted(numeric_thresholds().items()):
        if kind == "derived":
            skipped[pid] = "derived (%s): tested by check_cn_wht / check_scope" % field_
            continue
        hits = [(n, fid, on, stated) for n in grid for (rid, fid, on, stated) in pairs_by_case[n] if rid in rids and on]
        hits = [h for h in hits if h[3]] or hits                # a flow between stated companies first
        base = None
        if hits:
            first = min(h[0] for h in hits)                     # the first case by name, its earliest such flow
            on_, fid_ = min((h[2], h[1]) for h in hits if h[0] == first)
            base = (first, fid_, on_)
        if base is None:
            skipped[pid] = "no open single-year case fires %s" % ", ".join(sorted(rids))
            continue
        name, fid, on = base
        thr = float(P[pid])
        d = 1.0 if abs(thr) >= 10 else 0.1
        made[pid] = []
        ticks = threshold_ticks(pid, rids)
        for side, v in (("below", thr - d), ("at", thr), ("above", thr + d)):
            case = json.loads((DIR / (name + ".json")).read_text(encoding="utf-8"))
            case["ticks"] = dict(case.get("ticks", {}), **{k: v for k, v in ticks.items() if not k.startswith("FACT:")})
            for tk, tv in ticks.items():                        # yes/no facts next to the leaf, made decisive
                if not tk.startswith("FACT:"):
                    continue
                elem, fld = tk[5:].split(".", 1)
                bags = ([fx for fx in case["flows"].values() if fld in fx] if elem == "flow"
                        else [r["attrs"] for r in case["roles"].values() if fld in r.get("attrs", {})])
                for bag in bags:                                # stated facts only: derived ones stay the engine's
                    bag[fld] = tv
            if field_ != "group_revenue_eur":                   # isolate the threshold: a low-taxed member's top-up
                for r in case["roles"].values():                # would offset any change of its covered taxes one to one
                    if "group_revenue_eur" in r.get("attrs", {}):
                        r["attrs"]["group_revenue_eur"] = 100000000.0
            if kind == "hold_ratio":
                for h in case["holds"]:
                    h["ratio"] = v
            elif kind == "hold_months":
                for h in case["holds"]:
                    h["since"] = _months_before(on, v)
            elif kind == "role":
                hit = [r for r in case["roles"].values() if field_ in r.get("attrs", {})] or list(case["roles"].values())
                for r in hit:
                    r.setdefault("attrs", {})[field_] = v
            else:
                hit = [fx for fx in case["flows"].values() if field_ in fx] or [case["flows"].setdefault(fid.split("@")[0].split(".")[0], {})]
                for fx in hit:
                    fx[field_] = v
            case["notes"].append("boundary: %s %s = %g (%s, threshold %g)" % (kind, field_, v, side, thr))
            out_name = "%s__thr_%s_%s" % (name, pid.replace(".", "-"), side)
            (DIR / (out_name + ".json")).write_text(json.dumps(case, ensure_ascii=False, indent=1), encoding="utf-8")
            made[pid].append(out_name)
    return made, skipped


# ---------------------------------------------------------------- pairwise covering array (J7)
def covering_array(factors):
    """Strength-2 covering array, built greedily (AETG / IPOG manner), deterministic: every pair of levels of every two
    factors appears in some row. factors: [(name, [levels])]. Returns rows as {name: level}."""
    n = len(factors)
    todo = {(i, a, j, b) for i in range(n) for j in range(i + 1, n)
            for a in range(len(factors[i][1])) for b in range(len(factors[j][1]))}
    rows = []
    while todo:
        i, a, j, b = min(todo)
        row = {i: a, j: b}
        for k in range(n):
            if k in row:
                continue
            gain = lambda lv: sum(1 for m, v in row.items() if ((m, v, k, lv) if m < k else (k, lv, m, v)) in todo)
            row[k] = max(range(len(factors[k][1])), key=lambda lv: (gain(lv), -lv))
        todo -= {(m, row[m], k, row[k]) for m in row for k in row if m < k}
        rows.append({factors[k][0]: factors[k][1][row[k]] for k in range(n)})
    return rows


def pairwise_cases():
    """For each template's first full open single-year grid case: its yes/no facts (roles' and flows') as factors with
    the levels yes / no / unknown (absent); one case per row of the covering array."""
    made, stats = [], {}
    for tname in TEMPLATES:
        base = next((p.stem for p in sorted(DIR.glob(tname + "_*_full_open_y1.json"))), None)
        if base is None:
            continue
        case0 = json.loads((DIR / (base + ".json")).read_text(encoding="utf-8"))
        factors = [("role:%s.%s" % (r, k), [True, False, None]) for r, rv in sorted(case0["roles"].items())
                   for k, v in sorted(rv.get("attrs", {}).items()) if isinstance(v, bool)]
        factors += [("flow:%s.%s" % (f, k), [True, False, None]) for f, fx in sorted(case0["flows"].items())
                    for k, v in sorted(fx.items()) if isinstance(v, bool)]
        rows = covering_array(factors)
        for n_, row in enumerate(rows, 1):
            case = json.loads(json.dumps(case0))
            for key, v in row.items():
                kind, rest = key.split(":", 1)
                who, fld = rest.rsplit(".", 1)
                bag = case["roles"][who]["attrs"] if kind == "role" else case["flows"][who]
                if v is None:
                    bag.pop(fld, None)
                else:
                    bag[fld] = v
            case["notes"].append("pairwise row %d of %d over %d yes/no facts" % (n_, len(rows), len(factors)))
            name = "%s__pw%02d" % (base, n_)
            (DIR / (name + ".json")).write_text(json.dumps(case, ensure_ascii=False, indent=1), encoding="utf-8")
            made.append(name)
        k = len(factors)
        stats[tname] = {"base": base, "factors": k, "rows": len(rows), "pairs": 9 * k * (k - 1) // 2,
                        "exhaustive": 3 ** k}
    return made, stats


def _check_one(path):
    """One case, in a worker of the pool: its defects, the rules it fired, its (rule, flow, date) pairs, its table."""
    fired, pairs, summary = set(), set(), {}
    return Path(path).stem, check_case(path, fired, pairs, summary), fired, pairs, summary


def main(argv):
    """python -m tax_graph.battery [--run-only] [--jobs N]"""
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    jobs = int(argv[argv.index("--jobs") + 1]) if "--jobs" in argv else 1
    if "--run-only" not in argv:
        n = generate()
        out.write("generated %d cases in %s\n" % (n, DIR))
    fired, report, clean = set(), [], 0
    pairs_by_case, summary = {}, {}

    def run(paths_):
        nonlocal clean
        if jobs > 1:
            from multiprocessing import Pool
            with Pool(jobs) as pool:
                results = pool.map(_check_one, paths_, chunksize=1)
        else:
            results = [_check_one(p_) for p_ in paths_]
        for stem, d, f_, pairs_, summary_ in results:
            fired.update(f_)
            pairs_by_case[stem] = pairs_
            summary.update(summary_)
            if d:
                report.append((stem, d))
            else:
                clean += 1

    run(sorted(p_ for p_ in DIR.glob("*.json") if "__" not in p_.stem))
    design = {}
    if "--run-only" not in argv:
        made, skipped = threshold_cases(pairs_by_case)
        pw, pw_stats = pairwise_cases()
        design = {"thresholds": made, "skipped": skipped, "pairwise": pw_stats}
        OUT.mkdir(exist_ok=True)
        (OUT / "battery_design.json").write_text(json.dumps(design, ensure_ascii=False, indent=1), encoding="utf-8")
    elif (OUT / "battery_design.json").exists():
        design = json.loads((OUT / "battery_design.json").read_text(encoding="utf-8"))
    run(sorted(p_ for p_ in DIR.glob("*.json") if "__" in p_.stem))
    paths = sorted(DIR.glob("*.json"))
    all_ids = [r.id for r in RULES if r.effect.name not in ("NOCHARGE", "SPLIT")]     # declarations have no effect to fire
    never = sorted(rid for rid in all_ids if rid not in fired and rid not in EXPECTED_SILENT)
    lines = ["# Battery report", "", "cases: %d, clean: %d, with defects: %d" % (len(paths), clean, len(report)), "",
             "## defects"]
    for name, d in report:
        lines.append("- **%s**" % name)
        for x in d[:6]:
            lines.append("  - %s" % x)
    lines += ["", "## rules never fired (%d of %d)" % (len(never), len(all_ids))] + ["- " + r for r in never]
    lines += ["", "## silent by construction"] + ["- %s: %s" % kv for kv in sorted(EXPECTED_SILENT.items()) if kv[0] not in fired]
    thr = design.get("thresholds", {})
    live = {pid for pid, names in thr.items() if len(names) == 3 and all(n in summary for n in names)
            and summary[names[0]] != summary[names[2]]}
    lines += ["", "## boundary values (params.csv thresholds tried below / at / above)", "",
              "thresholds compared with a number: %d; tried on a case where the rule fires: %d; live (a tax item differs "
              "across the threshold): %d" % (len(thr) + len(design.get("skipped", {})), len(thr), len(live))]
    lines += ["- dead: %s — %s" % (pid, ", ".join(thr[pid][:1])) for pid in sorted(set(thr) - live)]
    lines += ["- not tried: %s — %s" % kv for kv in sorted(design.get("skipped", {}).items())]
    pw = design.get("pairwise", {})
    lines += ["", "## pairwise covering array over yes/no facts (levels yes / no / unknown)", ""]
    lines += ["- %s: %d facts, %d cases cover all %d pairs (exhaustive would be %.3g cases)" % (
        t, v["factors"], v["rows"], v["pairs"], v["exhaustive"]) for t, v in sorted(pw.items())]
    mpath = OUT / "mutation.json"
    lines += ["", "## mutation score (python -m tax_graph.mutation)", ""]
    if mpath.exists():
        m = json.loads(mpath.read_text(encoding="utf-8"))
        lines.append("killed %d of %d mutants (%.0f%%) on %d cases; by operator: %s" % (
            m["killed"], m["total"], 100.0 * m["killed"] / max(1, m["total"]), m["cases"],
            ", ".join("%s %d/%d" % (k, v[0], v[1]) for k, v in sorted(m["by_operator"].items()))))
        lines += ["- survived: %s" % x for x in m["survivors"][:60]]
    else:
        lines.append("not run yet")
    OUT.mkdir(exist_ok=True)
    (OUT / "battery_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    out.write("\n".join(lines[:3]) + "\n")
    kinds = {}
    for name, d in report:
        for x in d:
            kinds[x.split(" on ")[0].split(":")[0][:60]] = kinds.get(x.split(" on ")[0].split(":")[0][:60], 0) + 1
    for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]):
        out.write("  %4d  %s\n" % (v, k))
    out.write("rules never fired: %d of %d; thresholds live %d of %d tried; pairwise cases %d  (report: out/battery_report.md)\n" % (
        len(never), len(all_ids), len(live), len(thr), sum(v["rows"] for v in pw.values())))
    out.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
