#!/usr/bin/env python
"""Construction checks of tax-opt (optimization/优化层MCP规范.md §6). Calls the tools in-process through MCPServer.call_tool.

  python optimization/tools/test_mcp_server.py [--work <temp products root>]

Runs the example case into a temporary products root, so it takes a minute. No network: fx is only tested for its
`invalid` answer without a date.
"""
import argparse
import asyncio
import io
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from mcp_server import build_server  # noqa: E402
import optimize as op  # noqa: E402

PROJECT = HERE.parents[1]
DEFAULT_WORK = Path(r"C:/Users/L8770/AppData/Local/Temp/claude/c--Coding-Projects-TUM-project-study-self/7d2d869a-7976-44b2-8fc2-389dd64ca44a/scratchpad/optmcp")


async def call(server, name, args):
    r = await server.call_tool(name, args)
    return json.loads(r.content[0].text)


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default=str(DEFAULT_WORK))
    a = ap.parse_args()
    work = Path(a.work)
    if work.exists():
        shutil.rmtree(work)
    (work / "CASE-T" / "intake").mkdir(parents=True)
    shutil.copy(PROJECT / "optimization" / "examples" / "case001.json", work / "CASE-T" / "intake" / "facts.json")
    bad = json.loads((PROJECT / "optimization" / "examples" / "case001.json").read_text(encoding="utf-8"))
    bad.pop("payer")
    (work / "CASE-T" / "intake" / "bad.json").write_text(json.dumps(bad), encoding="utf-8")

    front, _ = build_server(PROJECT / "optimization", PROJECT / "rule", PROJECT / "database", work, "front")
    reader, _ = build_server(PROJECT / "optimization", PROJECT / "rule", PROJECT / "database", work, "reader")
    fails = []

    def check(name, ok, detail=""):
        print(("ok   " if ok else "FAIL ") + name + (("  " + str(detail)[:300]) if detail and not ok else ""))
        if not ok:
            fails.append(name)

    async def go():
        names_f = sorted(t.name for t in await front.list_tools())
        names_r = sorted(t.name for t in await reader.list_tools())
        check("front has run and diff", "run" in names_f and "diff" in names_f, names_f)
        check("reader lacks run and diff", "run" not in names_r and "diff" not in names_r, names_r)
        check("both share the readers", set(names_f) - {"run", "diff"} == set(names_r), names_r)
        # validate_input
        r = await call(reader, "validate_input", {"input": "CASE-T/intake/facts.json"})
        check("validate_input summary", r.get("payer") == "cn" and r.get("destinations") and "version" in r, r)
        r = await call(reader, "validate_input", {"input": "CASE-T/intake/bad.json"})
        check("validate_input missing payer -> invalid", r.get("error") == "invalid", r)
        r = await call(reader, "validate_input", {"input": "../case001.json"})
        check("path outside root -> forbidden", r.get("error") == "forbidden", r)
        # run
        r = await call(front, "run", {"case_id": "CASE-T", "input": "CASE-T/intake/facts.json"})
        run_id = r.get("run_id", "")
        check("run returns run_id of the form YYYYMMDD-8hex", bool(re.fullmatch(r"\d{8}-[0-9a-f]{8}", run_id)), r)
        products = "CASE-T/intake/products/%s" % run_id
        check("run wrote the products directory", (work / products / "ranking.json").exists(), products)
        check("run summary has top ranking and open-item count", len(r.get("ranking_top", [])) >= 1 and "open_items_changing_rank" in r, r)
        r2 = await call(front, "run", {"case_id": "CASE-T", "input": "CASE-T/intake/facts.json"})
        check("second run -> conflict", r2.get("error") == "conflict", r2)
        # slices vs whole files
        whole_rank = op.jload(work / products / "ranking.json")
        whole_deltas = op.jload(work / products / "deltas.json")["deltas"]
        whole_tax = op.jload(work / products / "tax.json")["taxes"]
        r = await call(reader, "ranking", {"products": products})
        check("ranking slice equals file", r.get("ranking") == whole_rank["ranking"] and r.get("key") == whole_rank["key"])
        top = whole_rank["ranking"][0]
        r = await call(reader, "deltas", {"products": products, "branch_id": top["branch_id"]})
        check("deltas slice by branch equals file item", r.get("deltas") == [d for d in whole_deltas if d["branch_id"] == top["branch_id"]])
        r = await call(reader, "deltas", {"products": products, "cand_id": top["cand_id"]})
        check("deltas slice by cand equals file items", r.get("deltas") == [d for d in whole_deltas if d["cand_id"] == top["cand_id"]])
        r = await call(reader, "tax", {"products": products, "branch_id": top["branch_id"]})
        check("tax slice equals file item", r.get("taxes") == [t for t in whole_tax if t["branch_id"] == top["branch_id"]])
        r = await call(reader, "tax", {"products": products, "branch_id": "zz.b9"})
        check("tax unknown branch -> not_found", r.get("error") == "not_found")
        r = await call(reader, "open_items", {"products": products, "changes_rank": True})
        check("open_items filter", all(x["changes_rank"] for x in r.get("open_items", [])) and "score_key" in r, r)
        r = await call(reader, "paths", {"products": products, "cand_id": "c0"})
        check("paths c0 is as_is with dominated_by key", r.get("candidates") and r["candidates"][0]["as_is"] is True and "dominated_by" in r["candidates"][0], r)
        r = await call(reader, "requirements", {"products": products, "cand_id": top["cand_id"]})
        check("requirements of the top candidate", r.get("cand_id") == top["cand_id"] and "requirements" in r, r)
        r = await call(reader, "hops", {"products": products, "cand_id": top["branch_id"]})
        check("hops file by branch id", "data" in r, r)
        r = await call(reader, "transfers", {"products": products, "cand_id": top["cand_id"]})
        check("transfers file by cand id", "data" in r or r.get("error") == "not_found", r)
        r = await call(reader, "version", {"products": products})
        check("version of products", r.get("version_json", {}).get("inputs_sha256") and r["version"]["products"]["inputs_sha256"], r)
        r = await call(reader, "version", {})
        check("layer version without products", "optimization" in r.get("version", {}) and r["version"]["optimization"]["rule"], r)
        # evaluate: as-is path plus one node, from the reader process
        c0 = op.jload(work / products / "paths.json")["candidates"][0]
        inp = op.jload(work / products / "input.json")
        dest = "%s:%s" % tuple(inp["destinations"][0])
        path = ";".join(c0["path"] + [dest])
        r = await call(reader, "evaluate", {"products": products, "path": path})
        check("evaluate adds x-1", r.get("cand", {}).get("cand_id") == "x-1" and r.get("taxes"), r)
        after = op.jload(work / products / "ranking.json")["ranking"]
        ranked = lambda rows: [x for x in rows if x.get("rank")]
        check("ranking unchanged after evaluate (x- rows listed but unranked)",
              ranked(after) == ranked(whole_rank["ranking"]) and all(not x.get("rank") for x in after if x["cand_id"].startswith("x-"))
              and any(x["cand_id"].startswith("x-") for x in after), [(x["branch_id"], x.get("rank")) for x in after if x["cand_id"].startswith("x-")][:3])
        r = await call(reader, "ranking", {"products": products})
        check("ranking tool after evaluate matches file", r.get("ranking") == after)
        r = await call(reader, "evaluate", {"products": products, "path": "cn:company"})
        check("evaluate with one node -> invalid", r.get("error") == "invalid")
        # product_check, fx, forbidden / not_found
        r = await call(reader, "product_check", {"products": products})
        check("product_check passes", r.get("passed") is True, r.get("failures"))
        r = await call(reader, "fx", {"base": "CNY"})
        check("fx without date -> invalid", r.get("error") == "invalid")
        r = await call(reader, "ranking", {"products": "../" + products})
        check("ranking outside root -> forbidden", r.get("error") == "forbidden", r)
        r = await call(reader, "ranking", {"products": "CASE-T/intake"})
        check("ranking on a non-products dir -> not_found", r.get("error") == "not_found", r)
        r = await call(front, "diff", {"products": products, "against": products})
        check("diff of a run against itself is empty", r.get("rank_moves") == [] and r.get("interval_changes") == [] and (work / products / "diff.json").exists(), r)

    asyncio.run(go())
    print("tax-opt checks: %s" % ("PASSED" if not fails else "%d failed" % len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
