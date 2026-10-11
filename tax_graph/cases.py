"""The cases the checks run (场景.md §4 校验): one per template, plus the mirror case with a Mainland parent so that
every jurisdiction appears as source and as residence. Facts are stated once per role / flow name; the templates
place the roles. Nothing here is an oracle: data/gold.py snapshots what the engine says about these cases."""
from datetime import date

from .data.domain import Event
from .model import CN, HK, SG, HoldEdge
from .scenarios import BUYER, HOLD, IPCO, OP, SERVICER, ULT, Case, RoleFacts

ON = date(2026, 3, 31)

_HK_HOLDER = {"residence_cert": True, "bo_safe_harbour": False, "managed_from": HK,   # onpay ratio, MNE status, residence: derived
              "pure_equity_holding": True, "registration_filing_compliant": True,
              "payee_is_government": False, "payee_is_financial_institution": False,
              "fixed_place_in_sg": False, "sch17k_elected": False, "substance_ruled_adequate": False}
_SG_PARENT = {"residence_cert": True, "bo_safe_harbour": True, "managed_from": SG,
              "payee_is_government": False, "payee_is_financial_institution": False,
              "is_excluded_entity": False, "fixed_place_in_sg": False}
_DIV_FROM_CN = {"receipt_kind": "REMITTED", "foreign_taxed": True, "foreign_headline_rate": 25, "underlying_profits_taxed": True,
                "deductible_at_payer": False, "reinvested_in_cn": False}
_UNWIND_CN_OP = {"immovable_ratio": 10, "listed_market_trade": False, "receipt_kind": "REMITTED", "foreign_taxed": True,
                 "foreign_headline_rate": 25, "underlying_profits_taxed": False, "deductible_at_payer": False}
_EXIT_OF_CN_OP = {"immovable_ratio": 10, "listed_market_trade": False, "receipt_kind": "REMITTED", "foreign_taxed": True,
                  "foreign_headline_rate": 25, "underlying_profits_taxed": False, "deductible_at_payer": False,
                  "cn_value_ratio": 90, "cn_asset_ratio": 95, "cn_income_ratio": 95, "limited_functions_and_risks": True,
                  "foreign_tax_lower_than_cn": True, "intragroup_reorg_ratio": 0, "reorg_consideration_in_equity": False,
                  "later_cn_tax_not_reduced": False}

# A: Mainland operating company, Hong Kong holder, Singapore parent; dividend up the chain and an exit to a Mainland buyer
CASE_A = Case(
    roles={OP: RoleFacts(CN), HOLD: RoleFacts(HK, dict(_HK_HOLDER)), ULT: RoleFacts(SG, dict(_SG_PARENT)), BUYER: RoleFacts(CN)},
    holds={(ULT, HOLD): HoldEdge(ULT, HOLD, 100.0, date(2020, 1, 1), 3000.0), (HOLD, OP): HoldEdge(HOLD, OP, 100.0, date(2020, 1, 1), 3000.0)},
    flows={"up1": dict(_DIV_FROM_CN), "up2": {"receipt_kind": "REMITTED", "foreign_taxed": True, "foreign_headline_rate": 16.5},
           "exit": dict(_EXIT_OF_CN_OP),
           # the unwinding (口径 D19) if the plan takes HOLD out: HOLD's stake at market value, what HOLD then distributes
           # on its liquidation (both synthetic, test-only)
           "unwind": dict(_UNWIND_CN_OP, amount=5000.0),
           "wind": {"amount": 5000.0, "receipt_kind": "REMITTED", "foreign_taxed": True, "foreign_headline_rate": 16.5}})
EVENT_A = Event(dividend=1000.0, onward=900.0, exit=5000.0, exit_on=date(2026, 12, 31), on=ON)
BASE_A = {HOLD: HK, "financing": "EQUITY", "payment": False, "exit_route": "DIRECT"}       # the client's present structure
CASE_A.present = dict(BASE_A)

# A-paid: the same client after the dividend was paid and 10% withheld in the Mainland (no treaty claim made); the
# holder has owned OP for five months only; looked at on 2027-01-31 — the exit is still open
CASE_A_PAID = Case(
    roles={k: RoleFacts(v.loc, dict(v.attrs)) for k, v in CASE_A.roles.items()},
    holds={(ULT, HOLD): HoldEdge(ULT, HOLD, 100.0, date(2020, 1, 1), 3000.0), (HOLD, OP): HoldEdge(HOLD, OP, 100.0, date(2025, 10, 1), 3000.0)},
    flows={"up1": dict(_DIV_FROM_CN, tax_paid_on=date(2026, 4, 7)), "up2": dict(CASE_A.flows["up2"]), "exit": dict(_EXIT_OF_CN_OP)},
    present=dict(BASE_A), settled={"up1": {CN: 100.0}})
EVENT_A_PAID = Event(dividend=1000.0, onward=900.0, exit=5000.0, exit_on=date(2026, 12, 31), on=ON, as_at=date(2027, 1, 31))

# B: the mirror — Singapore operating company, Hong Kong holder, Mainland parent; the Mainland is residence here
CASE_B = Case(
    roles={OP: RoleFacts(SG, {"managed_from": SG}), HOLD: RoleFacts(HK, dict(_HK_HOLDER, after_tax_profit=2500.0, income_tax_other=0.0)),   # a pure holder: the engine derives the tax behind up2
           ULT: RoleFacts(CN, {"residence_cert": True, "bo_safe_harbour": True, "payee_is_government": False,
                               "payee_is_financial_institution": False}),
           BUYER: RoleFacts(SG, {"managed_from": SG})},
    holds={(ULT, HOLD): HoldEdge(ULT, HOLD, 100.0, date(2020, 1, 1), 3000.0), (HOLD, OP): HoldEdge(HOLD, OP, 100.0, date(2020, 1, 1), 3000.0)},
    flows={"up1": {"receipt_kind": "REMITTED", "foreign_taxed": True, "foreign_headline_rate": 17, "underlying_profits_taxed": True,
                   "deductible_at_payer": False, "underlying_tax_share": 20.5},        # 17 / 83: Singapore tax behind a full distribution
           "up2": {"receipt_kind": "REMITTED", "foreign_taxed": False, "foreign_headline_rate": 16.5},
           "exit": {"immovable_ratio": 10, "listed_market_trade": False, "receipt_kind": "REMITTED", "foreign_taxed": False,
                    "foreign_headline_rate": 17, "underlying_profits_taxed": False, "deductible_at_payer": False},
           "unwind": {"amount": 5000.0, "immovable_ratio": 10, "listed_market_trade": False, "receipt_kind": "REMITTED",   # synthetic
                      "foreign_taxed": False, "foreign_headline_rate": 17, "underlying_profits_taxed": False, "deductible_at_payer": False},
           "wind": {"amount": 5000.0, "receipt_kind": "REMITTED", "foreign_taxed": False, "foreign_headline_rate": 16.5}})
EVENT_B = Event(dividend=1000.0, onward=900.0, exit=5000.0, exit_on=date(2026, 12, 31), on=ON)

# C: royalty from the Mainland operating company to the group's IP holder in Hong Kong, both under a Singapore parent
CASE_C = Case(
    roles={OP: RoleFacts(CN), ULT: RoleFacts(SG, {"residence_cert": True, "bo_safe_harbour": True, "fixed_place_in_sg": False}),
           IPCO: RoleFacts(HK, {"residence_cert": True, "bo_safe_harbour": False, "pure_equity_holding": False, "managed_from": HK,
                                "registration_filing_compliant": True, "fixed_place_in_sg": False,
                                "substance_ruled_adequate": False, "is_excluded_entity": False})},
    holds={(ULT, IPCO): HoldEdge(ULT, IPCO, 100.0, date(2020, 1, 1), 100.0), (ULT, OP): HoldEdge(ULT, OP, 100.0, date(2020, 1, 1), 3000.0)},
    flows={"roy": {"is_equipment_lease": False, "is_aircraft_or_ship_lease": False, "receipt_kind": "REMITTED",
                   "foreign_taxed": True, "foreign_headline_rate": 25, "qualifying_rd_expenditure": 50.0,
                   "non_qualifying_expenditure": 50.0, "ip_used_in_hk": False, "royalty_deductible_in_hk": False,
                   "price_includes_vat": True},
           # the IP transfer step (口径 D22) if the plan moves the IP: a patent at its market value 400, IPCO's tax basis
           # 100, no Hong Kong deductions on it (bought from an associate, s16EC(2)); amounts in yuan; synthetic, test-only
           "iptx": {"amount": 400.0, "ip_kind": "PATENT", "cost_basis": 100.0, "ip_allowances_claimed": 0.0, "receipt_kind": "REMITTED",
                    "qualifying_rd_expenditure": 50.0, "non_qualifying_expenditure": 50.0, "price_includes_vat": False,
                    "instrument_used_in_cn": True, "ip_useful_life_years": 10, "cny_rate": 1.0, "ip_book_value": 100.0,
                    "ip_book_amortization": 40.0}})
EVENT_C = Event(royalty=500.0, on=ON)

# D: management services for the Mainland operating company by a group company, performed in the Mainland for 100 days
CASE_D = Case(
    roles={OP: RoleFacts(CN), ULT: RoleFacts(SG, dict(_SG_PARENT)),
           SERVICER: RoleFacts(SG, {"residence_cert": True, "fixed_place_in_cn": False, "fixed_place_in_hk": False, "managed_from": SG,
                                    "fixed_place_in_sg": True, "bo_safe_harbour": True})},
    holds={(ULT, OP): HoldEdge(ULT, OP, 100.0, date(2020, 1, 1), 3000.0), (ULT, SERVICER): HoldEdge(ULT, SERVICER, 100.0, date(2020, 1, 1), 100.0)},
    flows={"svc": {"service_location": CN, "service_days_12m": 100, "service_kind": "MANAGEMENT", "profit_margin": 20,
                   "receipt_kind": "REMITTED", "foreign_taxed": True, "foreign_headline_rate": 25}})
EVENT_D = Event(service_fee=800.0, on=ON)

# E: taking 1000 out of the Mainland operating company: dividend, capital reduction (half the capital) or liquidation
CASE_E = Case(
    roles={OP: RoleFacts(CN), HOLD: RoleFacts(HK, dict(_HK_HOLDER)), ULT: RoleFacts(SG, dict(_SG_PARENT))},
    holds={(ULT, HOLD): HoldEdge(ULT, HOLD, 100.0, date(2020, 1, 1), 3000.0), (HOLD, OP): HoldEdge(HOLD, OP, 100.0, date(2020, 1, 1), 600.0)},
    flows={"out": dict(_DIV_FROM_CN, accumulated_profits_share=600.0, reduced_capital_ratio=50.0),
           "up2": {"receipt_kind": "REMITTED", "foreign_taxed": True, "foreign_headline_rate": 16.5},
           "unwind": dict(_UNWIND_CN_OP, amount=2000.0),                                    # synthetic, test-only
           "wind": {"amount": 2000.0, "receipt_kind": "REMITTED", "foreign_taxed": True, "foreign_headline_rate": 16.5}})
EVENT_E = Event(dividend=1000.0, onward=900.0, on=ON)

SCENARIOS = {"A": ("holding", CASE_A, EVENT_A), "B": ("holding", CASE_B, EVENT_B), "C": ("ip", CASE_C, EVENT_C),
             "D": ("services", CASE_D, EVENT_D), "E": ("repatriation", CASE_E, EVENT_E)}
