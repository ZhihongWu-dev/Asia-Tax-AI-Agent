"""Feedback between editions (agent/orchestration_cli_spec.en.md §9): structure signatures, the preview card and the impact of a
new run on the last delivered report. Program only: it reads products, intake files and the baseline draft, and decides by rules."""
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
CASES = PROJECT / "cases"
SPECS = ("agent/analysis_agent_spec.en.md", "agent/polish_agent_spec.en.md")
REVISE_CHAIN_MAX = 3
LIGHT_LINES_MAX = 40
SECTIONS = {"first": ["1", "3", "4", "5", "6", "7"], "scenario": ["1", "5"], "requirements": ["6", "7"], "open": ["7", "A"],
            "one_off": ["4", "6"], "exposure": ["4", "6"], "as_is": ["2"], "structures": ["3", "5"], "answers": ["7", "A"]}


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def last_line(p):
    p = Path(p)
    if not p.exists():
        return ""
    lines = [l.strip() for l in p.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip()]
    return lines[-1] if lines else ""


# ------------------------------------------------------------ signatures
def signatures(products):
    """cand_id -> signature: path, moves and kind of restructuring. Stable across runs, unlike cand_id."""
    out = {}
    for c in jload(Path(products) / "paths.json")["candidates"]:
        out[c["cand_id"]] = "%s | %s | %s" % (">".join(c["path"]), ",".join(sorted(c.get("moves") or [])) or "-",
                                             ",".join(sorted(c.get("restructure") or [])) or "-")
    return out


def labels(products):
    return {c["cand_id"]: (c.get("label") or " > ".join(c["path"])) for c in jload(Path(products) / "brief.json").get("structures", [])}


def scenario_table(products):
    """{scenario_id: {"order": [signature...], "amounts": {signature: amount}}} keyed by signature."""
    sig = signatures(products)
    out = {}
    for s in jload(Path(products) / "scenarios.json")["scenarios"]:
        out[s["scenario_id"]] = {"order": [sig[c] for c in s.get("order", []) if c in sig],
                                 "amounts": {sig[c]: v["amount"] for c, v in (s.get("structures") or {}).items() if c in sig}}
    return out


def first_of(table, scenario="all_favourable"):
    s = table.get(scenario) or {}
    return (s.get("order") or [None])[0]


# ------------------------------------------------------------ the baseline
def ledger(case_id):
    return jload(CASES / case_id / "rounds.json")


def baseline(case_id):
    """The last delivered edition of an earlier round: {round, run_id} or None."""
    led = ledger(case_id)
    for r in sorted(led["rounds"], key=lambda r: -r["round"]):
        if r["round"] == led["current"] or not r.get("run_id"):
            continue
        rd = CASES / case_id / "report" / r["run_id"]
        if last_line(rd / "review_final.md") == "DELIVERABLE":
            return {"round": r["round"], "run_id": r["run_id"]}
    return None


def products_dir(case_id, run_id):
    return CASES / case_id / "intake" / "products" / run_id


def names(case_id, run_id):
    """signature -> the name the report gave the structure (sources entries of kind name)."""
    p = CASES / case_id / "report" / run_id / "briefing.sources.json"
    if not p.exists():
        return {}
    try:
        rows = jload(p)
    except ValueError:
        return {}
    return {r.get("ref"): r.get("where") for r in rows if isinstance(r, dict) and r.get("kind") == "name"}


def spec_sha():
    return hashlib.sha256(b"".join((PROJECT / s).read_bytes() for s in SPECS if (PROJECT / s).exists())).hexdigest()[:16]


# ------------------------------------------------------------ answers and open points
def answer_values(answers):
    return {k: (a.get("value") if isinstance(a, dict) else a) for k, a in (answers or {}).items()}


def pending(products, answers):
    """Points that can still change the first structure: judgment points without yes / no, and fact gaps the client supplies."""
    vals = answer_values(answers)
    out, seen = [], set()
    for o in jload(Path(products) / "open_items.json")["open_items"]:
        if not o.get("changes_rank"):
            continue
        key = o["key"].split("@")[0]
        if o["kind"] == "tax" and vals.get(key) in ("yes", "no"):
            continue
        if o["kind"] == "one_off" and o["key"] == "fx_missing":
            continue
        tag = (o["kind"], o["key"], o.get("about"))
        if tag in seen:
            continue
        seen.add(tag)
        out.append({"kind": o["kind"], "key": o["key"], "about": o.get("about"), "question": o.get("question", "")})
    return out


def relied_on(products, cand_sig):
    """The judgment keys the all-favourable branch of a structure assumes in the client's favour."""
    sig = signatures(products)
    s = next((x for x in jload(Path(products) / "scenarios.json")["scenarios"] if x["scenario_id"] == "all_favourable"), None)
    cid = next((c for c, g in sig.items() if g == cand_sig), None)
    if not s or cid not in (s.get("structures") or {}):
        return {}
    bid = s["structures"][cid]["branch_id"]
    br = next((b for b in jload(Path(products) / "branches.json")["branches"] if b["branch_id"] == bid), None)
    return dict(br.get("answers_assumed") or {}) if br else {}


# ------------------------------------------------------------ the preview card
def card(case_id, products, answers):
    """update.json: what the client learns after a feedback, computed from the products alone (§9.3, §9.4)."""
    products = Path(products)
    table, sig, lab = scenario_table(products), signatures(products), labels(products)
    lab_sig = {sig[c]: l for c, l in lab.items() if c in sig}
    base = baseline(case_id)
    base_table = scenario_table(products_dir(case_id, base["run_id"])) if base else {}
    base_first = first_of(base_table) if base else None
    base_names = names(case_id, base["run_id"]) if base else {}
    first = first_of(table)
    fav = table.get("all_favourable", {})
    worst = table.get("all_unfavourable", {})
    open_points = pending(products, answers)
    vals = answer_values(answers)
    closing = {k for k, v in vals.items() if v in ("yes", "no")}
    t2_reason = ""
    if base_first:
        assumed = relied_on(products_dir(case_id, base["run_id"]), base_first)
        hit = sorted(k for k in assumed if k.split("@")[0] in closing and vals[k.split("@")[0]] != assumed[k])
        if hit:
            t2_reason = "answered against the recommended structure: " + ", ".join(hit)
        elif base_first not in fav.get("amounts", {}):
            t2_reason = "the recommended structure is no longer a complete structure under the constraints"
        else:
            then = (base_table.get("all_favourable", {}).get("amounts") or {}).get(base_first) or {}
            now_ = fav["amounts"][base_first]
            if then and now_.get("floor", 0) > then.get("floor", 0) + 0.005:
                t2_reason = "the recommended structure now costs %s instead of the %s the report states" % ("{:,.0f}".format(now_["floor"]), "{:,.0f}".format(then["floor"]))
    triggers = {"1_all_answered": {"value": not open_points, "reason": "%d point(s) still open" % len(open_points)},
                "2_recommendation_failed": {"value": bool(t2_reason), "reason": t2_reason or "the recommended structure still holds"}}
    def pack(s, table_part):
        return {"signature": s, "label": lab_sig.get(s, s), "name_in_last_report": base_names.get(s), "amount": table_part.get("amounts", {}).get(s)} if s else None
    out = {"case_id": case_id, "products": str(products.relative_to(CASES)).replace("\\", "/"),
           "baseline_run": base["run_id"] if base else None,
           "first": pack(first, fav), "first_changed": bool(base_first) and first != base_first,
           "worst": pack(first_of(table, "all_unfavourable"), worst),
           "baseline_first_now": ({**pack(base_first, fav), "unfavourable": worst.get("amounts", {}).get(base_first),
                                   "name_in_last_report": base_names.get(base_first)} if base_first else None),
           "pending": open_points, "triggers": triggers, "preliminary": True}
    (products / "update.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def card_figures(c):
    """The amounts a relay of the card may state."""
    vals = set()
    for k in ("first", "worst", "baseline_first_now"):
        part = c.get(k) or {}
        for a in (part.get("amount"), part.get("unfavourable")):
            if isinstance(a, dict):
                vals |= {a.get("floor"), a.get("ceiling")}
    return {v for v in vals if isinstance(v, (int, float))}


# ------------------------------------------------------------ impact of a run on the last edition
AMOUNT = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?")


def amounts_in(products):
    """Every amount of one thousand or more that the products state."""
    out = set()

    def walk(x, key=""):
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, k)
        elif isinstance(x, list):
            for v in x:
                walk(v, key)
        elif isinstance(x, (int, float)) and not isinstance(x, bool) and abs(x) >= 1000 and key not in ("rank", "structure_rank"):
            out.add(round(float(x), 2))
    for name in ("scenarios.json", "tax.json", "deltas.json", "brief.json", "past_payments.json"):
        p = Path(products) / name
        if p.exists():
            walk(jload(p))
    return out


def interest_amounts(products):
    out = set()
    p = Path(products) / "deltas.json"
    if p.exists():
        for d in jload(p)["deltas"]:
            ex = d.get("exposure_if_denied") or {}
            for part in [ex] + list(ex.get("cells") or []):
                for k in ("interest", "total"):
                    v = part.get(k) or {}
                    out |= {round(float(x), 2) for x in v.values() if isinstance(x, (int, float))}
    return out


def requirements_sig(products, cand_sig):
    sig = signatures(products)
    cid = next((c for c, g in sig.items() if g == cand_sig), None)
    p = Path(products) / "requirements" / ("%s.json" % cid)
    return hashlib.sha256(p.read_bytes()).hexdigest() if cid and p.exists() else None


def one_off_exposure(products, cand_sig):
    sig = signatures(products)
    cid = next((c for c, g in sig.items() if g == cand_sig), None)
    d = next((x for x in jload(Path(products) / "deltas.json")["deltas"] if x["cand_id"] == cid), None) if cid else None
    if not d:
        return None, None
    ex = dict(d.get("exposure_if_denied") or {})
    ex.pop("interest", None); ex.pop("total", None); ex.pop("as_of", None)
    ex["cells"] = [{k: v for k, v in c.items() if k not in ("interest", "overdue_months")} for c in ex.get("cells") or []]
    return json.dumps(d.get("one_off_cost"), sort_keys=True), json.dumps(ex, sort_keys=True)


def sentences_with(text, figures):
    out = []
    for i, line in enumerate(text.splitlines()):
        for m in AMOUNT.finditer(line):
            v = round(float(m.group(0).replace(",", "")), 2)
            if v in figures:
                a, b = max(0, m.start() - 60), min(len(line), m.end() + 40)
                out.append({"line": i + 1, "figure": m.group(0), "fragment": line[a:b].strip()})
    return out


def section_of(text, line_no):
    sec = ""
    for i, line in enumerate(text.splitlines()[:line_no]):
        m = re.match(r"^##\s+(?:Part\s+)?(\d+|Appendix\s+([A-Z]))", line)
        if m:
            sec = m.group(2) or m.group(1)
    return sec


def intake_now(case_id):
    it = CASES / case_id / "intake"
    return {n: (jload(it / n) if (it / n).exists() else None) for n in ("facts.json", "answers.json", "constraints.json")}


def impact(case_id, run_id, review_says_full=False):
    """impact.json of this run against the last delivered edition: level full / none / revise, sections, stale figures."""
    rd = CASES / case_id / "report" / run_id
    rd.mkdir(parents=True, exist_ok=True)
    new = products_dir(case_id, run_id)
    base = baseline(case_id)
    out = {"run_id": run_id, "baseline_run": base["run_id"] if base else None, "spec_sha": spec_sha(), "intake": intake_now(case_id),
           "level": "full", "reasons": [], "sections": [], "stale": [], "changes": []}
    def done(level, *why):
        out["level"] = level
        out["reasons"] += list(why)
        (rd / "impact.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        return out
    if review_says_full:
        return done("full", "the review or the analysis asked for a full rewrite")
    if not base:
        return done("full", "no delivered edition to revise")
    old = products_dir(case_id, base["run_id"])
    bimp = CASES / case_id / "report" / base["run_id"] / "impact.json"
    bprev = jload(bimp) if bimp.exists() else {}
    vn, vo = jload(new / "version.json"), jload(old / "version.json")
    if vn["rule_version"].get("rule_csv_sha256") != vo["rule_version"].get("rule_csv_sha256") or \
       vn["database_version"].get("doc_csv_sha256") != vo["database_version"].get("doc_csv_sha256"):
        return done("full", "the law in the library changed since the last edition (rule.csv or doc.csv)")
    if bprev.get("spec_sha") and bprev["spec_sha"] != out["spec_sha"]:
        return done("full", "the analysis or polish spec changed since the last edition")
    chain = 0
    led = ledger(case_id)
    for r in sorted((r for r in led["rounds"] if r.get("run_id") and r["round"] < led["current"]), key=lambda r: -r["round"]):
        p = CASES / case_id / "report" / r["run_id"] / "impact.json"
        if p.exists() and jload(p).get("level") == "revise":
            chain += 1
        else:
            break
    out["revise_chain"] = chain + 1
    if chain >= REVISE_CHAIN_MAX:
        return done("full", "%d revised editions in a row" % chain)
    tn, to = scenario_table(new), scenario_table(old)
    fn, fo = first_of(tn), first_of(to)
    discussed = set(signatures(old).values())
    if fn not in discussed:
        return done("full", "the new first structure was not among the structures of the last edition")
    sections, changes = set(), []
    def mark(kind, what):
        sections.update(SECTIONS[kind])
        changes.append({"kind": kind, "what": what})
    if fn != fo:
        mark("first", "first structure %s -> %s" % (fo, fn))
    for sid in sorted(set(tn) | set(to)):
        a, b = tn.get(sid), to.get(sid)
        if a is None or b is None:
            mark("scenario", "scenario %s %s" % (sid, "appeared" if b is None else "vanished"))
        elif a["order"][:3] != b["order"][:3] or a["amounts"] != b["amounts"]:
            mark("scenario", "scenario %s order or amounts" % sid)
    if set(signatures(new).values()) != discussed:
        mark("structures", "structures added %s, removed %s" % (sorted(set(signatures(new).values()) - discussed), sorted(discussed - set(signatures(new).values()))))
    if requirements_sig(new, fn) != requirements_sig(old, fn):
        mark("requirements", "condition tree of the first structure")
    oo_n, ex_n = one_off_exposure(new, fn)
    oo_o, ex_o = one_off_exposure(old, fn)
    if oo_n != oo_o:
        mark("one_off", "one-off cost of the first structure")
    if ex_n != ex_o:
        mark("exposure", "exposure of the first structure")
    on = {(o["kind"], o["key"], o.get("about"), o["changes_rank"]) for o in jload(new / "open_items.json")["open_items"]}
    of = {(o["kind"], o["key"], o.get("about"), o["changes_rank"]) for o in jload(old / "open_items.json")["open_items"]}
    if on != of:
        mark("open", "open items changed")
    bin_ = bprev.get("intake") or {}
    now = out["intake"]
    if bin_ and bin_.get("answers.json") != now.get("answers.json"):
        mark("answers", "answers changed")
    if bin_ and (bin_.get("facts.json") != now.get("facts.json") or bin_.get("constraints.json") != now.get("constraints.json")):
        changes.append({"kind": "facts", "what": "facts or constraints changed"})
    if not bin_:
        changes.append({"kind": "facts", "what": "no intake record of the last edition; facts treated as changed"})
    an, ao = amounts_in(new), amounts_in(old)
    time_only = (ao - an) & interest_amounts(old)
    gone = ao - an - time_only
    draft = CASES / case_id / "report" / base["run_id"] / "briefing.md"
    text = draft.read_text(encoding="utf-8") if draft.exists() else ""
    stale = sentences_with(text, gone)
    for s in stale:
        s["section"] = section_of(text, s["line"])
    out.update(sections=sorted(sections), stale=stale, changes=changes, time_only=sorted(time_only))
    if not changes:
        return done("none", "nothing the report uses changed")
    return done("revise", "the first structure is one the last edition discussed")


# ------------------------------------------------------------ light intake review
def intake_light(case_id, snapshot_dir, snapshot_round):
    """Whether the intake review may check only the changes since the last RUNNABLE of an earlier round, and the diff text."""
    import difflib
    it = CASES / case_id / "intake"
    snap = Path(snapshot_dir)
    docs_now = sorted(p.name for p in (it / "documents").iterdir()) if (it / "documents").exists() else []
    docs_then = (snap / "documents.txt").read_text(encoding="utf-8").splitlines() if (snap / "documents.txt").exists() else None
    if docs_then is None or docs_now != docs_then:
        return None, "documents changed or no document list in the snapshot"
    out = []
    for n in ("facts.json", "sources.json", "answers.json", "notes.md", "constraints.json"):
        old = (snap / n).read_text(encoding="utf-8").splitlines() if (snap / n).exists() else []
        new = (it / n).read_text(encoding="utf-8").splitlines() if (it / n).exists() else []
        out += list(difflib.unified_diff(old, new, n + " (round %s, checked)" % snapshot_round, n + " (now)", lineterm="", n=2))
    changed = sum(1 for l in out if l[:1] in "+-" and not l.startswith(("+++", "---")))
    if changed > LIGHT_LINES_MAX:
        return None, "%d changed lines" % changed
    return "\n".join(out) or "No intake file changed.", ""
