"""The report panel (2026-11-25, agent/orchestration_cli_spec.md §17): the client report as blocks.

The program writes every part it can state from the run's products (the opening basis, Parts 2 to 6, the tables, the
flowchart, Appendix B). The analysis agent writes three blocks in report/<run_id>/blocks/:
  strategy.md  Part 1, prose; amounts as {{fig:<id>}} from frame/figures.json, provisions as {{cite:<id>|<label>}}
  plan.json    Part 7, a dated plan of steps on the program's skeleton (frame/skeleton.json), with its sources
  points.json  Appendix A, one card per point of the assumptions table, plus notes on open facts
From them the program renders briefing.md and briefing.sources.json, which review, the legal lane, report_check and the
renderer read as before, and panel.json, the view the web panel shows block by block. The agents never edit the
rendered files. Program only.
"""
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import sections as S

FIG = re.compile(r"\{\{fig:([\w.@\-]+)\}\}")
CITE = re.compile(r"\{\{cite:([^|{}]+)\|([^{}]+)\}\}")
AMOUNT = re.compile(r"(?<![\w.\-/{:])(\d{1,3}(?:,\d{3})+|\d{4,})(?:\.\d+)?(?![\w\-/])")
YEAR = re.compile(r"^(19|20)\d\d$")
AI = ("strategy", "plan", "points")
PART_OF = {"strategy": "1", "plan": "7", "points": "A"}
FILE = {"strategy": "strategy.md", "plan": "plan.json", "points": "points.json"}
DEPENDS = {"strategy": ("points", "plan"), "plan": ("points",), "points": ()}
DEADLINES = ("legal", "estimate", "none")
STEP_FIELDS = ("title", "covers", "when", "deadline", "who", "where", "documents", "how", "reason", "sources")
CARD_FIELDS = ("key", "answer", "provision", "for", "against", "reason", "confirm_by", "how")
TITLES = {"basis": "Basis of this opinion", "1": S.TITLES["1"], "2": S.TITLES["2"], "3": S.TITLES["3"], "4": S.TITLES["4"],
          "5": S.TITLES["5"], "6": S.TITLES["6"], "7": S.TITLES["7"], "A": S.TITLES["A"], "B": S.TITLES["B"]}
EFFECT = {"exempt": "the dividend is exempt", "credit": "the tax paid abroad is credited", "deduct": "the dividend is deducted",
          "nil": "no tax is charged", "include": "the dividend is taxed"}


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def rd_of(case_id, run_id):
    return S.report_dir(case_id, run_id)


def blocks_dir(case_id, run_id):
    return rd_of(case_id, run_id) / "blocks"


def is_panel_run(case_id, run_id):
    """A run whose report is written as blocks: its frame carries the figures table (every run framed since 2026-11-25)."""
    return (S.frame_dir(case_id, run_id) / "figures.json").exists()


def slug(name):
    return re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")


def write_if_changed(path, text):
    """Rewrite a rendered file only when its content changes: its time stamp is what the case status reads."""
    path = Path(path)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    if path.exists():
        path.with_name(path.name + ".prev").write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    path.write_text(text, encoding="utf-8")
    return True


# ------------------------------------------------------------ the figures the report may state
def figure_table(case_id, run_id, names, cnames=None):
    """{id: {value, text, why, ref}}: every amount the report states, from the products. Part 1 cites them as {{fig:<id>}};
    the program's parts take theirs from the same table, so every figure of the report has its source row."""
    pd = S.products_dir(case_id, run_id)
    brief, tax = S.jload(pd / "brief.json"), S.jload(pd / "tax.json")
    ccy, gross = tax.get("currency", ""), tax["amount"]
    rel = "intake/products/%s/" % run_id
    out = {}

    def put(fid, value, why, ref, kind="money", **extra):
        if value is None:
            return
        value = float(value)
        text = ("%.1f" % value) if kind == "count" else ("%s %s" % (ccy, S.money(value))).strip()
        out[fid] = {"value": value, "text": text, "why": why, "ref": rel + ref, **extra}

    put("dividend", gross, "the dividend this report is about", "tax.json")
    deltas = {d["branch_id"]: d for d in S.jload(pd / "deltas.json")["deltas"]}
    rows = {s["cand_id"]: s for s in brief.get("structures", [])}
    by_branch = {r["branch_id"]: r for r in tax["taxes"]}
    rows.setdefault(brief["as_is"]["cand_id"], {"cand_id": brief["as_is"]["cand_id"],
                                                 "all_favourable": {"amount": brief["as_is"]["amount"], "branch_id": brief["as_is"]["branch_id"]}})
    for cid, nm in names.items():
        s = rows.get(cid) or {}
        fav = s.get("all_favourable") or {}
        k = slug(nm["name"])
        put(k + ".tax", (fav.get("amount") or {}).get("floor"), "tax on this dividend through %s, every point in the group's favour" % nm["name"], "brief.json")
        row = by_branch.get(fav.get("branch_id"))
        for i, (words, amount) in enumerate(S.legs(row, gross, "floor") or [] if row else []):
            put("%s.leg%d" % (k, i + 1), amount, "tax on the step %s through %s" % (words, nm["name"]), "tax.json", step=words)
        d = deltas.get(fav.get("branch_id")) or {}
        if (d.get("saving_per_payment") or {}).get("floor") is not None and d.get("baseline_branch") != fav.get("branch_id"):
            put(k + ".saving", d["saving_per_payment"]["floor"], "saving per payment of %s against the route the money takes today" % nm["name"], "deltas.json")
        if nm["restructure"]:
            put(k + ".one_off", ((d.get("one_off_cost") or {}).get("total") or {}).get("floor"), "one-off cost of the restructuring %s needs" % nm["name"], "deltas.json")
            put(k + ".payback", d.get("payback_payments"), "payments of the same size that repay the one-off cost of %s" % nm["name"], "deltas.json", "count")
        worst = (s.get("all_unfavourable") or {}).get("amount") or {}
        put(k + ".worst", worst.get("ceiling"), "tax on this dividend through %s if every point goes against the group" % nm["name"], "brief.json")
        rem = next((x for x in s.get("if_move_not_kept") or [] if x.get("move") == "remit(false)" and x.get("amount")), None)
        if rem:
            put(k + ".brought_in", rem["amount"]["floor"], "tax through %s if the money is brought into the destination" % nm["name"], "brief.json")
        for x in s.get("if_move_not_kept") or []:
            if x.get("amount") and x.get("move", "").startswith("wait_months"):
                put(k + ".without_wait", x["amount"]["floor"], "tax through %s if the dividend is paid before the holding period has run" % nm["name"], "brief.json")
    seq = brief.get("sequence") or {}
    for side in ("this_payment", "later"):
        x = seq.get(side) or {}
        put("%s.tax" % side.replace("_payment", ""), (x.get("amount") or {}).get("floor"),
            "tax on %s" % ("this dividend" if side == "this_payment" else "each later dividend"), "brief.json")
    for d in brief.get("diagnosis") or []:
        put("current.%s" % d["kind"], (d.get("amount") or {}).get("floor"), d.get("detail") or d["kind"].replace("_", " "), "brief.json")
    for i, x in enumerate(brief.get("must_state") or []):
        put("must.%d" % (i + 1), x.get("figure"), x.get("why", ""), "brief.json")
    for c in brief.get("conduct") or []:
        if c.get("stated") is None:
            put("choice.%s.tax" % c["key"], (c.get("same_structure_if_not_kept") or {}).get("floor"),
                "tax on this dividend if the money must be brought into the destination and the plan stays", "brief.json")
            put("choice.%s.saving" % c["key"], (c.get("saving_of_switching") or {}).get("floor"),
                "saving per payment of switching structure in that case", "brief.json")
    best = (brief.get("best") or {}).get("cand_id")
    bfav = ((brief.get("best") or {}).get("all_favourable") or {})
    bt = by_branch.get(bfav.get("branch_id")) or {}
    about = bt.get("answers_about") or {}
    for key in sorted(bt.get("answers_assumed") or {}):
        sid = "against:%s:%s" % (key, about.get(key, ""))
        sc = next((x for x in brief.get("scenarios") or [] if x.get("scenario_id") == sid), None)
        amt = ((sc or {}).get("amounts") or {}).get(best) if sc else None
        if amt and bfav.get("amount"):
            put("denied.%s" % key, float(amt["ceiling"]) - float(bfav["amount"]["floor"]),
                "more tax on this dividend through the recommended structure if %s goes against the group" % S.point_words(key), "brief.json")
    return out


def skeleton(case_id, run_id, names):
    """The steps Part 7 must cover, in the order the products impose, with the deadlines and the official procedure the rule
    layer gives for them. The analysis agent turns them into a dated plan; it adds steps, never drops one."""
    pd = S.products_dir(case_id, run_id)
    brief = S.jload(pd / "brief.json")
    best = (brief.get("best") or {}).get("cand_id")
    seq = brief.get("sequence") or {}
    points = _assumed(pd, brief)
    reqs = S.jload(pd / "requirements" / ("%s.json" % best)) if best and (pd / "requirements" / ("%s.json" % best)).exists() else {"requirements": []}
    deadlines, procedure = [], []
    for q in reqs.get("requirements") or []:
        for p in q.get("reference_params") or []:
            if re.search(r"deadline|due|within|days?|month", "%s %s" % (p.get("param_id", ""), p.get("note", "")), re.I):
                item = {"rule": p.get("note") or p.get("param_id"), "cite": p.get("cite_id")}
                if item not in deadlines:
                    deadlines.append(item)
        for fr in q.get("favourable_rules") or []:
            for ru in fr.get("rules") or []:
                for doc in ru.get("procedure") or []:
                    if doc.get("kind") == "doc" and doc.get("url") and not any(x["url"] == doc["url"] for x in procedure):
                        procedure.append({"title": doc.get("title", ""), "url": doc["url"]})
    steps = []
    if points:
        steps.append({"id": "k1", "kind": "confirm", "what": "put the points the plan rests on to those who can answer them, before the payment",
                      "points": points})
    if procedure:
        steps.append({"id": "k%d" % (len(steps) + 1), "kind": "claim", "what": "claim the treaty or domestic relief the plan relies on, in the form and by the date the payer's jurisdiction asks",
                      "procedure": procedure, "deadlines": deadlines})
    this, later = seq.get("this_payment") or {}, seq.get("later") or {}
    if this and not seq.get("same"):
        now_name = names.get(this.get("cand_id"), {}).get("name", "the present route")
        steps.append({"id": "k%d" % (len(steps) + 1), "kind": "pay", "what": "pay this dividend through %s" % ("the current structure" if now_name == "Current structure" else now_name),
                      "order": (seq.get("other_order") or {}).get("why", "")})
    bn = names.get(best) or {}
    if bn.get("restructure"):
        steps.append({"id": "k%d" % (len(steps) + 1), "kind": "restructure", "what": "carry out the restructuring %s needs: %s" % (bn["name"], ", ".join(bn["restructure"])),
                      "order": "after this dividend" if this and not seq.get("same") else "before the payment"})
    for w in bn.get("move_words") or []:
        if " is received in " not in w:                   # receiving the money where it ends asks nothing of the group
            steps.append({"id": "k%d" % (len(steps) + 1), "kind": "keep", "what": w})
    if later and not seq.get("same"):
        months = re.sub(r"\D", "", seq.get("later_from") or "")
        steps.append({"id": "k%d" % (len(steps) + 1), "kind": "later", "what": "pay later dividends through %s%s" % (
            bn.get("name", "the recommended structure"), ", once the new holder has held the shares for %s months" % months if months else "")})
    return {"steps": steps, "deadlines": deadlines, "procedure": procedure}


def plan_budget(n_steps):
    """Part 7's limit (report_limits.json, the same rule report_check applies) and its share per skeleton step."""
    import report_form
    rule = report_form.limits().get("7") or {}
    if not rule:
        return {}
    part = int(rule.get("base", 0) + (rule.get("each", 0) * n_steps if rule.get("per") == "skeleton" else 0))
    return {"part": part, "per_step": part // max(1, n_steps)}


def plan_words(case_id, run_id, plan):
    """The words of each step of the plan as Part 7 prints it, against the step's share of the budget; the problem line when
    the part runs over, naming the steps over their share first."""
    import report_form
    fd = S.frame_dir(case_id, run_id)
    sk = S.jload(fd / "skeleton.json") if (fd / "skeleton.json").exists() else {}
    budget = sk.get("words") or plan_budget(len(sk.get("steps") or []))
    if not budget.get("part") or not isinstance(plan, dict):
        return {}, []
    r = Render(S.jload(fd / "figures.json") if (fd / "figures.json").exists() else {}, set())   # amounts counted as printed
    rows = []
    for i, st in enumerate(plan.get("steps") or []):
        n = report_form.counted_words(render_plan({"steps": [st]}, r))
        covers = [c for c in st.get("covers") or [] if isinstance(c, str)]
        rows.append({"step": i + 1, "covers": covers, "words": n, "share": budget["per_step"] * max(1, len(covers))})
    total = sum(r["words"] for r in rows)
    info = {"words": total, "limit": budget["part"], "steps": rows}
    if total <= budget["part"]:
        return info, []
    over = ["step %d (%d words, share %d)" % (r["step"], r["words"], r["share"]) for r in rows if r["words"] > r["share"]]
    return info, ["Part 7: %d words, limit %d.%s Cut it." % (total, budget["part"], " Over their share: %s." % "; ".join(over) if over else "")]


def _assumed(pd, brief):
    tax = S.jload(pd / "tax.json")
    fb = ((brief.get("best") or {}).get("all_favourable") or {}).get("branch_id")
    row = next((r for r in tax["taxes"] if r["branch_id"] == fb), {})
    return list((row.get("answers_assumed") or {}).keys())


def frame_extra(case_id, run_id, names, cnames, fd):
    """Written with the frame: figures.json, skeleton.json, points.json (the keys Appendix A answers), and the frame.md lines
    that list them for the writer."""
    figs = figure_table(case_id, run_id, names, cnames)
    sk = skeleton(case_id, run_id, names)
    pd = S.products_dir(case_id, run_id)
    brief = S.jload(pd / "brief.json")
    keys = _assumed(pd, brief)
    (fd / "figures.json").write_text(json.dumps(figs, ensure_ascii=False, indent=1), encoding="utf-8")
    sk["words"] = plan_budget(len(sk["steps"]))
    (fd / "skeleton.json").write_text(json.dumps(sk, ensure_ascii=False, indent=1), encoding="utf-8")
    (fd / "points.json").write_text(json.dumps([{"key": k, "point": S.point_words(k), "if_denied": "denied.%s" % k if "denied.%s" % k in figs else None}
                                                for k in keys], ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["## Figures", "", "Write every amount in Part 1 as {{fig:<id>}}; the program sets the figure. Ids:", "",
             "| Id | Figure | What it is |", "|---|---|---|"]
    lines += ["| %s | %s | %s |" % (k, v["text"], v["why"]) for k, v in figs.items()]
    lines += ["", "## Skeleton of Part 7", "", "Every step below must be covered by a step of your plan (covers: [id]); keep the order.", ""]
    budget = sk["words"]
    if budget.get("part"):
        lines += ["Budget: Part 7 is at most %d words, about %d for each skeleton step; a step of yours that covers several "
                  "skeleton steps has their shares together. Everything the step prints counts: title, when, who, where, "
                  "documents, how, reason and its source line. Plan each step to its share before you write it; write_block "
                  "returns the count of every step." % (budget["part"], budget["per_step"]), ""]
    for s in sk["steps"]:
        lines.append("- **%s** (%s): %s%s" % (s["id"], s["kind"], s["what"], "; order: %s" % s["order"] if s.get("order") else ""))
    if sk["deadlines"]:
        lines += ["", "Deadlines the law sets:", ""] + ["- %s (%s)" % (d["rule"], d["cite"]) for d in sk["deadlines"]]
    if sk["procedure"]:
        lines += ["", "Official procedure pages:", ""] + ["- %s: %s" % (d["title"], d["url"]) for d in sk["procedure"]]
    lines += ["", "## Points of Appendix A", "", "One card per key:", ""]
    lines += ["- `%s`: %s%s" % (k, S.point_words(k), "; if denied: {{fig:denied.%s}}" % k if "denied.%s" % k in figs else "") for k in keys]
    return lines + [""]


# ------------------------------------------------------------ the program's parts
class Parts:
    """The program's prose, written from the figures table so that each amount it states has its source row."""

    def __init__(self, case_id, run_id):
        self.case_id, self.run_id = case_id, run_id
        self.fd, self.pd = S.frame_dir(case_id, run_id), S.products_dir(case_id, run_id)
        self.figs = S.jload(self.fd / "figures.json")
        self.names = S.jload(self.fd / "names.json")
        self.brief = S.jload(self.pd / "brief.json")
        self.inp = S.jload(self.pd / "input.json") if (self.pd / "input.json").exists() else {}
        self.used = set()

    def f(self, fid):
        x = self.figs.get(fid)
        if not x:
            return None
        self.used.add(fid)
        return x["text"]

    def name(self, cid):
        return (self.names.get(cid) or {}).get("name", "another structure")

    def basis(self, facts):
        import report_form
        keys = _assumed(self.pd, self.brief)
        day = report_form.date_of(facts)
        out = ["This opinion rests on the facts confirmed%s and on %s taken in the group's favour. Appendix A sets out each one: "
               "the provision, what weighs against it, who can confirm it and what its denial would cost." % (
                   " on %s" % day if day else "", "%d points of judgment" % len(keys) if len(keys) != 1 else "one point of judgment")]
        if keys:
            out += [""] + ["- %s (Appendix A item %d)" % (S.point_words(k)[0].upper() + S.point_words(k)[1:], i + 1) for i, k in enumerate(keys)]
        open_choice = [c for c in self.brief.get("conduct") or [] if c.get("stated") is None and c.get("changes_rank")]
        if open_choice:
            out += ["", "One choice of the group's own decides the plan and is set out both ways in Part 1."]
        return "\n".join(out)

    def current(self):
        b = self.brief
        as_is = b["as_is"]
        path = as_is.get("path") or []
        nm = self.name(as_is["cand_id"])
        k = slug(nm)
        payer, payee = (S.node_words(path[0]), S.node_words(path[-1])) if path else ("the payer", "the recipient")
        out = ["As things stand, the %s pays the dividend of %s to the %s%s." % (
            payer, self.f("dividend"), payee, " through %s" % " and ".join(S.node_words(n) for n in path[1:-1]) if len(path) > 2 else "")]
        legs = [self.figs[x] for x in sorted(self.figs) if x.startswith(k + ".leg")]
        tax = self.f(k + ".tax")
        if len(legs) == 1:
            self.f(k + ".leg1")
            out.append("It bears %s on this dividend, all of it on the step %s." % (tax, legs[0].get("step", "")))
        elif legs:
            out.append("It bears %s on this dividend: %s." % (tax, "; ".join("%s on the step %s" % (self.f(x), self.figs[x].get("step", ""))
                                                                        for x in sorted(self.figs) if x.startswith(k + ".leg"))))
        elif tax:
            out.append("It bears %s on this dividend." % tax)
        words = {"as_is_stops_short": "The money stops at the present recipient, short of where it is wanted%s.",
                 "as_is_points_at_stake": "%s of the tax as things stand rests on points of judgment nobody has confirmed.",
                 "conduct_not_stated": "A choice of the group's own decides the plan (Part 1)%s.",
                 "conduct_relied_on": "The recommended figure assumes a step the group must keep; if it is not kept, the tax is %s.",
                 "refund": "Tax overpaid on an earlier dividend can be reclaimed: %s.",
                 "conflict": "The documents and the account given of an earlier dividend differ; Appendix A sets out both readings."}
        items = []
        kept = {x.get("move"): S.move_words(x["move"], *x["hop"]) for x in (b.get("best") or {}).get("if_move_not_kept") or [] if x.get("hop")}
        for d in b.get("diagnosis") or []:
            w = words.get(d["kind"])
            if not w:
                continue
            if d["kind"] == "conduct_relied_on":
                step = next((v for m, v in kept.items() if m and m in (d.get("detail") or "")), None)
                if step:
                    w = "The recommended figure assumes that %s; if not, the tax is %%s." % step
            amt = self.f("current.%s" % d["kind"])
            if "%s" in w:
                if d["kind"] in ("as_is_stops_short", "conduct_not_stated"):
                    w = w % ("" if not amt else "; switching saves %s per payment" % amt if d["kind"] == "conduct_not_stated" else "")
                else:
                    w = w % (amt or "an amount not yet known")
            if d["kind"] == "refund" and d.get("limit"):
                w = w.rstrip(".") + ", claimed by %s." % d["limit"]
            items.append("- " + w)
        if items:
            out += ["", "What is wrong with that position:", ""] + items
        if (b.get("sequence") or {}).get("declared_to_payee"):
            out += ["", "This dividend is already declared to its present recipient, so it follows the present route; the plan applies to later dividends."]
        return "\n".join(out)

    def alternatives(self):
        b = self.brief
        rows = ["| Structure | Route | Restructuring | Tax on this dividend | Saving per payment | One-off cost | Payback |", "|---|---|---|---|---|---|---|"]
        for cid, nm in self.names.items():
            k = slug(nm["name"])
            if not self.figs.get(k + ".tax"):
                continue
            rows.append("| %s | %s | %s | %s | %s | %s | %s |" % (
                nm["name"], nm["label"], ", ".join(nm["restructure"]) or "none", self.f(k + ".tax"), self.f(k + ".saving") or "–",
                self.f(k + ".one_off") or ("none" if not nm["restructure"] else "not yet quantifiable"),
                ("%s payments" % self.f(k + ".payback")) if self.figs.get(k + ".payback") else "–"))
        out = ["The structures compared, each under the same answers in the group's favour:", ""] + rows
        others = b.get("others") or {}
        if others.get("count"):
            out += ["", "%d further route%s %s examined and set aside: each bears more tax on this dividend than the structures above." % (
                others["count"], "s" if others["count"] != 1 else "", "were" if others["count"] != 1 else "was")]
        return "\n".join(out)

    def optimal(self):
        b = self.brief
        best = b["best"]["cand_id"]
        nm = self.names.get(best) or {}
        k = slug(nm.get("name", ""))
        tax = self.f(k + ".tax")
        level = [n["name"] for c, n in self.names.items() if c != best and self.figs.get(slug(n["name"]) + ".tax", {}).get("value") == self.figs.get(k + ".tax", {}).get("value")]
        out = ["The plan is built on %s (%s). It bears the least tax on this dividend of the structures compared, %s%s." % (
            nm.get("name"), nm.get("label"), tax, "; %s bear%s the same, and among equal taxes the structure that repays its cost soonest, "
            "and then the one that asks the least of the group, comes first" % (" and ".join(level), "s" if len(level) == 1 else "") if level else "")]
        keys = _assumed(self.pd, b)
        if keys:
            out.append("It rests on Appendix A items %s." % (", ".join(str(i + 1) for i in range(len(keys)))))
        asks = [w for w in nm.get("move_words") or [] if " is received in " not in w]
        if asks:
            out.append("It also asks that %s." % "; that ".join(asks))
        return " ".join(out)

    def comparison(self):
        return ("The table gives, for each structure, the tax at each step and on this dividend under the answers in the group's favour, "
                "the saving per payment against the route the money takes today, the one-off cost of any restructuring and the payments "
                "that repay it. The second table shows what each figure rests on.")

    def requirements(self, labels):
        """Part 6 from the rules the recommended structure's favourable branch applies: what each needs, and whether the facts
        on file meet it or Appendix A takes it as an assumption."""
        b = self.brief
        best = b["best"]["cand_id"]
        fb = ((b.get("best") or {}).get("all_favourable") or {}).get("branch_id")
        rq = self.pd / "requirements" / ("%s.json" % best)
        hp = self.pd / "hops" / ("%s.json" % fb)
        if not rq.exists():
            return "The requirements of the recommended structure are set out in Appendix A."
        applied = set()
        if hp.exists():
            for hop in S.jload(hp).get("items") or []:
                for it in hop:
                    applied.update((it.get("rules_applied") or {}).get("floor") or [])
        keys = _assumed(self.pd, b)
        item_of = {k.split("@")[0]: i + 1 for i, k in enumerate(keys)}
        out, seen, slots = [], set(), {}
        reqs = S.jload(rq).get("requirements") or []
        for q in reqs:              # one rule per relief: the one with the most conditions
            for fr in q.get("favourable_rules") or []:
                for ru in fr.get("rules") or []:
                    if (applied and ru["rule_id"] not in applied) or ru.get("requires", {}).get("kind") == "always":
                        continue
                    key = (q.get("slot_key"), ru.get("effect", "").split(":")[0])
                    if key not in slots or len(list(_parts(ru.get("requires") or {}))) > len(list(_parts(slots[key].get("requires") or {}))):
                        slots[key] = ru
        for q in reqs:
            sk = q.get("slot_key", "").split("|")
            jur = S.JUR.get(sk[0], "")
            other = S.JUR.get(sk[3], "") if len(sk) > 3 and sk[3] != "*" else ""
            for fr in q.get("favourable_rules") or []:
                for ru in fr.get("rules") or []:
                    if ru["rule_id"] in seen or slots.get((q.get("slot_key"), ru.get("effect", "").split(":")[0])) is not ru:
                        continue
                    seen.add(ru["rule_id"])
                    cites = ", ".join("{{cite:%s|%s}}" % (c, labels.get(c, c.split("#")[-1])) for c in ru.get("cite_ids") or [])
                    what = relief_words(sk, ru.get("effect", ""))
                    conds = []
                    for part in _parts(ru.get("requires") or {}):
                        if part.get("kind") == "predicate":
                            n = item_of.get(part.get("key"))
                            conds.append("%s: see Appendix A item %s" % (S.POINT.get(part.get("key"), part.get("key", "")).capitalize(), n) if n else
                                         S.POINT.get(part.get("key"), part.get("key", "")).capitalize())
                        elif part.get("kind") == "compare":
                            left = part.get("left") or {}
                            question = left.get("question")
                            if not question:
                                continue
                            right = part.get("right") or {}
                            treaty = bool(re.match(r"^[a-z]{2}-[a-z]{2}\.", ru["rule_id"]))
                            said = condition_words(left.get("variable"), part.get("op"), right, jur, other if treaty else jur)
                            if said:
                                conds.append(said)
                                continue
                            want = ("yes" if right.get("constant") is True else "no" if right.get("constant") is False else
                                    ("%s %s" % ({">=": "at least", ">": "more than", "<=": "at most", "<": "less than", "=": ""}.get(part.get("op"), part.get("op")),
                                                right.get("value", right.get("constant", "")))).strip())
                            conds.append("%s Required: %s." % (question.rstrip(), want))
                    out.append("%d. %s%s: %s (%s)." % (len(out) + 1, jur + ", " if jur else "", what, cites or "the provision applied", "met on the facts confirmed" if not conds else "it requires the following"))
                    out += ["   - %s" % c for c in conds]
            for p in q.get("reference_params") or []:
                note = p.get("note")
                if note and re.search(r"deadline|by the|within|days?|month", note, re.I) and p.get("cite_id"):
                    line = "%d. Deadline: %s ({{cite:%s|%s}})." % (len(out) + 1, note.rstrip("."), p["cite_id"], labels.get(p["cite_id"], p["cite_id"].split("#")[-1]))
                    if not any(line.split(" ", 1)[1] == o.split(" ", 1)[1] for o in out if o[:1].isdigit()):
                        out.append(line)
        n = 0
        renum = []
        for line in out:                                   # numbers again after the duplicates were left out
            if re.match(r"^\d+\. ", line):
                n += 1
                line = "%d. %s" % (n, line.split(" ", 1)[1])
            renum.append(line)
        return "\n".join(renum) or "Nothing beyond the points of Appendix A."


def relief_words(sk, effect):
    """What a favourable rule does, by the role of its slot: withholding at source, the dividend received, the final holder."""
    kind, subject = (sk[2] if len(sk) > 2 else ""), (sk[1] if len(sk) > 1 else "")
    who = S.SUBJ.get(subject, "recipient") if subject not in ("", "all", "*") else "recipient"
    e = effect.split(":")[0]
    if kind == "outbound_wht":
        return {"cap": "the tax withheld on the dividend is limited by treaty", "exempt": "no tax is withheld on the dividend paid"}.get(e, "the withholding is reduced")
    if kind == "inbound":
        return {"exempt": "the dividend the %s receives is exempt" % who, "credit": "the %s is credited with the tax paid abroad" % who}.get(e, "the dividend received is relieved")
    if kind == "final":
        return {"exempt": "the dividend is exempt in the hands of the %s" % who}.get(e, "the final holder's tax is relieved")
    return EFFECT.get(e, "the relief applies")


def doc_list(value):
    """A step's documents as a list: the block asks for a list, a single string is read as items separated by ';'."""
    if isinstance(value, str):
        return [d.strip() for d in value.split(";") if d.strip()]
    return list(value or [])


def condition_words(variable, op, right, jur, payee_jur):
    """A condition of the rule layer in an adviser's words, for the variables Part 6 meets most; None for the others. The payee's
    residence is asked in the jurisdiction whose rule it is, or for a treaty rule in the treaty partner (payee_jur)."""
    value = right.get("value", right.get("constant"))
    least = {">=": "at least", ">": "more than"}.get(op)
    words = {
        "payee_resident": "The recipient is resident in %s." % (payee_jur or "the treaty partner"),
        "payer_resident": "The payer is resident in %s." % (jur or "its jurisdiction"),
        # the provision decides what is counted (capital or votes) and when; the sentence leaves that to the quoted provision
        "holding_pct": "The recipient holds %s %s per cent of the payer, measured as the provision states." % (least, value) if least else None,
        "holding_months": "The recipient's holding has lasted %s %s months, over the period the provision states." % (least, value) if least else None,
        "payer_income_taxed": "The profits behind the dividend were subject to income tax in the payer's jurisdiction.",
        "payer_tax_rate": "The headline rate of company income tax in the payer's jurisdiction is %s %s per cent." % (least, value) if least else None,
    }
    return words.get(variable) if right.get("constant") is not False else None


def _parts(node):
    if node.get("kind") in ("and", "or"):
        for p in node.get("parts") or []:
            yield from _parts(p)
    elif node.get("kind") != "not":
        yield node


# ------------------------------------------------------------ the agent's blocks
def read_block(case_id, run_id, block):
    p = blocks_dir(case_id, run_id) / FILE[block]
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8")
    return text if block == "strategy" else json.loads(text)


def parse_block(block, content):
    """(value, error) of a block as the agent gives it: strategy as text, plan and points as JSON."""
    if block not in AI:
        return None, "block must be one of %s" % ", ".join(AI)
    if block == "strategy":
        text = str(content or "").strip()
        if re.search(r"(?m)^#{1,3}\s", text):
            return None, "write Part 1 without headings: the program sets the heading"
        return (text, None) if text else (None, "the strategy text is empty")
    try:
        data = json.loads(content) if isinstance(content, str) else content
    except ValueError as e:
        return None, "not valid JSON: %s" % e
    if block == "plan":
        steps = data.get("steps") if isinstance(data, dict) else None
        if not isinstance(steps, list) or not steps:
            return None, "plan must be {\"steps\": [...]} with at least one step"
        for i, s in enumerate(steps):
            if not isinstance(s, dict) or not s.get("title"):
                return None, "steps[%d] needs a title" % i
            if s.get("deadline", "none") not in DEADLINES:
                return None, "steps[%d].deadline must be legal, estimate or none" % i
            unknown = sorted(set(s) - set(STEP_FIELDS) - {"date"})
            if unknown:
                return None, "steps[%d]: unknown fields %s; the fields are %s" % (i, ", ".join(unknown), ", ".join(STEP_FIELDS + ("date",)))
        return data, None
    cards = data.get("cards") if isinstance(data, dict) else None
    if not isinstance(cards, list):
        return None, "points must be {\"cards\": [...], \"notes\": [...]}"
    for i, c in enumerate(cards):
        if not isinstance(c, dict) or not c.get("key"):
            return None, "cards[%d] needs the key of its point (as in the frame's list)" % i
        unknown = sorted(set(c) - set(CARD_FIELDS) - {"title", "routes"})
        if unknown:
            return None, "cards[%d]: unknown fields %s" % (i, ", ".join(unknown))
    for i, n in enumerate(data.get("notes") or []):
        if not isinstance(n, dict) or not n.get("title") or not n.get("text"):
            return None, "notes[%d] needs a title and a text" % i
    return data, None


def strings(value):
    """Every string inside a block value, for the figure and citation checks."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


def check_block(case_id, run_id, block, value, known_cites=None):
    """Content problems of one block: the agent fixes them; the block is saved either way."""
    fd = S.frame_dir(case_id, run_id)
    figs = S.jload(fd / "figures.json") if (fd / "figures.json").exists() else {}
    problems = []
    for text in strings(value):
        for fid in FIG.findall(text):
            if fid not in figs:
                problems.append("{{fig:%s}} is not in the figures table" % fid)
        bare = [m.group(0) for m in AMOUNT.finditer(CITE.sub(" ", FIG.sub(" ", text))) if not YEAR.match(m.group(1))]
        if bare and block == "strategy":
            problems.append("amounts written as numbers (%s): write each as {{fig:<id>}} from the figures table" % ", ".join(sorted(set(bare))[:6]))
        if known_cites is not None:
            for cid, _ in CITE.findall(text):
                if cid.strip() not in known_cites:
                    problems.append("citation %s is not a provision of the library" % cid.strip())
    if block == "plan":
        sk = S.jload(fd / "skeleton.json") if (fd / "skeleton.json").exists() else {"steps": []}
        covered = {c for s in value["steps"] for c in (s.get("covers") or [])}
        missing = [s["id"] for s in sk["steps"] if s["id"] not in covered]
        if missing:
            problems.append("skeleton steps no step covers: %s" % ", ".join(missing))
        for i, s in enumerate(value["steps"]):
            if not s.get("when"):
                problems.append("step %d (%s): give its date or window in when" % (i + 1, s["title"][:40]))
            if s.get("deadline") == "legal" and not any("cite" in x for x in s.get("sources") or []) and not CITE.search(json.dumps(s, ensure_ascii=False)):
                problems.append("step %d: a legal deadline names its provision (a {{cite:...}} in the step or a cite in its sources)" % (i + 1))
            for x in s.get("sources") or []:
                if "url" in x and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(x.get("accessed", ""))):
                    problems.append("step %d: the web source %s needs accessed as YYYY-MM-DD" % (i + 1, str(x.get("url"))[:60]))
    if block == "points":
        want = [p["key"] for p in (S.jload(fd / "points.json") if (fd / "points.json").exists() else [])]
        have = [c["key"] for c in value["cards"]]
        miss = [k for k in want if k not in have]
        if miss:
            problems.append("points without a card: %s" % ", ".join(miss))
        for c in value["cards"]:
            for f in ("answer", "provision", "confirm_by"):
                if not c.get(f):
                    problems.append("card %s: %s is empty" % (c["key"], f))
            if not c.get("against"):
                problems.append("card %s: state what weighs against it (or one entry saying nothing on file does)" % c["key"])
    return problems


def write_block(case_id, run_id, block, content):
    """Saves an agent block and renders the report again. Returns {written, problems} or {error}."""
    value, error = parse_block(block, content)
    if error:
        return {"error": "invalid", "detail": error}
    bd = blocks_dir(case_id, run_id)
    bd.mkdir(parents=True, exist_ok=True)
    p = bd / FILE[block]
    text = value if block == "strategy" else json.dumps(value, ensure_ascii=False, indent=1)
    if p.exists():
        p.with_name(p.name + ".prev").write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
    p.write_text(text + ("\n" if block == "strategy" else ""), encoding="utf-8")
    return {"written": str(p)}


def edit_block(case_id, run_id, block, edits):
    """Replace exact passages in one block: each old text must occur once in it; all or none."""
    if block not in AI:
        return {"error": "invalid", "detail": "block must be one of %s" % ", ".join(AI)}
    p = blocks_dir(case_id, run_id) / FILE[block]
    if not p.exists():
        return {"error": "not_found", "detail": "write the %s block first" % block}
    raw = p.read_text(encoding="utf-8")
    text = raw if block == "strategy" else json.dumps(json.loads(raw), ensure_ascii=False)
    for i, e in enumerate(edits or []):
        old = e.get("old") if isinstance(e, dict) else None
        if block != "strategy" and old:
            old_j, new_j = json.dumps(old, ensure_ascii=False)[1:-1], json.dumps(str(e.get("new", "")), ensure_ascii=False)[1:-1]
        else:
            old_j, new_j = old, str(e.get("new", "")) if isinstance(e, dict) else ""
        n = text.count(old_j) if old_j else 0
        if n != 1:
            return {"error": "invalid", "detail": "edits[%d]: the old text occurs %d times in the %s block, it must occur once; nothing was changed" % (i, n, block)}
        text = text.replace(old_j, new_j)
    if not edits:
        return {"error": "invalid", "detail": "give a list of {old, new}"}
    return write_block(case_id, run_id, block, text if block == "strategy" else json.loads(text))


# ------------------------------------------------------------ rendering
class Render:
    def __init__(self, figs, used):
        self.figs, self.used = figs, used

    def __call__(self, text):
        def put(m):
            x = self.figs.get(m.group(1))
            if not x:
                return m.group(0)
            self.used.add(m.group(1))
            return x["text"]
        return FIG.sub(put, str(text or ""))


def render_plan(plan, r):
    out = []
    for i, s in enumerate(plan.get("steps") or []):
        when = r(s.get("when", ""))
        tag = {"legal": "deadline set by law", "estimate": "planning estimate"}.get(s.get("deadline"), "")
        out.append("%d. **%s**%s" % (i + 1, r(s["title"]).rstrip("."), " — %s%s" % (when, " (%s)" % tag if tag else "") if when else ""))
        for label, key in (("Who", "who"), ("Where", "where"), ("How", "how")):
            if s.get(key):
                out.append("   %s: %s" % (label, r(s[key])))
        if s.get("documents"):
            out.append("   Documents: %s." % "; ".join(r(d).rstrip(".") for d in doc_list(s["documents"])))
        if s.get("reason"):
            out.append("   %s" % r(s["reason"]))
        web = [x for x in s.get("sources") or [] if x.get("url")]
        if web:
            out.append("   Source: %s." % "; ".join("%s (%s, accessed %s)" % (x.get("title") or x["url"], x["url"], x.get("accessed", "")) for x in web))
    return "\n".join(out)


def ordered_cards(points, keys):
    """The cards in the order of the frame's points, so that "Appendix A item n" means the same in every part."""
    rank = {k: i for i, k in enumerate(keys)}
    return sorted(points.get("cards") or [], key=lambda c: (rank.get(c.get("key"), len(rank)), (points.get("cards") or []).index(c)))


def render_points(points, r, figs, keys=()):
    out = []
    for i, c in enumerate(ordered_cards(points, keys)):
        title = c.get("title") or (S.point_words(c["key"])[0].upper() + S.point_words(c["key"])[1:])
        out.append("%d. **%s** — %s. %s" % (i + 1, r(title), r(c.get("answer", "")).rstrip("."), r(c.get("provision", ""))))
        for label, key in (("For", "for"), ("Against", "against")):
            items = [r(x.get("fact") if isinstance(x, dict) else x).rstrip(".") for x in c.get(key) or []]
            if items:
                out.append("   %s: %s." % (label, "; ".join(items)))
        for x in c.get("routes") or []:
            out.append("   Route: %s%s." % (r(x.get("route") if isinstance(x, dict) else x).rstrip("."), " (%s)" % x["strength"] if isinstance(x, dict) and x.get("strength") else ""))
        if c.get("reason"):
            out.append("   %s" % r(c["reason"]))
        who = r(c.get("confirm_by", "")).rstrip(".")
        if who:
            out.append("   Confirmed by: %s%s." % (who, "; %s" % r(c["how"]).rstrip(".") if c.get("how") else ""))
        fid = "denied.%s" % c["key"]
        if fid in figs:
            out.append("   If denied: %s more on this dividend." % r("{{fig:%s}}" % fid))
    for j, n in enumerate(points.get("notes") or []):
        out.append("%d. **%s** — %s" % (len(points.get("cards") or []) + j + 1, r(n["title"]).rstrip("."), r(n["text"])))
    return "\n".join(out)


def clause_labels():
    import csv
    p = S.DB / "clause.csv"
    if not p.exists():
        return {}
    with p.open(encoding="utf-8-sig") as f:
        return {r["cite_id"]: r.get("label") or r["cite_id"] for r in csv.DictReader(f)}


def build(case_id, run_id, facts=None):
    """Render the report of a panel run: panel.json always; briefing.md and briefing.sources.json once the three agent blocks
    exist (before that the case has no draft). Returns {draft, panel, missing}."""
    if not is_panel_run(case_id, run_id):
        return {"error": "not_found", "detail": "run %s has no frame with a figures table" % run_id}
    rd, fd = rd_of(case_id, run_id), S.frame_dir(case_id, run_id)
    facts = facts if facts is not None else (S.jload(S.CASES / case_id / "intake" / "facts.json") if (S.CASES / case_id / "intake" / "facts.json").exists() else {})
    parts = Parts(case_id, run_id)
    labels = clause_labels()
    r = Render(parts.figs, parts.used)
    blocks = {b: read_block(case_id, run_id, b) for b in AI}
    program = {"basis": parts.basis(facts), "2": parts.current(), "3": parts.alternatives(), "4": parts.optimal(),
               "5": parts.comparison(), "6": parts.requirements(labels)}
    agent = {"1": r(blocks["strategy"]) if blocks["strategy"] else None,
             "7": render_plan(blocks["plan"], r) if blocks["plan"] else None,
             "A": render_points(blocks["points"], r, parts.figs, _assumed(parts.pd, parts.brief)) if blocks["points"] else None}
    missing = [b for b in AI if blocks[b] is None]
    order = [("basis", "## %s" % TITLES["basis"]), ("1", "## " + TITLES["1"]), ("2", "## " + TITLES["2"]), ("3", "## " + TITLES["3"]),
             ("4", "## " + TITLES["4"]), ("5", "## " + TITLES["5"]), ("6", "## " + TITLES["6"]), ("7", "## " + TITLES["7"]), ("A", "## " + TITLES["A"])]
    rows = sources(case_id, run_id, parts, blocks)
    draft = None
    if not missing:
        text = "\n\n".join("%s\n\n%s" % (head, (program.get(k) if k in program else agent.get(k)) or "") for k, head in order).strip() + "\n"
        write_if_changed(rd / "briefing.md", text)
        write_if_changed(rd / "briefing.sources.json", json.dumps(rows, ensure_ascii=False, indent=1))
        draft = str(rd / "briefing.md")
    view = panel_doc(case_id, run_id, facts, program, agent, blocks, rows, parts)
    write_if_changed(rd / "panel.json", json.dumps(view, ensure_ascii=False, indent=1))
    return {"draft": draft, "panel": str(rd / "panel.json"), "missing": missing}


def sources(case_id, run_id, parts, blocks):
    """briefing.sources.json from the figures the report states, the names it uses, the frame's tables and the sources the agent
    gave in its blocks (web pages of Part 7, documents of Appendix A). Citation markers need no row (the program adds one per marker)."""
    rows = []
    for fid in sorted(parts.used):
        x = parts.figs[fid]
        rows.append({"id": "fig-%s" % fid, "where": "figure %s" % x["text"], "claim": "%s: %s" % (x["text"], x["why"]), "kind": "product", "ref": x["ref"]})
    for nm in parts.names.values():
        rows.append({"id": "name-%s" % slug(nm["name"]), "where": "Name: '%s'" % nm["name"], "claim": nm["label"], "kind": "name", "ref": nm["signature"]})
    fd = S.frame_dir(case_id, run_id)
    if (fd / "blocks.sources.json").exists():
        rows += S.rows_of(S.jload(fd / "blocks.sources.json"))
    for i, s in enumerate((blocks.get("plan") or {}).get("steps") or []):
        for j, x in enumerate(s.get("sources") or []):
            if x.get("url"):
                rows.append({"id": "p7-%d-%d" % (i + 1, j + 1), "where": "Part 7 step %d" % (i + 1), "claim": x.get("title") or s["title"],
                             "kind": "url", "ref": "%s (accessed %s)" % (x["url"], x.get("accessed", ""))})
    for i, c in enumerate((blocks.get("points") or {}).get("cards") or []):
        for side in ("for", "against"):
            for j, x in enumerate(c.get(side) or []):
                if isinstance(x, dict) and x.get("source"):
                    rows.append({"id": "a%d-%s-%d" % (i + 1, side, j + 1), "where": "Appendix A item %d" % (i + 1), "claim": x.get("fact", ""),
                                 "kind": "document", "ref": str(x["source"])})
    return rows


# ------------------------------------------------------------ the panel
def plain(text):
    return CITE.sub(lambda m: m.group(2).strip(), text or "")


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12] if value is not None else None


def panel_doc(case_id, run_id, facts, program, agent, blocks, rows, parts):
    """panel.json: the blocks in report order, each with its client text; the state of each is set when the host serves it."""
    import report_form
    fb = S.frame_dir(case_id, run_id) / "blocks"
    tables = {p.stem: p.read_text(encoding="utf-8").strip() for p in fb.glob("*.md")} if fb.exists() else {}
    flow = S.jload(fb / "flow.json") if (fb / "flow.json").exists() else None
    cites = [{"kind": "cite", "ref": cid} for b in AI for t in strings(blocks.get(b)) for cid, _ in CITE.findall(t)]
    cites += [{"kind": "cite", "ref": cid} for t in program.values() for cid, _ in CITE.findall(t)]
    appendix_b = S.appendix_b(list(rows) + cites)
    r = Render(parts.figs, set())

    def p(text):
        return plain(text) if text else None
    plan = blocks.get("plan")
    points = blocks.get("points")
    out = [
        {"id": "summary", "kind": "program", "figures": summary(parts)},
        {"id": "basis", "kind": "program", "title": TITLES["basis"], "md": p(program["basis"])},
        {"id": "1", "kind": "agent", "block": "strategy", "title": TITLES["1"], "md": p(agent["1"]), "flow": flow,
         "tables": [plain(tables["choices_table"])] if "choices_table" in tables else []},
        {"id": "2", "kind": "program", "title": TITLES["2"], "md": p(program["2"])},
        {"id": "3", "kind": "program", "title": TITLES["3"], "md": p(program["3"])},
        {"id": "4", "kind": "program", "title": TITLES["4"], "md": p(program["4"])},
        {"id": "5", "kind": "program", "title": TITLES["5"], "md": p(program["5"]),
         "tables": [plain(tables[k]) for k in ("tax_table", "robustness_table") if k in tables]},
        {"id": "6", "kind": "program", "title": TITLES["6"], "md": p(program["6"])},
        {"id": "7", "kind": "agent", "block": "plan", "title": TITLES["7"], "md": p(agent["7"]),
         "steps": [{**{k: ([plain(r(x)) for x in doc_list(v)] if k == "documents" else plain(r(v)) if isinstance(v, str) else v)
                       for k, v in s.items() if k not in ("covers", "sources")},
                    "sources": [x for x in s.get("sources") or [] if x.get("url")]}      # a provision is named in the step's text already
                   for s in (plan or {}).get("steps") or []] if plan else None},
        {"id": "A", "kind": "agent", "block": "points", "title": TITLES["A"], "md": p(agent["A"]),
         "tables": [plain(tables["assumptions_table"])] if "assumptions_table" in tables else [],
         "cards": [card_view(c, r, parts.figs) for c in ordered_cards(points, _assumed(parts.pd, parts.brief))] if points else None,
         "notes": [{"title": plain(r(n["title"])), "text": plain(r(n["text"]))} for n in (points or {}).get("notes") or []] if points else None,
         "gaps": plain(tables["gaps_list"]) if "gaps_list" in tables else None},
        {"id": "B", "kind": "program", "title": TITLES["B"], "md": plain(re.sub(r"^## .*\n+", "", appendix_b))},
    ]
    return {"case_id": case_id, "run_id": run_id, "title": report_form.title_of(facts), "date": report_form.date_of(facts),
            "built": now(), "digests": {b: digest(blocks.get(b)) for b in AI}, "blocks": out}


def card_view(c, r, figs):
    title = c.get("title") or (S.point_words(c["key"])[0].upper() + S.point_words(c["key"])[1:])
    side = lambda key: [plain(r(x.get("fact") if isinstance(x, dict) else x)) for x in c.get(key) or []]
    fid = "denied.%s" % c["key"]
    return {"key": c["key"], "title": plain(r(title)), "answer": plain(r(c.get("answer", ""))), "provision": plain(r(c.get("provision", ""))),
            "for": side("for"), "against": side("against"),
            "routes": [plain(r(x.get("route") if isinstance(x, dict) else x)) for x in c.get("routes") or []],
            "reason": plain(r(c.get("reason", ""))), "confirm_by": plain(r(c.get("confirm_by", ""))), "how": plain(r(c.get("how", ""))),
            "if_denied": figs[fid]["text"] if fid in figs else None}


def summary(parts):
    b = parts.brief
    best = b["best"]["cand_id"]
    nm = parts.names.get(best) or {}
    k = slug(nm.get("name", ""))
    g = lambda fid: (parts.figs.get(fid) or {}).get("text")
    return {"plan": nm.get("name"), "route": nm.get("label"), "saving": g(k + ".saving"), "one_off": g(k + ".one_off"),
            "payback": g(k + ".payback"), "this_tax": g("this.tax") or g(k + ".tax")}


def view(case_id, run_id, status, running=None):
    """panel.json with the state of each block for the web panel: final, writing, review or updating. status is the case
    status (case_server.status); running the node now running, if any."""
    p = rd_of(case_id, run_id) / "panel.json"
    if not p.exists():
        return None
    doc = json.loads(p.read_text(encoding="utf-8"))
    times = {b: (blocks_dir(case_id, run_id) / FILE[b]).stat().st_mtime if (blocks_dir(case_id, run_id) / FILE[b]).exists() else None for b in AI}
    reviewed = (rd_of(case_id, run_id) / "review.md").exists()
    delivered = status == "delivered"
    passed = status in ("delivered", "reviewed")          # reviewed: both checklists passed, the render step still to run
    for blk in doc["blocks"]:
        if blk["kind"] == "program":
            blk["state"] = "final"
            continue
        b = blk["block"]
        if passed:
            state = "final"
        elif times[b] is None:
            state = "writing"
        elif running == "analysis":
            state = "updating" if reviewed else "writing"
        elif any(times.get(d) and times[d] > times[b] for d in DEPENDS[b]) and reviewed:
            state = "updating"
        else:
            state = "review"
        blk["state"] = state
        if state in ("writing", "updating") and not delivered:
            blk.pop("md", None)                              # what is being rewritten is not shown half-done
            blk.pop("steps", None)
            blk.pop("cards", None)
            blk.pop("notes", None)
    doc["status"] = status
    doc["export_ready"] = delivered and (rd_of(case_id, run_id) / "briefing.pdf").exists()
    agents = [b for b in doc["blocks"] if b["kind"] == "agent"]
    doc["progress"] = {"final": sum(1 for b in agents if b["state"] == "final"), "total": len(agents)}
    return doc


# ------------------------------------------------------------ reviewers' replacements
# what render_plan and render_points put around a field: a numbered title line, a line label, a deadline tag
FRAME_HEAD = re.compile(r"^\s*(?:\d+\.\s+)?(?:\*\*[^*\n]+\*\*\s+—\s+|(?:Who|Where|How|Documents|For|Against|Route|Confirmed by|Source):\s+)")
FRAME_TAIL = re.compile(r"\s+\((?:planning estimate|deadline set by law)\)\.?$")


def unframe(old, new):
    """A reviewer quotes a rendered line of Part 7 or Appendix A, label and all, while the block holds the field alone. Strips
    the frame both texts share (a frame that differs is a change of another field, which stays unapplied)."""
    for rx in (FRAME_HEAD, FRAME_TAIL):
        a, b = rx.search(old), rx.search(new)
        if a and b and a.group(0) == b.group(0):
            old, new = (old[a.end():], new[b.end():]) if rx is FRAME_HEAD else (old[:a.start()], new[:b.start()])
    return old, new


def apply_replacement(case_id, run_id, old, new):
    """A reviewer's {old, new} applied to the agent block whose rendered text holds old once. Returns the block changed, or None
    (the sentence is the program's, or not found). Figures stay placeholders: a figure the new text repeats is set back."""
    hit = replace_in_blocks(case_id, run_id, old, new)
    bare = unframe(old, new)
    return hit or (replace_in_blocks(case_id, run_id, *bare) if bare != (old, new) and bare[0] else None)


def replace_in_blocks(case_id, run_id, old, new):
    import report_form
    fd = S.frame_dir(case_id, run_id)
    figs = S.jload(fd / "figures.json")
    back = sorted(((x["text"], "{{fig:%s}}" % k) for k, x in figs.items()), key=lambda t: -len(t[0]))
    r = Render(figs, set())
    for b in AI:
        value = read_block(case_id, run_id, b)
        if value is None:
            continue
        hit = [0]

        def fix(s):
            if hit[0]:
                return s
            if s.count(old) == 1:
                hit[0] = 1
                return s.replace(old, new)
            rs = r(s)
            span = report_form.locate(rs, old)              # quoted with figures set, with or without its citation markers
            if not span:
                return s
            hit[0] = 1
            out = rs[:span[0]] + new + rs[span[1]:]
            for text, mark in back:
                if mark in s:
                    out = out.replace(text, mark)
            return out

        def walk(v):
            if isinstance(v, str):
                return fix(v)
            if isinstance(v, list):
                return [walk(x) for x in v]
            if isinstance(v, dict):
                return {k: walk(x) for k, x in v.items()}
            return v
        changed = walk(value)
        if hit[0]:
            write_block(case_id, run_id, b, changed)
            return b
    return None


def ai_lines(text):
    """Line numbers (1-based) of briefing.md that belong to the agent's parts (1, 7, A): the legal lane checks these only."""
    out, cur = set(), None
    for i, line in enumerate(text.splitlines(), 1):
        m = re.match(r"^##\s+(?:(\d)\.|Appendix\s+([AB])\b|(.+))", line)
        if m:
            cur = m.group(1) or m.group(2) or "other"
        if cur in ("1", "7", "A"):
            out.add(i)
    return out


def copy_baseline(case_id, run_id, base_run):
    """A revised edition starts from the last edition's agent blocks; the program's parts are rendered anew from this run."""
    src, dst = blocks_dir(case_id, base_run), blocks_dir(case_id, run_id)
    if not src.exists() or dst.exists():
        return []
    dst.mkdir(parents=True)
    done = []
    for b in AI:
        p = src / FILE[b]
        if p.exists():
            (dst / FILE[b]).write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
            done.append(b)
    return done
