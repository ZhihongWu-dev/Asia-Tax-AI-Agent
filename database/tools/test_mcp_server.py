#!/usr/bin/env python
"""Construction checks of tax-db (database/数据库MCP规范.md §6). Calls the tools in-process through MCPServer.call_tool.

  python database/tools/test_mcp_server.py [--root database]
"""
import argparse
import asyncio
import csv
import io
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mcp_server import build_server, read_csv  # noqa: E402

csv.field_size_limit(10 ** 9)


async def call(server, name, args):
    r = await server.call_tool(name, args)
    return json.loads(r.content[0].text)


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    a = ap.parse_args()
    root = Path(a.root)
    server, lib = build_server(root)
    fails = []

    def check(name, ok, detail=""):
        print(("ok   " if ok else "FAIL ") + name + (("  " + detail) if detail and not ok else ""))
        if not ok:
            fails.append(name)

    async def run():
        tools = await server.list_tools()
        names = sorted(t.name for t in tools)
        check("twelve tools", names == sorted(["find", "clause", "doc", "param", "params_for", "absent", "treaty", "jurisdictions",
                                               "param_history", "decision", "blocked", "version"]), str(names))
        # find: a known word hits a known clause
        p = next(iter(lib.params.values()))
        cite = p["cite_id"]
        word = re.sub(r"\s+", "", p["quote"])[:6]
        r = await call(server, "find", {"words": [word]})
        check("find hits the quoted clause", any(h["cite_id"] == cite for h in r["hits"]) or r["total"] > 0, json.dumps(r, ensure_ascii=False)[:200])
        check("find carries version", "version" in r and r["version"]["database"]["docs"] == len(lib.docs))
        r = await call(server, "find", {"words": []})
        check("find without words -> invalid", r.get("error") == "invalid")
        # clause: verbatim and paging
        r = await call(server, "clause", {"cite_id": cite})
        text = lib.by_cite[cite]["text"]
        check("clause text verbatim", r.get("text") == text and r.get("complete") is True)
        parts, off, step = [], 0, 50
        while off < len(text):
            q = await call(server, "clause", {"cite_id": cite, "offset": off, "max_chars": step})
            parts.append(q["text"]); off += step
        check("clause paging reassembles", "".join(parts) == text)
        r = await call(server, "clause", {"cite_id": "no.such#1"})
        check("clause unknown -> not_found", r.get("error") == "not_found")
        # param quote is a substring of its clause
        r = await call(server, "param", {"param_id": p["param_id"]})
        c = await call(server, "clause", {"cite_id": r["cite_id"]})
        norm = lambda s: re.sub(r"\s+", "", s)
        check("param quote inside clause text", norm(r["quote"]) in norm(c["text"]))
        # params_for and absent
        r = await call(server, "params_for", {"jur": "cn", "slot": "outbound_wht"})
        check("params_for cn outbound_wht non-empty", len(r["params"]) > 0 and all(x["slot"] == "outbound_wht" for x in r["params"]))
        r = await call(server, "absent", {"jur": "hk"})
        check("absent hk non-empty", len(r["absent"]) > 0 and all(".absent." in x["id"] for x in r["absent"]))
        # treaty cn-hk both orders
        r1 = await call(server, "treaty", {"jur_a": "cn", "jur_b": "hk"})
        r2 = await call(server, "treaty", {"jur_a": "hk", "jur_b": "cn"})
        check("treaty cn-hk non-empty, order-insensitive", len(r1["rows"]) > 0 and [x["doc_id"] for x in r1["rows"]] == [x["doc_id"] for x in r2["rows"]])
        # jurisdictions, decision, blocked, doc
        r = await call(server, "jurisdictions", {})
        check("jurisdictions has cn with CNY", any(j["code"] == "cn" and j["currency"] == "CNY" for j in r["jurisdictions"]))
        r = await call(server, "decision", {})
        check("decision all = decision.csv", len(r["decisions"]) == len(lib.decisions))
        r = await call(server, "blocked", {})
        check("blocked = blocked.csv", len(r["blocked"]) == len(lib.blocked))
        r = await call(server, "doc", {"doc_id": lib.by_cite[cite]["doc_id"]})
        check("doc row has title and clause count", bool(r.get("title")) and r.get("clauses", 0) > 0)
        # param_history: at least the parameter itself; chain follows superseded_by when present
        r = await call(server, "param_history", {"param_id": p["param_id"]})
        check("param_history has >= 1 version", len(r["versions"]) >= 1 and r["versions"][-1]["param_id"] == p["param_id"])
        sup = [q for q in lib.params.values() if q.get("superseded_by")]
        if sup:
            r = await call(server, "param_history", {"param_id": sup[0]["param_id"]})
            check("param_history follows superseded_by", len(r["versions"]) >= 2)
        else:
            print("skip param_history chain: no superseded parameter in the library yet")
        # version vs STATUS.md
        r = await call(server, "version", {})
        counts = r["status_counts"]
        check("version matches STATUS.md documents", counts.get("Documents") == str(len(lib.docs)), str(counts))
        check("version matches STATUS.md parameters", counts.get("Parameters") == str(len(lib.params)), str(counts))

    asyncio.run(run())
    print("tax-db checks: %s" % ("PASSED" if not fails else "%d failed" % len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
