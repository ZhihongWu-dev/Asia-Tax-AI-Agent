"""End-to-end check of the engine on every template x case (场景.md §4 校验): the candidate table with its bounds,
the pending items of the best row, and the invariants: lo <= hi, costs >= 0, the best row is not dominated, the
client's own floor labels leave nothing to claim (roundtrip), role views add up to the group total, and scaling all
amounts scales both bounds.

    python -m tax_graph.check_engine          (conda env "pytorch")
"""
import io
import sys
from dataclasses import replace
from datetime import date

from .cases import BASE_A, CASE_A, CASE_A_PAID, EVENT_A, EVENT_A_PAID, SCENARIOS
from .claims import _tax
from .engine import RULES, CaseCtx, EX_POST, bounds
from .model import HoldEdge
from .ex_ante import ex_ante
from .ex_post import ex_post
from .scenarios import GROUP, HOLD, HOLDING, OP, TEMPLATES, ULT, views


def run_scenario(out, name, template, case, event, subject=GROUP):
    res = ex_ante(template, event, case, subject=subject)
    vars_ = template.vars(event)
    bad = 0
    out.write("\n== %s (%s; subject %s)\n%-36s %9s %9s %9s %9s %5s %5s %8s %4s %s\n" % (
        name, template.name, subject, "candidate", "lo", "hi", "share@lo", "share@hi", "disc", "plan", "fragile", "ent", "dominated"))
    for r in res.table:
        out.write("%-36s %9.2f %9.2f %9.2f %9.2f %5d %5d %8.2f %4d %s\n" % (
            "/".join(str(r.cand.get(k)) for k in vars_), r.b.lo, r.b.hi, r.subject[0], r.subject[1],
            r.n_discretion, r.n_plan, r.fragility, r.n_entities, "yes" if r.dominated else ""))
        if r.b.lo > r.b.hi + 1e-9:
            bad += 1
            out.write("    DEFECT lo > hi\n")
        if any(c < -1e-9 for c in r.b.cost.values()):
            bad += 1
            out.write("    DEFECT negative cost %s\n" % r.b.cost)
    best = res.table[0]
    out.write("best: %s  lo %.2f  hi %.2f\n" % (best.cand, best.b.lo, best.b.hi))
    for title, rows in (("needs (MISSING, by cost)", res.needs), ("conditions (PLAN / DISCRETION, by cost)", res.conditions)):
        out.write("%s:\n" % title)
        for cost, g, keys in rows:
            out.write("  %8.2f  %-40s %s\n" % (cost, g, ", ".join(keys)))
    if best.dominated:
        bad += 1
        out.write("DEFECT: best row is dominated\n")
    return res, best, bad


def main():
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    bad, n = 0, 0
    results = {}
    for name, (tname, case, event) in SCENARIOS.items():
        subject = ULT if name == "B" else GROUP                # B: the Mainland parent's own view next to the group total
        res, best, b = run_scenario(out, "scenario " + name, TEMPLATES[tname], case, event, subject)
        results[name] = (res, best)
        bad += b
        n += len(res.table)

    # roundtrip on A: the best row's own floor labels, taken as what was actually paid, leave nothing to claim
    res, best = results["A"]
    g = HOLDING.build(EVENT_A, best.cand, CASE_A)
    payable = lambda lb: round(sum(lb.flow.amount * it.effective / 100.0 for it in lb.items if not it.deduction and not it.deferred), 2)
    actual = {fid: payable(lb) for fid, lb in best.b.L_lo.items()}
    post = ex_post(g, actual, t0=date(2027, 1, 31))
    if post.claims:
        bad += 1
        out.write("\nDEFECT roundtrip: claims on own labels %s\n" % post.claims)
    else:
        out.write("\nroundtrip ok: no claim against the row's own floor labels\n")
    # ex_post on the client's present structure with the domestic rate withheld: what is recoverable
    base = HOLDING.build(EVENT_A, BASE_A, CASE_A)
    withheld = {"up1": 100.0, "up2": 0.0, "exit": 200.0}
    post = ex_post(base, withheld, t0=date(2027, 1, 31))
    out.write("ex_post on the present structure (10%% withheld on up1, 10%% on the exit gain): claims %s\n" % [
        (c.flow, c.confirmed, c.potential) for c in post.claims])
    # subject views add up: every role's share sums to the group total on the present structure
    b = bounds(base, lambda facts: CaseCtx(facts, {}, EX_POST))
    roles = sorted(base.group())
    for i, total in ((0, b.lo), (1, b.hi)):
        parts = sum(views(b, r)[i] for r in roles)
        if abs(parts - total) > 0.01:
            bad += 1
            out.write("DEFECT views: roles sum to %.2f, group %.2f\n" % (parts, total))
    out.write("views by role on the present structure (lo): %s\n" % {r: views(b, r)[0] for r in roles})
    # ex_post on E: the whole distribution compared against its parts
    tE, caseE, eventE = SCENARIOS["E"]
    resE, bestE = results["E"]
    gE = TEMPLATES[tE].build(eventE, bestE.cand, caseE)
    actualE = {fid: payable(lb) for fid, lb in bestE.b.L_lo.items() if "." not in fid}
    actualE["out"] = sum(payable(lb) for fid, lb in bestE.b.L_lo.items() if fid.startswith("out"))
    postE = ex_post(gE, actualE, t0=date(2027, 1, 31))
    if postE.claims:
        bad += 1
        out.write("DEFECT roundtrip E: %s\n" % postE.claims)
    else:
        out.write("roundtrip ok on E (split flow compared as a whole)\n")

    # settled items (场景.md §8): the Mainland withholding on up1 is paid; the structure around it is pinned, its
    # plan items are facts, the claim is what the rules would have charged, and once its clocks run out it is closed
    paid = ex_ante(HOLDING, EVENT_A_PAID, CASE_A_PAID)
    out.write("\n== scenario A-paid: %d candidates keep up1 as taxed (only the exit route is still open)\n" % len(paid.table))
    if len(paid.table) != 2 or any(r.cand[HOLD] != "HK" or r.cand["financing"] != "EQUITY" or r.cand["payment"] for r in paid.table):
        bad += 1
        out.write("DEFECT settled: candidates alter a taxed flow %s\n" % [r.cand for r in paid.table])
    by_id = {r.id: r for r in RULES}
    plans = {n.key for r in paid.table for g, ns in r.b.groups.items()
             if g[1] == "up1" and g[0] in by_id and by_id[g[0]].scope.taxing == "CN" for n in ns if n.source == "PLAN"}
    if plans:
        bad += 1
        out.write("DEFECT settled: plan items on a taxed flow %s\n" % plans)
    for c in paid.claims:
        out.write("claim %s/%s: paid %.2f, rules say [%.2f, %.2f], recoverable confirmed %.2f potential %.2f, routes %s\n" % (
            c.flow, c.jur, c.actual, c.lo, c.hi, c.confirmed, c.potential, [r[0] for r in c.routes]))
    cl = {(c.flow, c.jur): c for c in paid.claims}
    if ("up1", "CN") not in cl or cl[("up1", "CN")].potential != 0.0 or cl[("up1", "CN")].lo != 100.0:
        bad += 1
        out.write("DEFECT settled: five months of holding is a fact now, so 10%% stands and nothing is recoverable\n")
    # the same, but the holding is old enough and the holder passes less than half on (beneficial-owner factors can hold):
    # the 5% cap was available, so half the withholding is recoverable if the judgement goes the client's way
    old = replace(CASE_A_PAID, holds={**CASE_A_PAID.holds, (HOLD, OP): HoldEdge(HOLD, OP, 100.0, date(2020, 1, 1), 3000.0)})
    ev_old = replace(EVENT_A_PAID, onward=400.0)
    c = {(x.flow, x.jur): x for x in ex_ante(HOLDING, ev_old, old).claims}[("up1", "CN")]
    out.write("claim with an old holding, 40%% passed on: rules [%.2f, %.2f], potential %.2f, confirmed %.2f, clocks %s, routes %s\n" % (
        c.lo, c.hi, c.potential, c.confirmed, sorted(c.deadlines), [r[0] for r in c.routes]))
    if c.potential != 50.0 or c.confirmed != 0.0 or not c.routes:
        bad += 1
        out.write("DEFECT settled: the 5%% cap should leave 50 potentially recoverable, nothing confirmed, with a route\n")
    # closed: looked at after every Mainland clock has run out, the Mainland item keeps what was paid and raises nothing
    # (the Hong Kong side of the same flow is still open and still moves between the bounds)
    late = ex_ante(HOLDING, replace(ev_old, as_at=date(2035, 1, 1)), old)
    cn_lo, cn_hi = _tax(late.table[0].b.L_lo, "up1", "CN"), _tax(late.table[0].b.L_hi, "up1", "CN")
    if late.claims or ("up1", "CN") not in late.archived or cn_lo != 100.0 or cn_hi != 100.0:
        bad += 1
        out.write("DEFECT closed: %s %s lo %.2f hi %.2f\n" % (late.claims, late.archived, cn_lo, cn_hi))
    else:
        out.write("closed ok: after the clocks, up1/CN stays at 100 under both bounds, archived %s\n" % late.archived)

    # metamorphic: scaling all amounts by k scales both bounds by k
    k = 3.0
    money = {"amount", "accumulated_profits_share", "cost_basis", "ip_allowances_claimed", "ip_book_value",
             "ip_book_amortization"}                                    # flow amounts (D19, D22, D27)
    scaled_case = replace(CASE_A, holds={key: replace(h, cost=h.cost * k if h.cost else h.cost) for key, h in CASE_A.holds.items()},
                          flows={name: {f: (v * k if f in money else v) for f, v in fs.items()} for name, fs in CASE_A.flows.items()})
    scaled_event = replace(EVENT_A, dividend=EVENT_A.dividend * k, onward=EVENT_A.onward * k, exit=EVENT_A.exit * k)
    res_k = ex_ante(HOLDING, scaled_event, scaled_case)
    pairs = {tuple(sorted(r.cand.items())): r for r in res_k.table}
    meta = 0
    for r in res.table:
        rk = pairs[tuple(sorted(r.cand.items()))]
        if abs(rk.b.lo - k * r.b.lo) > 0.05 or abs(rk.b.hi - k * r.b.hi) > 0.05:
            meta += 1
            out.write("DEFECT metamorphic: %s  (%.2f, %.2f) vs k x (%.2f, %.2f)\n" % (r.cand, rk.b.lo, rk.b.hi, r.b.lo, r.b.hi))
    bad += meta
    out.write("metamorphic scaling %s\n" % ("ok" if not meta else "FAILED"))
    out.write("%d candidates, %d defects\n" % (n, bad))
    out.flush()
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
