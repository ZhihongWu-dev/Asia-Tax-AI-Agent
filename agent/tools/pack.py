"""Prefetch packs (agent/retrieval_spec.en.md §9): what a node always needs, written by the program before the node starts
to cases/<case>/report/<run_id>/pack/<node>.md (intake/index/pack/ while there is no run). Every item carries its id, which
the agent cites as the ref of the sources table without fetching it again. Values are copied from the indexes, never
recomputed. Sections come in priority order; when the pack would pass LIMIT, whole sections from the end are left out and
named, so nothing is cut in the middle."""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = HERE.parents[1] / "cases"
LIMIT = 36000                     # characters, about 9,000 tokens


def cards(con, sql, args=()):
    return [(r["id"], r["card"]) for r in con.execute(sql, args)]


def loads(card):
    try:
        return json.loads(card)
    except ValueError:
        return {}


def build(reader, case_id, node):
    """Write the pack of `node` for the current run of `case_id`; returns (path, [ids])."""
    rnd, run = reader.current(case_id)
    cd = CASES / case_id
    out_dir = cd / "report" / run / "pack" if run else cd / "intake" / "index" / "pack"     # before a run: with the case-file index
    out_dir.mkdir(parents=True, exist_ok=True)
    sections = []                                  # (title, body, ids) in priority order

    def items(title, rows, fmt=None):
        if rows:
            body = "\n".join("- `%s` %s" % (i, fmt(c) if fmt else c) for i, c in rows)
            sections.append((title, body, [i for i, _ in rows]))

    def text(title, body):
        if body and body.strip():
            sections.append((title, body.strip(), []))

    if node == "polish":
        return polish_pack(case_id, rnd, run, out_dir)
    reading = node in ("analysis", "review_draft", "review_final")
    m = reader.map(case_id)
    text("Files of the case (what map returns; read them through tax-read, not Glob)",
         "\n".join("- %s/: %s" % (f["path"].split("/", 2)[2], ", ".join(x["name"] for x in f["files"])) for f in m.get("folders", [])))
    ccon, _ = reader.casefile(case_id)
    if ccon:
        keys = ("amount", "currency", "date", "instructed_on", "payer.", "payee.", "payment.", "entities.", "destinations", "valuation.", "past_payments")
        rows = []
        for r in ccon.execute("SELECT id, full FROM record WHERE type = 'fact' ORDER BY rowid"):
            f = json.loads(r["full"])
            if not any(f["key"].startswith(k) for k in keys) or f["key"].endswith((".source", ".note", "conflict_note", ".as_of")):
                continue
            where = ", ".join(sorted({"%s p.%s" % (s.get("doc"), s.get("page")) for s in f.get("sources", []) if s.get("doc")}))
            rows.append((r["id"], "= %s%s" % (json.dumps(f["value"], ensure_ascii=False), " (%s)" % where if where else "")))
        items("Facts recorded (intake/facts.json) with the documents they come from", rows)
        items("Client's answers to judgment points", cards(ccon, "SELECT id, card FROM record WHERE type = 'answer' ORDER BY rowid"))
    hp = cd / "intake" / "handoff.md"
    if reading and hp.exists():
        text("Handoff (intake/handoff.md)", hp.read_text(encoding="utf-8").replace("\n## ", "\n#### ").replace("\n# ", "\n#### "))
    if reading and run:
        pcon, e = reader.products(case_id, run)
        if pcon:
            try:
                import sections as secm
                import impact
                secm.CASES = impact.CASES = CASES
                last = impact.baseline(case_id)
                secm.build_frame(case_id, run, (last or {}).get("run_id"))
                frame = (cd / "report" / run / "frame" / "frame.md").read_text(encoding="utf-8")
                frame = frame.split("\n", 2)[2].replace("## Tables (markers)", "#### Tables").replace("## Structure names", "#### Structure names")
                frame = re.sub(r"(?s)### \{\{block:(assumptions_table|gaps_list)\}\}.*?(?=### \{\{block:|\Z)", "", frame)   # the sections below carry them
                frame = frame.replace("### {{block:", "##### ").replace("}}", "")
                text("Structure names and the program's tables (report/%s/frame/frame.md)" % run, frame)
                names = json.loads((cd / "report" / run / "frame" / "names.json").read_text(encoding="utf-8"))
                items("Structure ids by name", [("%s:structure:%s" % (run, cid), "%s: %s" % (n["name"], n["signature"])) for cid, n in names.items()])
            except Exception as ex:                          # noqa: BLE001  (the pack still carries the rest)
                text("Structure names", "not available: %s" % ex)
            brief = pcon.execute("SELECT full FROM record WHERE type = 'brief'").fetchone()
            best = json.loads(brief["full"]).get("best", {}).get("cand_id") if brief else None
            if best:
                fav = pcon.execute("SELECT full FROM record WHERE type = 'structure' AND cand = ?", (best,)).fetchone()
                bs = (json.loads(fav["full"]).get("brief") or {}) if fav else {}
                fb = (bs.get("all_favourable") or {}).get("branch_id")
                ub = (bs.get("all_unfavourable") or {}).get("branch_id")
                key = [b for b in (fb, ub) if b]
                items("The first structure (%s): the structure, its all-favourable and all-unfavourable branches and their deltas "
                      "(list('branches', {'cand': '%s'}) for the others)" % (best, best),
                      cards(pcon, "SELECT id, card FROM record WHERE (type = 'structure' AND cand = ?) OR (type IN ('branch', 'delta') AND branch IN (%s)) "
                                  "ORDER BY type DESC, rowid" % ",".join("?" * len(key)), [best] + key))
                cells = cards(pcon, "SELECT id, card FROM record WHERE type = 'cell' AND branch = ? ORDER BY rowid", (fb,)) if fb else []
                cells = [(i, c) for i, c in cells if loads(c).get("status") != "absent" and (loads(c).get("rules") or loads(c).get("needs"))]
                items("Cells of its all-favourable branch %s: rules and provisions applied" % fb, cells)
                cites = []
                for _, c in cells:
                    for x in loads(c).get("cite_ids") or []:
                        if x not in cites:
                            cites.append(x)
                law = []
                for cite in cites[:8]:                    # the basis records below hold them all
                    meta = reader.law_meta([cite]).get(cite)
                    if meta:
                        law.append((cite, "%s %s: %s" % (meta["title"], meta["label"], reader.unit_text(None, cite, 420).replace("\n", " "))))
                items("Provisions the first structure relies on (verbatim, first part; get(id) for all of it)", law)
            named = [best] if best else []
            for r in pcon.execute("SELECT full FROM record WHERE type = 'scenario'"):
                sc = json.loads(r["full"])
                for c in (sc.get("first"), sc.get("second")):
                    if c and c not in named:
                        named.append(c)
            rows = []
            for c in named[:8]:
                b = pcon.execute("SELECT id, full FROM record WHERE type = 'basis' AND cand = ?", (c,)).fetchone()
                if b:
                    prov = json.loads(b["full"])
                    rows.append((b["id"], "%d provisions, those setting the tax first: %s" % (len(prov), ", ".join(
                        "%s %s" % (x.get("title", "")[:28], x.get("label", x["cite_id"])) for x in prov[:6]))))
            items("Legal basis of each structure the report discusses: get(id) returns every provision it rests on, verbatim, with the rules "
                  "that apply it; the rule layer has already matched them to the products, so cite them by their cite_id", rows)
            items("Earlier dividends", cards(pcon, "SELECT id, card FROM record WHERE type = 'past_payment'"))
            pts = []
            for r in pcon.execute("SELECT id, full FROM record WHERE type = 'point' ORDER BY rowid"):
                jp = json.loads(r["full"])
                f, u = jp.get("first_if_favourable") or {}, jp.get("first_if_unfavourable") or {}
                pts.append((r["id"], json.dumps({"changes_rank": jp.get("changes_rank"), "at_stake": jp.get("value_at_stake"),
                                                 "first_if_favourable": [f.get("cand_id"), f.get("amount")], "first_if_unfavourable": [u.get("cand_id"), u.get("amount")],
                                                 "question": (jp.get("question") or "")[:140]}, ensure_ascii=False)))
            items("Judgment points: first structure and its tax under either answer (get(id) for the full question)", pts)
            ois = []
            for r in pcon.execute("SELECT id, full FROM record WHERE type = 'open_item' ORDER BY rowid"):
                it = json.loads(r["full"])
                if it.get("changes_rank") or it.get("client_supplies"):
                    ois.append((r["id"], json.dumps({"changes_rank": it.get("changes_rank"), "client_supplies": it.get("client_supplies"),
                                                     "question": (it.get("question") or "")[:160]}, ensure_ascii=False)))
            items("Open items that change the ranking or that the client can supply", ois)
            items("Decision gaps", cards(pcon, "SELECT id, card FROM record WHERE type = 'gap' ORDER BY rowid"))
            if best:
                items("Requirements of the first structure", cards(pcon, "SELECT id, card FROM record WHERE type = 'requirement' AND cand = ? ORDER BY rowid", (best,)))
                items("Transfers of the first structure", cards(pcon, "SELECT id, card FROM record WHERE type = 'transfer' AND cand = ? ORDER BY rowid", (best,)))
            items("Difference from the previous run", cards(pcon, "SELECT id, card FROM record WHERE type = 'diff'"))
            items("Scenarios (who comes first and second; get(id) for the amounts)",
                  [(i, json.dumps({k: loads(c).get(k) for k in ("against", "first", "second")}, ensure_ascii=False))
                   for i, c in cards(pcon, "SELECT id, card FROM record WHERE type = 'scenario' ORDER BY rowid")])
    if node in ("review_draft", "review_final") and run:
        cc = reader.cite_check(case_id, run, "draft" if node == "review_draft" else "polished")
        if "error" not in cc:
            sections.insert(1, ("Provenance check of the %s (cite_check)" % cc["target"],
                                "unresolved refs: %s\n\nfigures no source row states: %s" % (json.dumps(cc["unresolved_refs"], ensure_ascii=False),
                                                                                           json.dumps(cc["uncovered_figures"], ensure_ascii=False)), []))
    if node in ("review_intake", "front") and ccon:
        items("Sources recorded (intake/sources.json)", cards(ccon, "SELECT id, card FROM record WHERE type = 'source' ORDER BY rowid"))
        items("Documents and how they were read", cards(ccon, "SELECT id, card FROM record WHERE type = 'document' ORDER BY id"))
    head = ("# Prefetch pack: %s, case %s, round %s, run %s\n\nWritten by the program. Each item starts with its id; cite that id as the "
            "ref of the sources table. For more, use tax-read: search (several questions at once), list(kind), get(id), expand(id). "
            "Paths are relative to cases/%s.\n" % (node, case_id, rnd, run or "-", case_id))
    out, ids, left = [head], [], []
    used = len(head)
    for title, body, sids in sections:
        block = "\n## %s\n\n%s\n" % (title, body)
        if used + len(block) > LIMIT:
            left.append(title)
            continue
        out.append(block)
        ids += sids
        used += len(block)
    if left:
        out.append("\n## Left out (the pack is capped at %d characters; fetch these with tax-read)\n\n%s\n" % (LIMIT, "\n".join("- " + t for t in left)))
    path = out_dir / ("%s.md" % node)
    path.write_text("".join(out), encoding="utf-8")
    return path, ids


def polish_pack(case_id, rnd, run, out_dir):
    """What polish otherwise digs out of the system's code: the tables the draft's markers stand for, what report_check tests,
    and the diagram format (polish_agent_spec.en.md §6)."""
    import case_server as cs
    cd = CASES / case_id
    rd = cd / "report" / run
    draft = (rd / "briefing.md").read_text(encoding="utf-8") if (rd / "briefing.md").exists() else ""
    rel = lambda p: p.relative_to(cd).as_posix()                                        # noqa: E731
    files = [rel(p) for p in (rd / "briefing.md", rd / "briefing.sources.json", rd / "review.md", rd / "review_legal.md", cd / "intake" / "handoff.md") if p.exists()]
    out = ["# Prefetch pack: polish, case %s, round %s, run %s\n\nWritten by the program. Paths are relative to cases/%s. You need nothing "
           "else from the system: do not read its code or specifications.\n" % (case_id, rnd, run, case_id),
           "## Files\n\n" + "\n".join("- " + f for f in files) + "\n"]
    marks = list(dict.fromkeys(re.findall(r"\{\{block:([a-z_]+)\}\}", draft)))
    fb = rd / "frame" / "blocks"
    if marks:
        out.append("## Program tables the draft's markers stand for\n\nA line {{block:<name>}} in the draft stands for the table below, which the "
                   "program generated from the products. In the polished report write the table itself in place of the marker (you may cut a "
                   "table that the body already states in prose, or drop a column; do not change a cell). report_check counts the figures of "
                   "these tables as figures of the draft.\n")
        for name in marks:
            p = fb / ("%s.md" % name)
            out.append("### %s\n\n%s\n" % (name, p.read_text(encoding="utf-8").strip() if p.exists() else "(no such block in frame/blocks)"))
    out.append("## What report_check(target=polished) tests\n\n" + "\n".join("- " + x for x in (
        "every number of the polished report is a number of the draft (thousands separators and units ignored): number_drift must be empty",
        "every sources row keeps the draft's claim, kind and ref (claims_changed empty); a row may be dropped with its sentence (sources_cut lists it)",
        "every row's where fragment is verbatim in the polished body (where_unlocated empty): when you reword a sentence, update the fragment",
        "parts 1 to 7 and Appendices A and B present, a Date line, no internal-reference line and no system identifiers in the body",
        "the body before the appendices runs to %d to %d PDF pages (render_pdf first; report_check reads briefing.pdf)" % (cs.BODY_FLOOR, cs.BODY_LIMIT),
        "no sentence of the body prose over %d words; tables and the diagram block do not count" % cs.LONG_SENTENCE,
        "no spoken lead-ins in bold (In one sentence, Why, How much it saves, ...) and none of the optimizer's words: per 100, modelled, variant, "
        "judgment world, ranked N-th, the library",
        "it lists numbers_omitted and sources_cut for the final review: cutting is allowed, but nothing the polish spec says must stay")) + "\n")
    tpl = HERE.parent / "templates" / "flowchart.example.json"
    if tpl.exists():
        out.append("## The diagram\n\nThe restructuring diagram is a fenced block ```flow holding JSON of this shape (render_pdf draws it; keep it "
                   "to the facts of the report):\n\n```json\n%s\n```\n" % tpl.read_text(encoding="utf-8").strip())
    path = out_dir / "polish.md"
    path.write_text("\n".join(out), encoding="utf-8")
    return path, []


def inventory(reader, case_id):
    """The one-paragraph file list the orchestrator puts into a task."""
    m = reader.map(case_id)
    return "; ".join("%s: %s" % (f["path"], ", ".join(x["name"] for x in f["files"][:30])) for f in m.get("folders", []))
