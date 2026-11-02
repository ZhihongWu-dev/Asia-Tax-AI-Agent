#!/usr/bin/env python
"""Construction checks of tax-rule (rule/规则层MCP规范.md §6): each tool once, in-process through MCPServer.call_tool,
compared with a direct call of the layer function on the same inputs.

  python rule/tools/test_mcp_server.py [--root rule --db database --cases cases]
"""
import argparse
import asyncio
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import eval as ev  # noqa: E402
from common import read_csv  # noqa: E402
from mcp_server import build_server  # noqa: E402
from query import cells_for_flow  # noqa: E402

TOOLS = ["variables", "predicates", "version", "cells_for_flow", "judgment_points", "requirements", "options", "what_if", "gap",
         "eval_cell", "eval_flow", "eval_transfer", "trace", "rule_tool"]


async def call(server, name, args):
    r = await server.call_tool(name, args)
    return json.loads(r.content[0].text)


def strip(obj):
    if isinstance(obj, dict):
        return {k: v for k, v in obj.items() if k != "version"}
    return obj


def same(a, b):
    return json.loads(json.dumps(a, sort_keys=True)) == json.loads(json.dumps(b, sort_keys=True))


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(HERE.parent))
    ap.add_argument("--db", default=str(HERE.parent.parent / "database"))
    ap.add_argument("--cases", default=str(HERE.parent.parent / "cases"))
    a = ap.parse_args()
    server, st = build_server(a.root, a.db, a.cases)
    fails = []

    def check(name, ok, detail=""):
        print(("ok   " if ok else "FAIL ") + name + (("  " + detail[:300]) if detail and not ok else ""))
        if not ok:
            fails.append(name)

    # inputs from the golden tests
    tests = read_csv(Path(a.root) / "rule_test.csv")
    cap = next(t for t in tests if t["slot_key"] == "cn|company|outbound_wht|hk" and t["answers"])
    facts, answers, date = ev.parse_kv(cap["facts"]), ev.parse_kv(cap["answers"]), cap["date"]
    facts_obj = {k: (True if v == "true" else False if v == "false" else int(v) if v.isdigit() else v) for k, v in facts.items()}
    tr = next(t for t in tests if t["slot_key"] == "cn|company|restructure|*")
    tr_facts = ev.parse_kv(tr["facts"])

    async def run():
        names = sorted(t.name for t in await server.list_tools())
        check("fourteen tools", names == sorted(TOOLS), str(names))

        r = await call(server, "variables", {})
        check("variables = Query.variables", same(r["variables"], st.q.variables()) and "version" in r)
        r = await call(server, "predicates", {})
        check("predicates = Query.predicates", same(r["predicates"], st.q.predicates()))
        r = await call(server, "version", {})
        v = st.q.version()
        check("version carries rule and database stamps", r["version"]["rule"] == v["rule"] and r["version"]["database"] == v["database"]
              and r["version"]["server"])
        r = await call(server, "cells_for_flow", {"payer_jur": "cn", "payee_jur": "hk", "subject": "company"})
        check("cells_for_flow cn hk company non-empty and equal", r["cells"] == cells_for_flow("cn", "hk", "company") and len(r["cells"]) > 0)

        flow = {"payer_jur": "cn", "payee_jur": "hk", "subject": "company"}
        r = await call(server, "judgment_points", {"flow": flow, "date": date, "facts": facts_obj, "answers": {}})
        d = st.q.judgment_points(["cn", "hk", "company"], None, date, facts, {}, "record")
        check("judgment_points (typed facts) = Query.judgment_points (string facts)", same(r["judgment_points"], d))
        check("judgment_points finds the bo predicate", any(j["predicate"] == "bo" for j in r["judgment_points"]), json.dumps(r)[:200])

        r = await call(server, "requirements", {"slot": cap["slot_key"], "date": date})
        check("requirements = Query.requirements", same(strip(r), st.q.requirements(cap["slot_key"], None, None, date)))
        r = await call(server, "requirements", {})
        check("requirements without slot/rule -> invalid", r.get("error") == "invalid")

        r = await call(server, "options", {"payer_jur": "cn", "payee_jur": "hk", "subject": "company", "date": date})
        check("options = Query.options", same(r["options"], st.q.options("cn", "hk", "company", date)))

        r = await call(server, "what_if", {"flow": flow, "date": date, "facts": facts_obj, "answers": answers, "set": {"holding_pct": 1}})
        d = st.q.what_if(["cn", "hk", "company"], None, date, facts, answers, "record", {"holding_pct": "1"}, {})
        check("what_if = Query.what_if", same(strip(r), d))
        check("what_if sees the change", any(c["changed"] for c in r["cells"]))

        r = await call(server, "gap", {"payer_jur": "cn", "payee_jur": "hk", "subject": "company"})
        check("gap = Query.gap", same(strip(r), st.q.gap("cn", "hk", "company")))

        r = await call(server, "eval_cell", {"slot": cap["slot_key"], "date": date, "facts": facts_obj, "answers": answers})
        d = [ev.eval_cell(st.rs, cap["slot_key"], date, facts, answers, "record", assume=[])]
        check("eval_cell = eval.eval_cell", same(r["items"], d))
        check("eval_cell reproduces the golden expectation", str(r["items"][0]["ceiling"]["value"]).startswith(cap["expect"].split()[1]), cap["expect"])

        r = await call(server, "eval_flow", {"payer_jur": "cn", "payee_jur": "hk", "subject": "company", "date": date, "facts": facts_obj, "answers": answers})
        d = ev.eval_flow(st.rs, "cn", "hk", "company", date, facts, answers, "record", assume=[])
        check("eval_flow = eval.eval_flow", same(r["items"], d))
        r_missing = await call(server, "eval_flow", {"payer_jur": "cn", "payee_jur": "hk", "subject": "company", "date": ""})
        check("eval_flow without date -> invalid", r_missing.get("error") == "invalid")
        r_mode = await call(server, "eval_flow", {"payer_jur": "cn", "payee_jur": "hk", "subject": "company", "date": date, "mode": "guess"})
        check("eval_flow bad mode -> invalid", r_mode.get("error") == "invalid")
        r_bad = await call(server, "eval_cell", {"slot": "not-a-slot", "date": date})
        check("eval_cell malformed slot -> invalid", r_bad.get("error") == "invalid", json.dumps(r_bad)[:200])
        r_abs = await call(server, "eval_cell", {"slot": "xx|company|outbound_wht|hk", "date": date})
        check("eval_cell unknown jurisdiction -> the layer's own 'absent' answer, not a server error",
              r_abs.get("items", [{}])[0].get("status") == "absent", json.dumps(r_abs)[:200])

        r2 = await call(server, "eval_transfer", {"target_jur": "cn", "home_jur": "hk", "subject": "company", "date": tr["date"], "facts": tr_facts})
        d = ev.eval_transfer(st.rs, "cn", "hk", "company", tr["date"], tr_facts, {}, "record", assume=[])
        check("eval_transfer = eval.eval_transfer", same(r2["items"], d) and len(r2["items"]) > 0)

        items = r["items"]
        t = await call(server, "trace", {"items": items})
        check("trace returns one trace per item", len(t["traces"]) == len(items) and all("slot_key" in x for x in t["traces"]))
        t2 = await call(server, "trace", {"flow": flow, "date": date, "facts": facts_obj, "answers": answers})
        check("trace from flow = trace from items", same(t2["traces"], t["traces"]))
        t3 = await call(server, "trace", {"items": "no/such/file.json"})
        check("trace missing file -> not_found", t3.get("error") == "not_found")
        t4 = await call(server, "trace", {"items": "../rule/rule.csv"})
        check("trace path outside cases -> invalid", t4.get("error") == "invalid")

        r = await call(server, "rule_tool", {"slot": cap["slot_key"], "date": date, "brief": True})
        rows = st.tool.rule_rows(cap["slot_key"], date, None, None, None)
        d = {"found": len(rows), "rules": [st.tool.expand(x, True) for x in rows], "reference_params": st.tool.reference_params(cap["slot_key"])}
        check("rule_tool slot = RuleTool", same(strip(r), d) and r["found"] > 0)
        r = await call(server, "rule_tool", {"variable": "holding_pct"})
        check("rule_tool variable row present", r.get("variable") and r["found"] > 0)
        r = await call(server, "rule_tool", {})
        check("rule_tool without selector -> invalid", r.get("error") == "invalid")

    asyncio.run(run())
    print("tax-rule checks: %s" % ("PASSED" if not fails else "%d failed" % len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
