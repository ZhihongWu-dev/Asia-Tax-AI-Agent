#!/usr/bin/env python
"""The coverage matrix, the source list and the watch list of the library (database_spec.en.md §4.6), from the csv
files alone (no slicing, so the verbatim-quote errors of the build are not in it; run build.py for those).

  python database/tools/coverage.py

Writes database/coverage/:
  matrix.csv      one row per jurisdiction of scope.csv: status, priority, the cells accounted for, the treaty list, the
                  pairs, exit tax and CFC in our words with their sources, and the supervisor's notes beside them (leads.csv);
  pairs.csv       one row per pair of active jurisdictions: the treaty row, the parts held, what each list says, what is due;
  sources.csv     every document with its official address, other address, hash, dates and part: the list to check updates by;
  watch.csv       the documents watch.py re-fetches: each treaty list and every treaty signed but not yet in force;
  overview.xlsx   the three sheets of the supervisor's Overview.xlsx (DTA, National Tax Files, Exit Tax) with our values.
"""
import io
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build  # noqa: E402

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

FETCHED = re.compile(r"(?:downloaded|registered|fetched)[^;]*?(\d{4}-\d{2}-\d{2})")


def fetched(d):
    m = FETCHED.search(d.get("note") or "")
    return m.group(1) if m else ""


def summary(jur, slot, params, decisions):
    """'company: name=value unit [cite]; individual: none [absence id]' for one slot of one jurisdiction."""
    out = []
    for subj in ("company", "individual"):
        ps = [p for p in params if p["scope"] == jur and p["slot"] == slot and p["subject"] in (subj, "all")]
        ab = [d for d in decisions if d.get("jur") == jur and d.get("slot") == slot and d.get("subject") in (subj, "all")]
        if ps:
            out.append("%s: %s" % (subj, "; ".join("%s=%s%s [%s]" % (p["name"], p["value"][:60], "" if p["unit"] in ("bool", "text") else " " + p["unit"],
                                                                      p["cite_id"]) for p in ps[:6])
                                     + (" (+%d more)" % (len(ps) - 6) if len(ps) > 6 else "")))
        elif ab:
            out.append("%s: none [%s]" % (subj, ab[0]["id"]))
        else:
            out.append("%s: not collected" % subj)
    return " | ".join(out)


def main():
    root = build.ROOT
    t = {name: build.read_csv(root / (name + ".csv")) for name in build.FILLED}
    scope = build.read_csv(root / "scope.csv")
    leads = build.read_csv(root / "leads.csv")
    juris = t["jurisdiction"]
    docs = {d["id"]: d for d in t["doc"]}
    named = build.treaty_lists(t["treaty_list"], t["decision"])
    cat_gaps = build.coverage_categories(t["doc"], t["decision"], juris)
    slot_gaps = build.coverage_slots(t["param"], t["decision"], juris)
    errs, warns = [], []
    pair_gaps = build.pair_gaps(t["treaty"], named, juris, errs, warns)
    out = root / "coverage"
    out.mkdir(exist_ok=True)
    rows_by_pair = {r["pair"]: r for r in t["treaty"]}
    lead = {}
    for r in leads:
        if r["source"].startswith("supervisor"):
            lead.setdefault((r["jur"], r["item"]), r)

    # ---- pairs
    parts = {}
    for d in t["doc"]:
        if d.get("part"):
            parts.setdefault(d["jur"], []).append(d["part"])
    pair_rows = []
    for pair in build.pairs_of([j["code"] for j in juris]):
        a, b = pair.split("-")
        r = rows_by_pair.get(pair, {})
        say = lambda x, y: (named[x][y]["status"] if y in named.get(x, {}) else "not named") if x in named else "list missing"
        pair_rows.append({"pair": pair, "status": r.get("status", "no row"), "doc_id": r.get("doc_id", ""),
                          "parts": ";".join(sorted(parts.get(pair, []))), "in_force_from": r.get("in_force_from", ""),
                          "mli_doc_id": r.get("mli_doc_id", ""), "pending_doc_id": r.get("pending_doc_id", ""),
                          "list_" + "a": "%s: %s" % (a, say(a, b)), "list_b": "%s: %s" % (b, say(b, a)),
                          "due": next((g.split(": ", 1)[1] for g in pair_gaps if g.startswith(pair + ":")), "")})
    build.write_csv(out / "pairs.csv", list(pair_rows[0]) if pair_rows else ["pair"], pair_rows)

    # ---- matrix
    matrix = []
    for s in scope:
        c = s["code"]
        active = s["status"] == "active"
        mine = [p for p in pair_rows if c in p["pair"].split("-")]
        count = lambda st: sum(1 for p in mine if p["status"] == st)
        lst = named.get(c)
        row = dict(s)
        row.update({
            "categories": "%d/%d" % (len(build.COVERED_CATEGORIES) - sum(1 for g in cat_gaps if g.startswith(c + "|")), len(build.COVERED_CATEGORIES)) if active else "",
            "slots": "%d/18" % (18 - sum(1 for g in slot_gaps if g.startswith(c + "|"))) if active else "",
            "treaty_list": ("%d entries" % len(lst) if lst else "no treaty (absence record)") if lst is not None else ("missing" if active else ""),
            "pairs": "in force %d, signed %d, none %d, due %d" % (count("in_force"), count("signed"), count("none"), count("no row")) if active else "",
            "exit": summary(c, "exit", t["param"], t["decision"]) if active else "",
            "cfc": summary(c, "cfc", t["param"], t["decision"]) if active else "",
            "supervisor_exit": lead.get((c, "exit"), {}).get("value", ""),
            "supervisor_cfc": lead.get((c, "cfc"), {}).get("value", ""),
        })
        matrix.append(row)
    build.write_csv(out / "matrix.csv", list(matrix[0]), matrix)

    # ---- sources and watch list
    src = [{"id": d["id"], "jur": d["jur"], "type": d["type"], "part": d.get("part", ""), "category": d.get("category", ""),
            "title": d["title"], "url": d["url"], "alt_url": d.get("alt_url", ""), "sha256": d["sha256"], "lang": d["lang"],
            "authentic": d.get("authentic", ""), "effective_from": d["effective_from"], "effective_to": d["effective_to"],
            "fetched": fetched(d)} for d in t["doc"]]
    build.write_csv(out / "sources.csv", list(src[0]), src)
    watch = {}
    for d in t["doc"]:
        if "page_treaties" in build.split_list(d.get("category")):
            watch[d["id"]] = "treaty list"
    for r in t["treaty"]:
        if r.get("status") == "signed" and r["doc_id"]:
            watch[r["doc_id"]] = "signed, not yet in force (%s)" % r["pair"]
        if r.get("pending_doc_id"):
            watch[r["pending_doc_id"]] = "signed beside the treaty in force, not yet in force (%s)" % r["pair"]
    wrows = [{"id": i, "why": why, "url": docs[i]["url"], "sha256": docs[i]["sha256"], "fetched": fetched(docs[i])}
             for i, why in sorted(watch.items()) if i in docs]
    build.write_csv(out / "watch.csv", ["id", "why", "url", "sha256", "fetched"], wrows)

    # ---- the supervisor's layout
    try:
        import openpyxl
    except ImportError:
        openpyxl = None
    if openpyxl:
        wb = openpyxl.Workbook()
        head = ["Country", "Alpha-2 code", "Alpha-3 code", "Numeric", "Status", "When", "Priority"]
        def base(s, when):
            return [s["name"], s["code"].upper(), s["alpha3"], s["numeric"], s["status"] + (" (%s)" % s["reason"] if s["reason"] else ""), when, s["priority"]]
        latest = lambda c: max((fetched(d) for d in t["doc"] if d["jur"] == c or c in d["jur"].split("-")), default="")
        ws = wb.active
        ws.title = "DTA"
        ws.append(head + ["Source", "Comment"])
        for s, m in zip(scope, matrix):
            lst_docs = sorted({r["doc_id"] for r in named.get(s["code"], {}).values()})
            ws.append(base(s, latest(s["code"])) + ["; ".join(docs[i]["url"] for i in lst_docs if i in docs),
                                                    "; ".join(x for x in (m["treaty_list"], m["pairs"]) if x)])
        ws = wb.create_sheet("National Tax Files")
        ws.append(head + ["What", "Source", "Comment"])
        for s, m in zip(scope, matrix):
            laws = [d for d in t["doc"] if d["jur"] == s["code"] and set(build.split_list(d.get("category"))) & {"1", "2"}]
            ws.append(base(s, latest(s["code"])) + ["; ".join(d["title"] for d in laws), "; ".join(d["url"] for d in laws),
                                                    "categories %s, slots %s" % (m["categories"], m["slots"]) if m["categories"] else ""])
        ws = wb.create_sheet("Exit Tax")
        ws.append(head + ["Comment Exit Tax", "Comment CFC Rules", "Supervisor: exit tax", "Supervisor: CFC rules"])
        for s, m in zip(scope, matrix):
            ws.append(base(s, latest(s["code"])) + [m["exit"], m["cfc"], m["supervisor_exit"], m["supervisor_cfc"]])
        for w in wb.worksheets:
            w.auto_filter.ref = w.dimensions
            w.freeze_panes = "B2"
        wb.save(out / "overview.xlsx")
    print("coverage/: matrix %d rows, pairs %d, sources %d, watch %d%s" % (
        len(matrix), len(pair_rows), len(src), len(wrows), ", overview.xlsx" if openpyxl else " (openpyxl missing: no overview.xlsx)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
