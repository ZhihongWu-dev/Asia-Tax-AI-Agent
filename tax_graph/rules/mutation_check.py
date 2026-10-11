"""Mutation check (规则层.md §4): break the specs in known ways and confirm the checks notice.

    python -m tax_graph.rules.mutation_check

A mutant is "killed" when compile_rules refuses it or a check (check_sg_s45 on official labels, check_cn_wht on
text-derived cases) reports a difference. A surviving mutant names a behaviour no check covers; it is reported.
"""
import io
import sys
from dataclasses import replace

from .. import check_cn_wht, check_flow_tax, check_hk_tax, check_sg_s45, cn_wht, flow_tax, sg_s45
from ..params import Params
from .compile import CompileError, compile_rules
from .model import ALWAYS, And, Discretion, Effect, Leaf, is_false, is_true, lt
from .spec import SPEC
from . import spec_cn, spec_hk


def edit(spec, rule_id, **changes):
    return [replace(r, **changes) if r.id == rule_id else r for r in spec]


FIXED_PLACE_DOMESTIC_ONLY = frozenset({"sg.wht.interest", "sg.wht.royalty", "sg.wht.equipment_rent"})
BO_FLIPPED = And(Leaf("onpay_ratio_12m", lt, "cn.bo.onpay_ratio", on="payee").__class__(
    "onpay_ratio_12m", is_true, "cn.bo.onpay_ratio", on="payee"), Discretion("no_adverse_bo_factors", cites=("cn.sta.2018-09#i2",)))

MUTANTS = {
    # Singapore
    "SG: drop the bank condition on the 7% cap": edit(SPEC, "cn-sg.int.cap_bank@sg", cond=ALWAYS),
    "SG: flip the equipment-rent condition": edit(SPEC, "sg.wht.equipment_rent", cond=Leaf("is_equipment_lease", is_false)),
    "SG: fixed place no longer overrides the treaty caps": edit(SPEC, "sg.wht.fixed_place", overrides=FIXED_PLACE_DOMESTIC_ONLY),
    "SG: equipment rent charge without overrides": edit(SPEC, "sg.wht.equipment_rent", overrides=frozenset()),
    "SG: no Saturday practice": [r for r in SPEC if r.id != "sg.wht.due_practice"],
    "SG: equipment base applied as a cap": edit(SPEC, "cn-sg.roy.equipment_base@sg", effect=Effect.RATE_CAP),
    "SG: treaty cap taken instead of min(domestic, cap)": "MIN_TO_CAP",
    # Mainland
    "CN: 5% cap without the 12-month holding condition": edit(SPEC, "cn-hk.div.cap_qualified@cn",
        cond=And(spec_cn.RESIDENT, Leaf("direct_ratio", spec_cn.ge, "cn-hk.div.ratio_min"), spec_cn.BO_DIVIDEND)),
    "CN: on-payment factor ignored (always passes)": edit(SPEC, "cn-hk.div.cap_qualified@cn",
        cond=And(spec_cn.RESIDENT, spec_cn.QUALIFIED("cn-hk.div.ratio_min"), BO_FLIPPED)),
    "CN: reduced 10% rate without overriding the statutory 20%": edit(SPEC, "cn.wht.reduced", overrides=frozenset()),
    "CN: GAAR no longer reaches the reinvestment deferral": edit(SPEC, "cn.gaar", overrides=frozenset()),
    "CN: PPT no longer denies the Hong Kong caps": edit(SPEC, "cn-hk.ppt@cn", overrides=frozenset()),
    "CN: 'other' dividend cap without the residence certificate": edit(SPEC, "cn-hk.div.cap_other@cn", cond=spec_cn.BO_DIVIDEND),
    # Hong Kong
    "HK: associate base without overriding the 30% base": edit(SPEC, "hk.royalty.deemed_profit_associate", overrides=frozenset()),
    "HK: associate proviso dropped": edit(SPEC, "hk.royalty.deemed_profit_associate", cond=Leaf("payee_is_associate", is_true, on="payee")),
    "HK: FSIE charge without the MNE condition": edit(SPEC, "hk.fsie.charge", cond=Leaf("receipt_kind", spec_hk.is_in, "hk.fsie.receipt_kinds")),
    "HK: participation without the anti-hybrid leaf": edit(SPEC, "hk.fsie.participation.dividend", cond=And(
        *[x for x in spec_hk.PARTICIPATION_COND.xs if not (isinstance(x, Leaf) and x.field == "deductible_at_payer")])),
    "HK: nexus taken as a cap instead of a base": edit(SPEC, "hk.fsie.ip_nexus", effect=Effect.RATE_CAP, value="hk.fsie.nexus_cap"),
    "HK: tax certainty without the election": edit(SPEC, "hk.onshore_gain.certainty", cond=And(
        *[x for x in spec_hk.SPEC[-1].cond.xs if not (isinstance(x, Leaf) and x.field == "sch17k_elected")])),
    "HK: pure equity-holder exempt without registration compliance": edit(SPEC, "hk.fsie.substance.dividend", cond=spec_hk.Or(
        And(Leaf("pure_equity_holding", is_true, "hk.fsie.substance_pure_holding", on="payee"), spec_hk.SUBSTANCE),
        And(Leaf("pure_equity_holding", is_false, "hk.fsie.substance_non_pure_holding", on="payee"), spec_hk.SUBSTANCE))),
}


class _Quiet:
    def __init__(self):
        self.buffer = io.BytesIO()


def run(rules):
    """Run both checks silently; each gets a fresh sink because TextIOWrapper closes the buffer it wraps."""
    sg_s45.RULES = rules
    cn_wht.RULES = rules
    flow_tax.RULES = rules                 # hk_tax and check_flow_tax evaluate through flow_tax
    real, rc = sys.stdout, 0
    try:
        for check in (check_sg_s45, check_cn_wht, check_hk_tax, check_flow_tax):
            sys.stdout = _Quiet()
            rc = rc or check.main()
    finally:
        sys.stdout = real
    return rc


def main():
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    P, original = Params(), sg_s45.RULES
    killed = 0
    for name, spec in MUTANTS.items():
        try:
            if spec == "MIN_TO_CAP":
                from . import eval as ev
                saved = ev.apply

                def apply_cap(items, r, P_, facts=None, bound=None, ch=None, _saved=saved):
                    if r.effect is Effect.RATE_CAP:
                        for it in items:
                            if it.jur == r.scope.taxing:
                                it.rate = P_[r.value]
                                it.cites.append(r.id)
                        return items
                    return _saved(items, r, P_, facts, bound, ch)
                ev.apply = apply_cap
                try:
                    rc = run(original)
                finally:
                    ev.apply = saved
            else:
                rc = run(compile_rules(spec, P))
            verdict = "killed by checks" if rc else "SURVIVED"
        except CompileError as e:
            rc, verdict = 1, "killed by compile: " + str(e).splitlines()[0][:70]
        killed += bool(rc)
        out.write("%-62s %s\n" % (name, verdict))
    sg_s45.RULES = original
    cn_wht.RULES = original
    flow_tax.RULES = original
    out.write("%d of %d mutants killed\n" % (killed, len(MUTANTS)))
    out.flush()
    return 0 if killed == len(MUTANTS) else 1


if __name__ == "__main__":
    sys.exit(main())
