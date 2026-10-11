"""Singapore section 45 withholding on a payment to a non-resident company: rate, due date, late penalty.

A consumer of the rule layer (规则层.md): the rules are compiled from official/ by tax_graph.rules.spec_sg, this
module only turns the calculator's inputs into facts and the flow result back into the calculator's fields.
Version 1 scope: payee resident in CN or HK; company, bank / financial institution or government body;
interest, royalties, rent of equipment.
"""
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional

from .params import Params
from .rules.compile import compile_rules
from .rules.eval import Flow, evaluate_flow
from .rules.model import Effect
from .rules.procedure_sg import add_months, late_penalty, roll_forward, saturday_roll   # noqa: F401 (re-exported)
from .rules.spec import SPEC
from .rules.tri import CEILING, FLOOR, Ctx

CN, HK, SG = "CN", "HK", "SG"
CORPORATE, BANK_FI, GOVERNMENT = "CORPORATE", "BANK_FI", "GOVERNMENT"
INTEREST, ROYALTY, EQUIPMENT_RENT, SERVICE_FEE = "INTEREST", "ROYALTY", "EQUIPMENT_RENT", "SERVICE_FEE"

RULES = compile_rules(SPEC, Params())


def due_dates(date_of_payment, P):
    """(nominal, statutory, practice): the 15th named in s45(4)(a); after the Interpretation Act roll; as the
    IRAS calculator shows it (Saturdays also move, an observed practice under s45(2)(a))."""
    nominal = add_months(date_of_payment, 2).replace(day=15)
    statutory = roll_forward(nominal, P)
    return nominal, statutory, saturday_roll(statutory, P)


@dataclass
class S45Result:
    dtr_rate: Optional[float]               # treaty rate in %, None = no treaty rate applies
    dtr_base_share: float                   # share of the gross amount the treaty rate applies to
    rate_without_dtr: float                 # domestic rate in %
    due_date: Optional[date] = None             # last day in IRAS practice, as its calculator shows
    due_date_statutory: Optional[date] = None   # last day under the statute; never later than due_date
    due_date_nominal: Optional[date] = None     # the 15th named in the statute, before any roll
    tax: Optional[float] = None
    penalty: Optional[float] = None
    cor_due: Optional[date] = None
    cor_rule: Optional[str] = None              # which certificate deadline applies
    conditions: List[str] = field(default_factory=list)     # pending items (needs) under the favourable bound
    cites: List[str] = field(default_factory=list)          # parameter ids read

    @property
    def effective_rate(self):
        return self.rate_without_dtr if self.dtr_rate is None else self.dtr_rate * self.dtr_base_share


def s45(country, structure, nature, period_to, fixed_place_in_sg=False, date_of_payment=None, amount=None,
        as_at=None, params=None):
    P = params or Params()
    P.used = []
    if country not in (CN, HK) or structure not in (CORPORATE, BANK_FI, GOVERNMENT) \
            or nature not in (INTEREST, ROYALTY, EQUIPMENT_RENT, SERVICE_FEE):
        raise ValueError("outside the scope of version 1: %s / %s / %s" % (country, structure, nature))
    income = INTEREST if nature == INTEREST else (SERVICE_FEE if nature == SERVICE_FEE else ROYALTY)
    facts = {
        ("payee", "payee_is_financial_institution"): structure == BANK_FI,
        ("payee", "payee_is_government"): structure == GOVERNMENT,
        ("payee", "fixed_place_in_sg"): fixed_place_in_sg,
        ("payee", "payee_in_source_jur"): False,
        ("flow", "is_equipment_lease"): nature == EQUIPMENT_RENT,
        # the calculator's DTR rate presumes a treaty-resident payee without a permanent establishment and does not ask
        # where the work is done: services in Singapore (s12(7A) otherwise excludes them), no fixed place, no 183 days
        ("payee", "residence_cert"): True,
        ("flow", "service_performed_in_source"): True,
        ("flow", "service_days_12m"): 0,
        ("flow", "claim_is_for_prior_year"): as_at is not None and period_to.year < as_at.year,
        ("flow", "date_of_payment"): date_of_payment,
        ("flow", "period_to"): period_to,
        ("flow", "as_at"): as_at,
    }
    f = Flow(SG, country, income, on=date_of_payment or period_to)
    lo = evaluate_flow(RULES, Ctx(facts), f, FLOOR, P, amount=amount)
    hi = evaluate_flow(RULES, Ctx(facts), f, CEILING, P, amount=amount)

    item = lo.item(SG)
    treaty_applied = any(r.scope.residence and r.effect in (Effect.RATE_CAP, Effect.EXEMPT) for r in lo.applied)
    res = S45Result(item.cap if treaty_applied else None, item.cap_base if treaty_applied else 1.0, item.charge_rate,
                    conditions=sorted(set(lo.needs(SG)) | set(hi.needs(SG))))
    if "filing" in lo.deadlines:
        res.due_date_nominal, res.due_date = lo.deadlines["filing"]
        res.due_date_statutory = hi.deadlines["filing"][1]
    if "cor" in lo.deadlines:
        res.cor_due, res.cor_rule = lo.deadlines["cor"][1], lo.deadline_rules["cor"]
    if amount is not None:
        res.tax = round(amount * res.effective_rate / 100.0, 2)
        res.penalty = lo.penalty
    res.cites = list(P.used)
    return res
