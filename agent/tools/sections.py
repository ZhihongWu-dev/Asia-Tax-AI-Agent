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
JUR = {"cn": "Mainland China", "hk": "Hong Kong", "sg": "Singapore", "jp": "Japan", "th": "Thailand", "kr": "Korea"}
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
                    "moves": paths[cid].get("moves") or [], "restructure": paths[cid].get("restructure") or []}
    return out


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
    blocks["tax_table"] = ("\n".join(lines) + "\n\nEvery figure assumes the points listed at the head of this opinion are answered in the group's "
                           "favour (Appendix A). The saving is measured against %s, the route the money takes today without any restructuring. "
                           "The one-off cost counts the taxes the restructuring itself triggers when it is carried out. Payback = one-off cost ÷ "
                           "saving per payment, counting payments of the same amount; not discounted." % base_name)

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
    for key, ans in sorted((bt.get("answers_assumed") or {}).items()):
        node = about.get(key) or ""
        o = oi.get((key, node)) or oi.get((key, None)) or {}
        f = facts_of(node)
        facts = "; ".join(fact_words(v, f[v]) for v in (o.get("factor_vars") or []) if v in f) or "—"
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

    for k, v in blocks.items():
        (fd / "blocks" / ("%s.md" % k)).write_text(v + "\n", encoding="utf-8")
    (fd / "blocks.sources.json").write_text(json.dumps(sources, ensure_ascii=False, indent=1), encoding="utf-8")
    (fd / "names.json").write_text(json.dumps(names, ensure_ascii=False, indent=1), encoding="utf-8")
    best = names.get(brief["best"]["cand_id"], {})
    lines = ["# Frame of the draft for run %s" % run_id, "",
             "Written by the program from this run's products. Use these names for the structures, exactly; the tables below are inserted "
             "into the draft by writing their marker on a line of its own; their figures and sources come with them, do not retype them.", "",
             "## Structure names", ""]
    for cid, nm in names.items():
        lines.append("- **%s**: %s; moves: %s; restructuring: %s (signature `%s`)%s" % (
            nm["name"], nm["label"], ", ".join(nm["moves"]) or "none", ", ".join(nm["restructure"]) or "none", nm["signature"],
            " — the structure the optimizer ranks first" if cid == brief["best"]["cand_id"] else ""))
    lines += ["", "The plan is built on **%s**." % best.get("name", "?"), "", "## Tables (markers)", ""]
    for k, v in blocks.items():
        lines += ["### {{block:%s}}" % k, "", v, ""]
    (fd / "frame.md").write_text("\n".join(lines), encoding="utf-8")
    return {"names": names, "blocks": sorted(blocks), "sources": len(sources)}


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
