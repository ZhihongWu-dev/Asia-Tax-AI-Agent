"""PATHS (v1 §5): for a deviation found ex post, the ordered routes to recover it, each tied to the DEADLINE rule whose
clock governs it. Data only — no deadline is computed here; the rule layer attaches the dates to the label.

    PATHS[(taxing jurisdiction, deviation kind)] -> [Route, ...]   first feasible route is used; a flow is archived
    only when every route's clock has run out (规则层.md: several clocks, not one).
"""
from dataclasses import dataclass
from typing import Optional, Tuple

OVER_WITHHELD, RELIEF_NOT_CLAIMED, DENIED = "OVER_WITHHELD", "RELIEF_NOT_CLAIMED", "DENIED"


@dataclass(frozen=True)
class Route:
    name: str                        # deadline name on the label (see procedure_*.DEADLINE_EVALUATORS)
    via: str                         # who acts: payer (withholding agent) | taxpayer | competent_authority
    rule: str                        # the DEADLINE rule whose clock applies
    claim: Optional[str] = None      # parameter describing the claim procedure, for the narrative


PATHS = {
    ("CN", OVER_WITHHELD): (
        Route("refund", "taxpayer", "cn.refund", "cn.treaty.refund_route"),          # 2019-35 第十条; 征管法第51条 3 年
        Route("map", "competent_authority", "cn-hk.map"),                            # Arrangement 23: 3 years from first notification
        Route("map", "competent_authority", "cn-sg.map"),                            # Agreement 24
    ),
    ("CN", RELIEF_NOT_CLAIMED): (
        Route("refund", "taxpayer", "cn.refund", "cn.treaty.claim_proc"),            # self-assessed relief, refund of the excess
    ),
    ("CN", DENIED): (
        Route("review", "taxpayer", "cn.review", "cn.review.pay_first"),             # 征管法第88条 复议前置; 行政复议法第20条 60 日
        Route("map", "competent_authority", "cn-hk.map"),
        Route("map", "competent_authority", "cn-sg.map"),
    ),
    ("SG", OVER_WITHHELD): (
        Route("cor", "payer", "sg.dtr.cor", "sg.dtr.cor_due"),                       # certificate of residence by 31 Mar next year
        Route("cor", "payer", "sg.dtr.cor_prior_years", "sg.dtr.cor_due_prior_years"),
    ),
    ("SG", DENIED): (
        Route("objection", "taxpayer", "sg.objection", "sg.objection.months_company"),   # s76(3)(a) 2 months
        Route("map", "competent_authority", "cn-sg.map"),
    ),
    ("HK", DENIED): (
        Route("objection", "taxpayer", "hk.objection", "hk.objection.months"),          # s64 1 month
        Route("appeal", "taxpayer", "hk.appeal", "hk.appeal.months"),                   # s66 1 month after the determination
        Route("map", "competent_authority", "cn-hk.map"),
    ),
}


def routes(jur, kind):
    return PATHS.get((jur, kind), ())
