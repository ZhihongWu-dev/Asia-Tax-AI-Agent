"""Sectioned drafting (agent/orchestration_cli_spec.en.md §10): the program frame (structure names, tables and their sources),
one file per part of the briefing, assembly of the draft, Appendix B from the cited sources, and parts carried from the last edition.
Program only: it reads products, the library and the baseline draft; the prose is written by the analysis agent."""
import csv
import json
import re
import shutil
from pathlib import Path

csv.field_size_limit(2 ** 31 - 1)                     # clause texts are long

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
CASES = PROJECT / "cases"
DB = PROJECT / "database"

ORDER = ["head", "1", "2", "3", "4", "5", "6", "7", "A", "B", "end"]
TITLES = {"1": "1. Strategy", "2": "2. Current State", "3": "3. Alternatives", "4": "4. Optimal Plan", "5": "5. Tax Comparison",
          "6": "6. Requirements", "7": "7. Implementation", "A": "Appendix A — Points to Confirm and Assumptions",
          "B": "Appendix B — Legal Basis and Sources"}
GROUPS = {"current": ["2"], "alternatives": ["3", "5"], "plan": ["4", "6"], "implementation": ["7", "A"]}
INTEGRATOR = ["head", "1"]
PROGRAM = ["B", "end"]
JUR = {"cn": "Mainland China", "hk": "Hong Kong", "sg": "Singapore", "jp": "Japan", "th": "Thailand", "kr": "Korea",
       "id": "Indonesia", "in": "India", "my": "Malaysia", "vn": "Vietnam", "ae": "United Arab Emirates"}
SUBJ = {"company": "company", "individual": "individual"}
POINT = {"bo": "beneficial ownership", "parent_bo": "beneficial ownership of the parent", "ppt": "the treaty's principal purpose test",
         "gaar": "the general anti-avoidance rule", "fsie_mpr": "the Hong Kong main purpose rule for foreign-sourced dividends",
         "substance": "economic substance", "lob": "limitation on benefits"}
FLAG = {"valuation_missing": "no valuation of the company transferred", "fx_missing": "no exchange rate on file",
        "cost_missing": "no cost of the shares transferred"}
MARK = re.compile(r"\{\{block:([a-z_]+)\}\}")
ONE_OFF_POINT = {"indirect_transfer_purpose": "reasonable commercial purpose of the indirect transfer (Mainland China)"}
NAME = re.compile(r"\bPlan [A-Z]\b|\bCurrent structure\b")
FACT_WORDS = {"passes_on_within_12m": ("passes the dividend on within 12 months", "does not pass the dividend on within 12 months"),
              "substantive_business": ("carries on substantive business", "carries on no substantive business"),
              "premises_in_jurisdiction": ("has premises of its own there", "has no premises of its own there"),
              "parent_holding_pct": None, "parent_jur": None, "employees_in_jurisdiction": None}


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def rows_of(data):
    return data if isinstance(data, list) else (data or {}).get("sources", [])


def money(x):
    return "{:,.0f}".format(float(x))


def span(a, b):
    """'700,000' or '700,000 – 1,400,000'; None when either side is unknown."""
    if a is None or b is None:
        return None
    a, b = float(a), float(b)
    return money(a) if abs(a - b) < 0.5 else "%s – %s" % (money(min(a, b)), money(max(a, b)))


def node_words(node):
    jur, _, subject = str(node).partition(":")
    return "%s %s" % (JUR.get(jur, jur.upper()), SUBJ.get(subject, subject))


def point_words(key):
    """bo@cn -> 'beneficial ownership (Mainland China)'."""
    pred, _, jur = key.partition("@")
    return "%s (%s)" % (POINT.get(pred, pred.replace("_", " ")), JUR.get(jur, jur.upper()))


def scenario_words(sid):
    if sid == "all_favourable":
        return "every point favourable"
    if sid == "all_unfavourable":
        return "every point against the group"
    m = re.match(r"against:([^:]+):(.+)$", sid)
    if m:
        return "%s answered against the group, for the %s" % (point_words(m.group(1)), node_words(m.group(2)))
    return sid


# ------------------------------------------------------------ paths
def report_dir(case_id, run_id):
    return CASES / case_id / "report" / run_id


def products_dir(case_id, run_id):
    return CASES / case_id / "intake" / "products" / run_id


def sec_dir(case_id, run_id):
    return report_dir(case_id, run_id) / "sections"


def frame_dir(case_id, run_id):
    return report_dir(case_id, run_id) / "frame"


# ------------------------------------------------------------ the frame
def signature(c):
    return "%s | %s | %s" % (">".join(c["path"]), ",".join(sorted(c.get("moves") or [])) or "-", ",".join(sorted(c.get("restructure") or [])) or "-")


def baseline_names(case_id, base_run):
    """signature -> name from the kind-name sources of the last edition."""
    if not base_run:
        return {}
    p = report_dir(case_id, base_run) / "briefing.sources.json"
    if not p.exists():
        return {}
    out = {}
    for r in rows_of(jload(p)):
        if isinstance(r, dict) and r.get("kind") == "name":
            m = NAME.search(" ".join(str(r.get(k, "")) for k in ("where", "claim")))
            if m:                                          # only a real name ("Plan B", "Current structure"), never the label of a passage
                out[str(r.get("ref", "")).split(" (")[0].strip()] = m.group(0)
    return out


def name_structures(products, base_names):
    """cand_id -> {name, signature, label}: the as-is structure, every structure of the brief and every structure a judgment point
    puts first; the last edition's names are kept, a structure new to the report takes the next free letter."""
    brief = jload(products / "brief.json")
    paths = {c["cand_id"]: c for c in jload(products / "paths.json")["candidates"]}
    wanted = [brief["as_is"]["cand_id"]] + [s["cand_id"] for s in sorted(brief.get("structures", []), key=lambda s: s.get("structure_rank") or 99)]
    base = baseline_cand(products)
    if base:
        wanted.append(base)
    for jp in brief.get("judgment_points", []):
        for side in ("first_if_favourable", "first_if_unfavourable"):
            c = (jp.get(side) or {}).get("cand_id")
            if c:
                wanted.append(c)
    seen, out = set(), {}
    used = set(base_names.values())
    letters = iter("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    for cid in wanted:
        if cid in seen or cid not in paths:
            continue
        seen.add(cid)
        sig = signature(paths[cid])
        if sig in base_names:
            name = base_names[sig]
        elif cid == brief["as_is"]["cand_id"]:
            name = "Current structure"
        else:
            name = next("Plan %s" % l for l in letters if "Plan %s" % l not in used)
            used.add(name)
        out[cid] = {"name": name, "signature": sig, "label": " → ".join(node_words(n) for n in paths[cid]["path"]),
                    "moves": paths[cid].get("moves") or [], "restructure": paths[cid].get("restructure") or [],
                    "move_words": [move_words(*m) for m in moves_of(products, paths[cid])]}
    return out


def conduct_names(products, names):
    """(key, cand_id) -> {name, label, ...} for the structures of a conduct run (products/conduct/<key>/): a structure the main run
    names keeps its name (the remit move aside), another takes the next free letter."""
    out = {}
    used = {v["name"] for v in names.values()}
    letters = iter("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    core = lambda sig: re.sub(r"remit\((?:true|false)\),?|,?remit\((?:true|false)\)", "", sig).replace("|  |", "| - |")
    by_core = {core(v["signature"]): v["name"] for v in names.values()}
    for sub in sorted((products / "conduct").glob("*")) if (products / "conduct").exists() else []:
        if not (sub / "brief.json").exists():
            continue
        cb = jload(sub / "brief.json")
        paths = {c["cand_id"]: c for c in jload(sub / "paths.json")["candidates"]}
        seq = cb.get("sequence") or {}
        for cid in [(cb.get("best") or {}).get("cand_id"), (seq.get("this_payment") or {}).get("cand_id"), (seq.get("later") or {}).get("cand_id")]:
            if not cid or cid not in paths or (sub.name, cid) in out:
                continue
            sig = signature(paths[cid])
            name = by_core.get(core(sig))
            if not name:
                name = next("Plan %s" % l for l in letters if "Plan %s" % l not in used)
                used.add(name)
                by_core[core(sig)] = name
            out[(sub.name, cid)] = {"name": name, "signature": sig, "label": " → ".join(node_words(n) for n in paths[cid]["path"]),
                                    "moves": paths[cid].get("moves") or [], "restructure": paths[cid].get("restructure") or [],
                                    "move_words": [move_words(*m) for m in moves_of(sub, paths[cid])]}
    return out


def dest_words(brief):
    """'Singapore' for the jurisdiction the money ends in (the first destination of the recommended structure)."""
    path = (brief.get("best") or {}).get("path") or []
    return JUR.get(path[-1].split(":")[0], path[-1].split(":")[0].upper()) if path else "the destination"


def baseline_cand(products):
    """The structure the savings are measured against (optimization spec §4.7), from the deltas of the first structure."""
    brief = jload(products / "brief.json")
    fb = ((brief.get("best") or {}).get("all_favourable") or {}).get("branch_id")
    d = next((x for x in jload(products / "deltas.json")["deltas"] if x["branch_id"] == fb), {}) if fb else {}
    b = d.get("baseline_branch")
    return b.split(".")[0] if b else None


def payback_words(pb, restructure, saving):
    if not restructure:
        return "none needed"
    if pb is None:
        return "not repaid" if saving is not None and saving <= 0 else "open"
    if pb == 0:
        return "none needed"
    if pb < 1:
        return "within the first payment"
    return "%.1f payments" % pb


def move_words(move, tail, head):
    """remit(false) on hk:company -> sg:company -> 'the dividend is kept outside Singapore (not received there)'."""
    name, _, arg = move.partition("(")
    arg, where = arg.rstrip(")"), JUR.get(head.split(":")[0], head.split(":")[0].upper())
    if name == "remit":
        return "the dividend %s is %s" % ("from the %s" % node_words(tail), "kept outside %s (not received there)" % where if arg == "false" else "received in %s" % where)
    if name == "wait_months":
        return "the dividend is paid only once the %s has held the shares for %s months" % (node_words(head), arg)
    if name == "holding_pct":
        return "the %s raises its holding in the payer to %s%%" % (node_words(head), arg)
    return move


def moves_of(products, cand):
    """[(move, tail, head)] of a candidate, from the edges it takes."""
    edges = {e["edge_id"]: e for e in jload(products / "graph.json")["edges"]}
    return [(m, edges[e]["tail"], edges[e]["head"]) for e in cand.get("edges", []) for m in edges[e]["moves"]]


def fact_words(key, value):
    w = FACT_WORDS.get(key)
    if isinstance(value, bool) and w:
        return w[0] if value else w[1]
    if key == "employees_in_jurisdiction" and value is not None:
        return "%s employees there" % value
    if key == "parent_jur" and value:
        return "parent resident in %s" % JUR.get(str(value), str(value).upper())
    if key == "parent_holding_pct" and value is not None:
        return "%s%% held by that parent" % value
    return "%s: %s" % (key.replace("_", " "), value)


def legs(row, gross, side):
    """[(hop words, amount)] of one branch on one side; None when the hops do not add up to the branch amount."""
    amt, out = float(gross), []
    for h in row["hops"]:
        t = float((h.get(side) or {}).get("t") or 0)
        tax = t * amt
        out.append(("%s → %s" % (node_words(h["tail"]), node_words(h["head"])), tax))
        amt -= tax
    total = float(row["amount"][side])
    return out if abs(sum(x for _, x in out) - total) < 1 else None


def flow_spec(case_id, pd, names, brief, by_branch, gross, ccy):
    """The flowchart of Part 1 (2026-11-12, the program's, drawn by render_pdf): the holding chain as it is and as recommended,
    the dividend's route on each, and the moves between them (changes of holder, and what the group must do). Entity names
    come from facts.json "names" when the front recorded them, otherwise from the jurisdiction ("Hong Kong company")."""
    inp = jload(pd / "input.json")
    paths = {c["cand_id"]: c for c in jload(pd / "paths.json")["candidates"]}
    fp = CASES / case_id / "intake" / "facts.json"
    legal = (jload(fp).get("names") or {}) if fp.exists() else {}
    payer = "%s:company" % inp["payer"]["jur"]
    payee = "%s:%s" % (inp["payee"]["jur"], inp["payee"].get("subject", "company"))
    pay = dict((inp.get("payee") or {}).get("facts") or {}, **(inp.get("payment") or {}))   # the payment facts may sit with the payee
    holder = {payer: (payee, pay.get("holding_pct"))}
    for node, e in (inp.get("entities") or {}).items():
        if e.get("holds"):
            holder.setdefault(e["holds"], (node, e.get("holding_pct")))
    if payee not in holder and pay.get("parent_jur"):
        holder[payee] = ("%s:company" % pay["parent_jur"], pay.get("parent_holding_pct"))

    def chain_of(path):
        """Top holder first, the paying company last: the dividend's route upwards, then the known holders above its end."""
        above, node = [], path[-1]
        while node in holder and holder[node][0] not in path and holder[node][0] not in above and len(above) < 6:
            node = holder[node][0]
            above.append(node)
        return list(reversed(above)) + list(reversed(path))

    def label(node):
        words = node_words(node)
        return words[:1].upper() + words[1:]

    def box(node):
        return {"name": legal[node], "note": label(node)} if legal.get(node) else {"name": label(node)}

    def pct(x):
        return ("%g" % float(x)) if x is not None else None

    def holds(chain):
        out = []
        for up, down in zip(chain, chain[1:]):
            h = holder.get(down)
            out.append("holds %s%%" % pct(h[1]) if h and h[0] == up and h[1] is not None else "holds")
        return out

    def tax_of(cid):
        s = next((x for x in brief.get("structures", []) if x["cand_id"] == cid), None)
        row = by_branch.get(((s or {}).get("all_favourable") or {}).get("branch_id"))
        if row is None:
            rows = [r for r in by_branch.values() if r["cand_id"] == cid]
            row = min(rows, key=lambda r: r["amount"]["floor"]) if rows else None
        return row["amount"]["floor"] if row else None

    def panel(cid, title):
        path = paths[cid]["path"]
        chain = chain_of(path)
        tax = tax_of(cid)
        return chain, {"title": title, "chain": [box(n) for n in chain], "holds": holds(chain), "dividend_to": chain.index(path[-1]),
                       "dividend_label": "Dividend %s %s" % (ccy, money(gross)),
                       "result": "Tax on this dividend: %s %s" % (ccy, money(tax)) if tax is not None else ""}

    as_is, best = brief["as_is"]["cand_id"], brief["best"]["cand_id"]
    now, current = panel(as_is, "Current structure")
    then, target = panel(best, "Recommended structure: %s" % names.get(best, {}).get("name", ""))
    moves = []
    for up, down in zip(then, then[1:]):
        if down not in now:
            moves.append("a %s is added to the chain" % node_words(down))
        elif (holder.get(down) or (None,))[0] != up and up in then:
            moves.append("the %s holds the %s directly" % (node_words(up), node_words(down)))
    moves += list(names.get(best, {}).get("move_words") or [])
    if not moves:
        moves = ["holdings unchanged"]
    elif not any("chain" in m or "directly" in m for m in moves):
        moves.insert(0, "holdings unchanged")
    return {"current": current, "target": target, "steps_title": "From the current to the recommended structure",
            "steps": [m[:1].upper() + m[1:] for m in moves]}


def build_frame(case_id, run_id, base_run=None):
    """report/<run_id>/frame/: names.json, blocks/<name>.md, blocks.sources.json and frame.md (what the section writers read)."""
    pd, fd = products_dir(case_id, run_id), frame_dir(case_id, run_id)
    shutil.rmtree(fd, ignore_errors=True)
    (fd / "blocks").mkdir(parents=True)
    brief, tax = jload(pd / "brief.json"), jload(pd / "tax.json")
    names = name_structures(pd, baseline_names(case_id, base_run))
    by_branch = {r["branch_id"]: r for r in tax["taxes"]}
    by_cand = {}
    for r in tax["taxes"]:
        by_cand.setdefault(r["cand_id"], []).append(r)
    gross, ccy = tax["amount"], tax.get("currency", "")
    rel = "intake/products/%s/" % run_id
    sources, n = [], [0]

    def src(where, claim, ref):
        n[0] += 1
        sid = "f-%03d" % n[0]
        sources.append({"id": sid, "where": where, "claim": claim, "kind": "product", "ref": rel + ref})
        return sid

    rows = {s["cand_id"]: s for s in brief.get("structures", [])}
    blocks = {}

    # tax comparison: per structure, under the answers favourable to the group (the assumptions declared once at the head)
    deltas = {d["branch_id"]: d for d in jload(pd / "deltas.json")["deltas"]}
    complete = {c["cand_id"]: c.get("path_complete", True) for c in jload(pd / "paths.json")["candidates"]}
    base_cid = baseline_cand(pd)
    base_name = names.get(base_cid, {}).get("name", "the route without restructuring") if base_cid else "the route without restructuring"
    lines = ["| Structure | Route | Tax at each step (%s) | Tax on this dividend (%s) | Saved per payment against %s (%s) | One-off cost (%s) | Payback |"
             % (ccy, ccy, base_name, ccy, ccy), "|---|---|---|---|---|---|---|"]
    kept = []                                          # what each structure's figure asks the group to do, and its cost if not done
    for cid, nm in names.items():
        s_ = rows.get(cid)
        branches = by_cand.get(cid, [])
        fav = by_branch.get(((s_ or {}).get("all_favourable") or {}).get("branch_id")) or (min(branches, key=lambda r: r["amount"]["floor"]) if branches else None)
        if not fav:
            continue
        lf = legs(fav, gross, "floor")
        steps = "; ".join("%s: %s" % (w, money(a)) for w, a in lf) if lf else "see total"
        total = span(fav["amount"]["floor"], fav["amount"]["ceiling"])
        d = deltas.get(fav["branch_id"]) or {}
        sv = (d.get("saving_per_payment") or {}).get("floor")
        if cid == base_cid:
            saving = "—"
        elif not complete.get(cid, True):
            saving = "— (the money stops here)"
        else:
            saving = money(sv) if sv is not None else "—"
        oo = ((d.get("one_off_cost") or {}).get("total") or {})
        if not nm["restructure"]:
            one_off = "none"
        elif oo.get("floor") is not None:
            one_off = money(oo["floor"])
        else:
            flags = [FLAG.get(f, f.replace("_", " ")) for f in (s_ or {}).get("one_off_flags", [])]
            one_off = "not yet quantifiable (%s)" % "; ".join(flags) if flags else "not yet quantifiable"
        pb = payback_words(d.get("payback_payments"), nm["restructure"], sv)
        lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (nm["name"], nm["label"], steps, total, saving, one_off, pb))
        src("Part 5 table, row %s" % nm["name"], "tax %s; saved per payment %s against %s; one-off %s; payback %s; branch %s"
            % (total, saving, base_name, one_off, pb, fav["branch_id"]), "deltas.json")
        for x in d.get("if_move_not_kept") or []:
            if x.get("amount") is None or x.get("delta") is None:
                continue
            words = move_words(x["move"], *x["hop"])
            alt = span(x["amount"]["floor"], x["amount"]["ceiling"])
            lo, hi = sorted((x["delta"]["amount"]["floor"], x["delta"]["amount"]["ceiling"]))
            more = span(lo, hi)
            extra = "" if hi < 0.5 else " (up to %s %s more)" % (ccy, money(hi)) if lo < 0.5 else " (%s %s more)" % (ccy, more)
            kept.append("- %s: its figure of %s %s assumes that %s. If that is not done, the tax on this dividend is %s %s%s." % (
                nm["name"], ccy, total, words, ccy, alt, extra))
            src("Part 5 note, %s not kept on %s" % (x["move"], nm["name"]), "tax %s if %s is not kept; delta %s; variant branch %s"
                % (alt, x["move"], more, x.get("branch_id")), "variants.json")
    blocks["tax_table"] = ("\n".join(lines) + "\n\nEvery figure assumes the points listed at the head of this opinion are answered in the group's "
                           "favour (Appendix A). The saving is measured against %s, the route the money takes today without any restructuring. "
                           "The one-off cost counts the taxes the restructuring itself triggers when it is carried out. Payback = one-off cost ÷ "
                           "saving per payment, counting payments of the same amount; not discounted." % base_name
                           + ("\n\nWhat the figures ask the group to do:\n\n" + "\n".join(kept) if kept else ""))

    # assumptions of the recommended structure: the judgment points its figures rest on, with the facts on file bearing on them
    inp = jload(pd / "input.json")
    best_fb = ((brief.get("best") or {}).get("all_favourable") or {}).get("branch_id")
    bt = by_branch.get(best_fb) or {}
    oi = {(o["key"], o.get("about")): o for o in jload(pd / "open_items.json")["open_items"] if o.get("kind") == "tax"}
    head_of = {h["edge_id"]: h["head"] for h in bt.get("hops", [])}
    derived = {}
    for eid, dd in (bt.get("derived_facts") or {}).items():
        for k, v in dd.items():
            derived.setdefault(head_of.get(eid), {})[k] = v.get("value")

    def facts_of(node):
        if node == "%s:%s" % (inp["payee"]["jur"], inp["payee"].get("subject", "company")):
            f = dict(inp["payee"].get("facts") or {})
        else:
            f = dict(((inp.get("entities") or {}).get(node) or {}).get("facts") or {})
        f.update(derived.get(node) or {})               # a fact the structure itself sets wins over the statement of the structure as it is
        return f
    lines = ["| Point assumed in the group's favour | Concerns | Facts on file that bear on it |", "|---|---|---|"]
    about = bt.get("answers_about") or {}
    best_c0 = (brief.get("best") or {}).get("cand_id")
    for key, ans in sorted((bt.get("answers_assumed") or {}).items()):
        node = about.get(key) or ""
        o = oi.get((key, node)) or oi.get((key, None)) or {}
        f = facts_of(node)
        stands = {x["variable"]: x["stands"] for p_ in ((brief.get("premises") or {}).get(best_c0) or []) if p_["key"] == key for x in p_["factors"]}
        facts = "; ".join(fact_words(v, f[v]) + (" (against)" if stands.get(v) == "against" else "")
                          for v in (o.get("factor_vars") or []) if v in f) or "—"
        lines.append("| %s (%s) | %s | %s |" % (point_words(key), "assumed met" if ans == "yes" else "assumed not to apply", node_words(node) if node else "—", facts))
        src("Appendix A assumptions table, row %s" % point_words(key), "assumed %s on %s; facts on file: %s" % (ans, node, facts), "open_items.json")
    best_c = (brief.get("best") or {}).get("cand_id")
    for o in jload(pd / "open_items.json")["open_items"]:
        if o.get("kind") == "one_off" and o.get("need") == "DISCRETION" and any(b.split(".")[0] == best_c for b in o.get("blocks", [])):
            lines.append("| %s (assumed met) | the restructuring | — |" % ONE_OFF_POINT.get(o["key"], o["key"].replace("_", " ")))
            src("Appendix A assumptions table, row %s" % o["key"], "one-off assumption, favourable answer taken", "open_items.json")
    blocks["assumptions_table"] = "\n".join(lines)

    # facts the client can still supply that change the conclusion
    gaps = [g for g in (brief.get("decision_gaps") or []) if g.get("need") == "MISSING" and g.get("client_supplies", True)]
    if gaps:
        blocks["gaps_list"] = "\n".join("- %s" % (g.get("question") or g.get("need") or g.get("key")) for g in gaps)
        src("Gaps list", "%d facts that change the conclusion" % len(gaps), "brief.json")

    # the client's own choices: this dividend and later ones, as things are and with the conduct the other way (§4.7a)
    cnames = conduct_names(pd, names)
    dest = dest_words(brief)
    seq = brief.get("sequence") or {}
    conduct = [c for c in brief.get("conduct") or [] if c.get("stated") is None and c.get("changes_rank")]
    nm = lambda cid, key=None: (cnames.get((key, cid)) if key else names.get(cid)) or {"name": "the structure %s" % cid}

    def world(label, s, key=None):
        if not s or not s.get("this_payment") or not s.get("later"):
            return None
        tp, lt = s["this_payment"], s["later"]
        later_tax = money(lt["amount"]["floor"])
        return "| %s | %s | %s | %s | %s |" % (label, nm(tp["cand_id"], key)["name"], money(tp["amount"]["floor"]),
                                              nm(lt["cand_id"], key)["name"] + (" (once the holding period has run)" if s.get("later_from") else ""), later_tax)
    rows_c = []
    if conduct:
        rows_c.append(world("The money may stay outside %s" % dest, seq))
        for c in conduct:
            rows_c.append(world("The money must be brought into %s" % dest, c.get("sequence_if_not_kept"), c["products"].split("/")[-1]))
    elif seq.get("same") is False:
        rows_c.append(world("As instructed", seq))
    rows_c = [r for r in rows_c if r]
    if rows_c:
        blocks["choices_table"] = "\n".join(["| If | Structure for this dividend | Tax on this dividend (%s) | Structure for later dividends | Tax on each later dividend (%s) |" % (ccy, ccy),
                                             "|---|---|---|---|---|"] + rows_c)
        src("Part 1 table of the group's choices", "; ".join(rows_c), "brief.json")

    # what each figure rests on: the money received where it ends, every point against the group
    lines = ["| Structure | Tax as planned (%s) | If the money is brought into %s (%s) | If every point goes against the group (%s) |" % (ccy, dest, ccy, ccy),
             "|---|---|---|---|"]
    for cid, nmx in names.items():
        s_ = rows.get(cid)
        if not s_ or not s_.get("all_favourable"):
            continue
        planned = s_["all_favourable"]["amount"]["floor"]
        rem = next((x for x in s_.get("if_move_not_kept") or [] if x.get("move") == "remit(false)" and x.get("amount")), None)
        brought = money(rem["amount"]["floor"]) if rem else money(planned)
        worst = (s_.get("all_unfavourable") or {}).get("amount") or {}
        lines.append("| %s | %s | %s | %s |" % (nmx["name"], money(planned), brought, money(worst["ceiling"]) if worst.get("ceiling") is not None else "—"))
    if len(lines) > 3:
        blocks["robustness_table"] = "\n".join(lines)
        src("Part 5 table of what each figure rests on", "; ".join(lines[2:]), "brief.json")

    flow = flow_spec(case_id, pd, names, brief, by_branch, gross, ccy)
    (fd / "blocks" / "flow.json").write_text(json.dumps(flow, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in blocks.items():
        (fd / "blocks" / ("%s.md" % k)).write_text(v + "\n", encoding="utf-8")
    (fd / "blocks.sources.json").write_text(json.dumps(sources, ensure_ascii=False, indent=1), encoding="utf-8")
    (fd / "names.json").write_text(json.dumps(names, ensure_ascii=False, indent=1), encoding="utf-8")
    best = names.get(brief["best"]["cand_id"], {})
    lines = ["# Frame of the draft for run %s" % run_id, "",
             "Written by the program from this run's products. Use these names for the structures, exactly. The program adds the tables "
             "below to the client copy; do not copy them into your text.", "",
             "## Structure names", ""]
    for cid, nm in names.items():
        lines.append("- **%s**: %s; what it asks the group to do: %s; restructuring: %s (signature `%s`)%s" % (
            nm["name"], nm["label"], "; ".join(nm.get("move_words") or []) or "nothing beyond the route", ", ".join(nm["restructure"]) or "none", nm["signature"],
            " — the structure the optimizer ranks first" if cid == brief["best"]["cand_id"] else ""))
    for (key, cid), nmx in cnames.items():
        lines.append("- **%s** with the money brought into %s: %s; what it asks the group to do: %s; restructuring: %s (signature `%s`); used where the money must be brought into %s" % (
            nmx["name"], dest, nmx["label"], "; ".join(nmx.get("move_words") or []) or "nothing beyond the route", ", ".join(nmx["restructure"]) or "none",
            nmx["signature"], dest))
    lines += ["", "The plan is built on **%s**." % best.get("name", "?"), ""]
    lines += frame_strategy(brief, names, cnames, ccy, dest)
    lines += word_limits(fd)
    lines += ["## Tables (markers)", ""]
    for k, v in blocks.items():
        lines += ["### {{block:%s}}" % k, "", v, ""]
    (fd / "frame.md").write_text("\n".join(lines), encoding="utf-8")
    return {"names": names, "blocks": sorted(blocks), "sources": len(sources)}


def word_limits(fd):
    """frame.md: each part's word limit (agent/tools/report_limits.json with this frame's counts). The one thing of the template
    the writer is told (2026-11-12, the user's decision): first drafts ran two to four times over and were cut part by part."""
    import report_form                                  # it imports this module: a late import
    words = {"head": "The opening before Part 1", "A": "Appendix A"}
    rows = [(k, report_form.limit_of(k, fd)) for k in ["head", "1", "2", "3", "4", "5", "6", "7", "A"]]
    out = ["## Word limits", "",
           "Write each part within its limit from the first draft. Counted: the prose only; citation markers, quoted passages, tables, "
           "headings and program markers are not counted, and a CJK character counts as half a word. report_check names a part that "
           "runs over.", "", "| Part | At most (words) |", "|---|---|"]
    out += ["| %s | %d |" % (words.get(k, "Part %s" % k), n) for k, n in rows if n]
    return out + [""]


def frame_strategy(brief, names, cnames, ccy, dest):
    """frame.md sections for the strategy (§4.7a of the optimization spec): the client's own choices, this dividend and later
    ones, the position as it stands, the facts each point rests on, and the figures the report must state."""
    m = lambda a: "%s %s" % (ccy, money(a["floor"])) if isinstance(a, dict) and a.get("floor") is not None else "—"
    nm = lambda cid, key=None: ((cnames.get((key, cid)) if key else names.get(cid)) or {}).get("name", "the structure %s" % cid)
    out = ["## The group's own choices", ""]
    rows = brief.get("conduct") or []
    if not rows:
        out += ["None this structure depends on.", ""]
    for c in rows:
        if c.get("stated") is not None:
            out += ["- %s Stated: %s; a fact of the plan, not an assumption." % (c.get("question") or c["key"], "yes" if c["stated"] else "no"), ""]
            continue
        f = c.get("first_if_not_kept") or {}
        key = c["products"].split("/")[-1]
        out += ["- %s The client has not said. The figures above assume the answer that keeps the money outside %s." % (c.get("question"), dest),
                "  - If the money must be brought into %s and the recommended structure stays, the tax on this dividend is %s." % (dest, m(c.get("same_structure_if_not_kept"))),
                "  - Then **%s** comes first instead (%s): %s per payment, saving %s per payment against bringing the money in through the present route%s." % (
                    nm(f.get("cand_id"), key), " > ".join(node_words(n) for n in f.get("path") or []), m(f.get("amount")), m(c.get("saving_of_switching")),
                    "; one-off cost %s, payback %s" % (m(f.get("one_off_total")) if (f.get("one_off_total") or {}).get("floor") is not None else "not yet quantifiable",
                                                       payback_words(f.get("payback_payments"), f.get("restructure"), (f.get("saving_per_payment") or {}).get("floor")))
                    if f.get("restructure") else ""),
                "  - Write both in Part 1: the group's choice decides the plan. Name the question in Appendix A as a point for the group to decide.", ""]

    def seq_lines(s, key, label):
        if not s or not s.get("this_payment"):
            return []
        tp, lt = s["this_payment"], s["later"]
        if s.get("same"):
            return ["- %s: this dividend and later dividends both go through **%s** (%s each)." % (label, nm(tp["cand_id"], key), m(tp["amount"]))]
        o = s.get("other_order") or {}
        why = o.get("why") if o.get("open") is False else ("restructuring before this dividend would cost %s more on it" % m(o.get("cost"))) if o.get("open") else ""
        return ["- %s: this dividend goes through **%s** (%s); later dividends through **%s** (%s each)%s.%s" % (
            label, nm(tp["cand_id"], key), m(tp["amount"]), nm(lt["cand_id"], key), m(lt["amount"]),
            " once the new holder has held the shares for %s months, the period the reduced rate needs" % re.sub(r"\D", "", s["later_from"]) if s.get("later_from") else "",
            " Order: pay this dividend first, then restructure; %s." % why if why else "")]
    out += ["## This dividend and later dividends", ""]
    out += seq_lines(brief.get("sequence"), None, "As the figures above stand")
    for c in rows:
        if c.get("stated") is None and c.get("changes_rank"):
            out += seq_lines(c.get("sequence_if_not_kept"), c["products"].split("/")[-1], "If the money must be brought into %s" % dest)
    s0 = brief.get("sequence") or {}
    if s0.get("declared_to_payee") is None:
        out += ["- Whether this dividend is already declared to its present recipient is not on file; where it is, this dividend cannot follow a restructuring."]
    out += ["", "## What is wrong with the position as it stands (Part 2)", ""]
    words = {"as_is_stops_short": "The money stops at the present recipient, short of where the client wants it; the tax as things stand is %s", "as_is_points_at_stake": "Tax resting on points not yet confirmed: %s",
             "conduct_not_stated": "A choice of the group's decides the plan (see above); switching saves %s per payment", "conduct_relied_on": "The recommended figure assumes a step the group must keep; if it does not, the tax is %s",
             "refund": "Tax overpaid on an earlier dividend can be reclaimed: %s", "conflict": "The documents and the client's account of an earlier dividend differ"}
    for d in brief.get("diagnosis") or []:
        w = words.get(d["kind"], d["kind"])
        amt = d.get("amount")
        if amt and d["kind"] == "conduct_not_stated":
            amt = {"floor": amt.get("floor"), "ceiling": amt.get("floor")}      # a saving is stated on the favourable side
        txt = w % (m(amt) if amt and (amt.get("floor") == amt.get("ceiling")) else "%s to %s" % (m(amt), m({"floor": amt["ceiling"]})) if amt else "") if "%s" in w else w
        if d["kind"] == "refund":
            txt += "; claim by %s" % d.get("limit")
        out.append("- %s." % txt.rstrip("."))
    out += ["", "## Facts on file for each point (Part 7 and Appendix A)", "",
            "Facts against a point that the group can change are steps for Part 7 (make the point stronger before payment); facts not known are questions for Appendix A.", ""]
    best = (brief.get("best") or {}).get("cand_id")
    for p in (brief.get("premises") or {}).get(best) or []:
        fs = p.get("factors") or []
        if not fs:
            continue
        out.append("- %s, for the %s: %s." % (point_words(p["key"]), node_words(p.get("about") or ""),
                                              "; ".join(("%s %s" % (fact_words(f["variable"], f["value"]) if f["value"] not in (None, "") else f["variable"].replace("_", " "),
                                                                   "(against)" if f["stands"] == "against" else "(not known)" if f["stands"] == "not known" else "")).strip()
                                                        for f in fs)))
    out += ["", "## Figures the report must state", ""]
    out += ["- %s %s: %s" % (ccy, money(x["figure"]), x["why"]) for x in brief.get("must_state") or []]
    return out + [""]


# ------------------------------------------------------------ sections
def split_draft(text):
    """A briefing.md -> {section id: text}. head = everything before Part 1; end = the internal reference line."""
    out, cur, buf = {}, "head", []
    for line in text.splitlines():
        m = re.match(r"^##\s+(?:(\d)\.|Appendix\s+([AB])\b)", line)
        if m:
            out[cur] = "\n".join(buf).strip("\n")
            cur, buf = (m.group(1) or m.group(2)), []
        buf.append(line)
    out[cur] = "\n".join(buf).strip("\n")
    tail = out.get("B", "")
    m = re.search(r"\n-{3,}\s*\n(?=[^\n]*Internal reference)", tail)
    if m:
        out["B"], out["end"] = tail[:m.start()].rstrip(), tail[m.end():].strip()
    return out


def section_rows(rows, sid):
    """The sources of a parsed draft that belong to one part (by where)."""
    if sid == "head":
        pat = re.compile(r"^(Heading|Basis|Opening|Declaration)", re.I)
    elif sid in "1234567":
        pat = re.compile(r"^Part\s*%s\b" % sid, re.I)
    else:
        pat = re.compile(r"^Appendix\s*%s\b" % sid, re.I)
    return [r for r in rows if pat.match(str(r.get("where", "")))]


def carry(case_id, run_id, base_run, keep):
    """Copy the parts `keep` of the last edition's draft into this run's sections, with their sources; product refs move to this run
    where the same file exists. Returns the parts carried."""
    bd = report_dir(case_id, base_run)
    if not (bd / "briefing.md").exists():
        return []
    parts = split_draft((bd / "briefing.md").read_text(encoding="utf-8"))
    rows = rows_of(jload(bd / "briefing.sources.json")) if (bd / "briefing.sources.json").exists() else []
    sd = sec_dir(case_id, run_id)
    sd.mkdir(parents=True, exist_ok=True)
    done = []
    for sid in keep:
        if sid not in parts or sid in PROGRAM:
            continue
        mine = []
        for r in section_rows(rows, sid):
            r = dict(r)
            ref = str(r.get("ref", ""))
            moved = ref.replace("products/%s/" % base_run, "products/%s/" % run_id)
            if moved != ref and (CASES / case_id / moved.split("#")[0].split(" ")[0]).exists():
                r["ref"] = moved
            r["id"] = "%s-%s" % (sid, r["id"]) if not str(r["id"]).startswith(sid + "-") else r["id"]
            mine.append(r)
        (sd / ("%s.md" % sid)).write_text(parts[sid] + "\n", encoding="utf-8")
        (sd / ("%s.sources.json" % sid)).write_text(json.dumps(mine, ensure_ascii=False, indent=1), encoding="utf-8")
        done.append(sid)
    return done


def appendix_b(rows):
    """Appendix B from the cited sources: library provisions grouped by law, web texts, the client's documents."""
    docs = {r["id"]: r for r in csv.DictReader(open(DB / "doc.csv", encoding="utf-8-sig"))}
    labels = {r["cite_id"]: r["label"] for r in csv.DictReader(open(DB / "clause.csv", encoding="utf-8-sig"))}
    by_doc = {}
    for r in rows:
        if r.get("kind") != "cite":
            continue
        for cite in re.findall(r"[a-z]{2}[\w.\-]*#[\w.\-()]+", str(r.get("ref", ""))):
            doc = cite.split("#")[0]
            by_doc.setdefault(doc, set()).add(labels.get(cite, cite.split("#")[1]))
    lines = ["## %s" % TITLES["B"], "", "**Provisions relied on**", ""]
    for doc in sorted(by_doc, key=lambda d: (d.split(".")[0], docs.get(d, {}).get("title", d))):
        title = docs.get(doc, {}).get("title", doc)
        lines.append("- %s: %s" % (title, ", ".join(sorted(by_doc[doc], key=lambda s: (len(s), s)))))
    urls = sorted({"%s (%s)" % (r.get("claim", "").strip()[:120], r.get("ref", "")) for r in rows if r.get("kind") == "url"})
    if urls:
        lines += ["", "**Official texts consulted on government websites**", ""] + ["- %s" % u for u in urls]
    client = sorted({m for r in rows if r.get("kind") == "document" for m in re.findall(r"documents/([^\s,;#)]+)", str(r.get("ref", "")))})
    if client:
        lines += ["", "**Your documents relied on**", ""] + ["- %s" % c for c in client]
    return "\n".join(lines)


def assemble(case_id, run_id, version=""):
    """briefing.md and briefing.sources.json from the section files, the frame blocks and the program parts."""
    sd, fd, rd = sec_dir(case_id, run_id), frame_dir(case_id, run_id), report_dir(case_id, run_id)
    blocks = {p.stem: p.read_text(encoding="utf-8").strip() for p in (fd / "blocks").glob("*.md")} if (fd / "blocks").exists() else {}
    block_rows = rows_of(jload(fd / "blocks.sources.json")) if (fd / "blocks.sources.json").exists() else []
    used, texts, rows = set(), [], []
    for sid in ORDER:
        if sid in PROGRAM:
            continue
        p = sd / ("%s.md" % sid)
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8").strip()

        def put(m):
            used.add(m.group(1))
            return blocks.get(m.group(1), m.group(0))
        texts.append(MARK.sub(put, text))
        sp = sd / ("%s.sources.json" % sid)
        if sp.exists():
            rows += rows_of(jload(sp))
    extra = sd / "extra.sources.json"
    if extra.exists():
        rows += rows_of(jload(extra))
    names = jload(fd / "names.json") if (fd / "names.json").exists() else {}
    body = "\n".join(texts)
    if names:                                                                 # names come from the frame, one row each
        rows = [r for r in rows if r.get("kind") != "name"]
        rows += [{"id": "name-%s" % nm["name"].replace(" ", "_"), "where": "Name: '%s'" % nm["name"], "claim": nm["label"], "kind": "name",
                  "ref": nm["signature"]} for nm in names.values() if re.search(r"(?<!\w)%s(?!\w)" % re.escape(nm["name"]), body)]
    want = {"tax_table": "Part 5 table", "assumptions_table": "Appendix A assumptions table", "gaps_list": "Gaps list"}
    rows += [r for r in block_rows if any(want[b] in r["where"] for b in used if b in want)]
    texts.append(appendix_b(rows))
    texts.append("---\n<span style=\"font-size:0.8em\">Internal reference: %s · run %s%s.</span>" % (case_id, run_id, " · products " + version if version else ""))
    for name, content in (("briefing.md", "\n\n".join(texts) + "\n"), ("briefing.sources.json", json.dumps(rows, ensure_ascii=False, indent=1))):
        path = rd / name
        if path.exists():
            shutil.copyfile(path, path.with_name(name + ".prev"))
        path.write_text(content, encoding="utf-8")
    return {"parts": [s for s in ORDER if (sd / ("%s.md" % s)).exists()], "blocks_used": sorted(used), "sources": len(rows)}


def products_version(case_id, run_id):
    b = products_dir(case_id, run_id) / "brief.json"
    return str(jload(b).get("version", "")) if b.exists() else ""


def missing(case_id, run_id, wanted):
    sd = sec_dir(case_id, run_id)
    return [s for s in wanted if not (sd / ("%s.md" % s)).exists()]
