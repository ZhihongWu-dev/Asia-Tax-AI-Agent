#!/usr/bin/env python
"""Development stand-in for the MCP transport: call one tool of one server in-process and print the JSON answer.

  python agent/tools/mcp_call.py <server> <tool> '<json arguments>'
  python agent/tools/mcp_call.py <server> list

Servers: tax-db, tax-rule, tax-opt-front, tax-opt, tax-case-front, tax-case-analysis, tax-case-polish, tax-case-review. Same code paths as
the MCP servers (build_server + call_tool), so an answer here is what the host would receive. Used when a session was
started before .mcp.json existed or for scripted checks; the agents' normal path is the MCP host. Arguments may also be
given as a path to a JSON file prefixed with @ (e.g. @args.json) to avoid shell quoting.
"""
import asyncio
import io
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
PY = str(PROJECT)


def build(server):
    if server == "tax-db":
        sys.path.insert(0, str(PROJECT / "database" / "tools"))
        import mcp_server as m
        return m.build_server(PROJECT / "database")[0]
    if server == "tax-rule":
        sys.path.insert(0, str(PROJECT / "rule" / "tools"))
        import mcp_server as m
        return m.build_server(PROJECT / "rule", PROJECT / "database", PROJECT / "cases")[0]
    if server in ("tax-opt", "tax-opt-front"):
        sys.path.insert(0, str(PROJECT / "optimization" / "tools"))
        import mcp_server as m
        return m.build_server(PROJECT / "optimization", PROJECT / "rule", PROJECT / "database", PROJECT / "cases",
                              "front" if server == "tax-opt-front" else "reader")[0]
    if server.startswith("tax-case-"):
        sys.path.insert(0, str(PROJECT / "agent" / "tools"))
        import case_server as m
        return m.build_server(PROJECT / "cases", server[len("tax-case-"):])[0]
    raise SystemExit("unknown server %s" % server)


async def run(server, tool, args):
    s = build(server)
    if tool == "list":
        return [{"name": t.name, "params": list(t.input_schema.get("properties", {}))} for t in await s.list_tools()]
    r = await s.call_tool(tool, args)
    try:
        return json.loads(r.content[0].text)
    except Exception:  # noqa: BLE001
        return {"raw": [c.text for c in r.content]}


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    server, tool = sys.argv[1], sys.argv[2]
    raw = sys.argv[3] if len(sys.argv) > 3 else "{}"
    if raw.startswith("@"):
        raw = Path(raw[1:]).read_text(encoding="utf-8")
    args = json.loads(raw) if raw.strip() else {}
    out = asyncio.run(run(server, tool, args))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 1 if isinstance(out, dict) and out.get("error") else 0


if __name__ == "__main__":
    sys.exit(main())
