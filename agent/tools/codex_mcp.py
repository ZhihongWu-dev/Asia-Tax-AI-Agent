"""Start the existing native stdio MCP implementations with a fixed role and case.

There is no JSON-RPC transport adapter here: the CLI connects directly to the
SDK server. The wrapper adds case binding and an audit trail before dispatch.
"""
import argparse
import json
import os
from pathlib import Path
import runpy
import sys
from datetime import datetime, timezone

from harness import PROJECT, redact
from make_agents import SERVERS


def check_arguments(arguments, case_id):
    def walk(value, key=""):
        if isinstance(value, dict):
            for name, item in value.items():
                walk(item, name)
        elif isinstance(value, list):
            for item in value:
                walk(item, key)
        elif isinstance(value, str):
            text = value.replace("\\", "/")
            if key == "case_id" and text != case_id:
                raise PermissionError("session is bound to case " + case_id)
            if key == "id" and text.startswith("file:") and not text.startswith("file:" + case_id + "/"):
                raise PermissionError("file id belongs to another case")
            if key in ("input", "products", "against", "items", "file_path", "src_path") and text:
                if text.startswith(("/", "..")) or ":" in text or ".." in text.split("/"):
                    raise PermissionError("file arguments must stay inside this case")
                rel = text.removeprefix("cases/")
                if not (rel == case_id or rel.startswith(case_id + "/")):
                    raise PermissionError("file argument belongs to another case")
    walk(arguments)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", required=True, choices=SERVERS)
    ap.add_argument("--case", required=True)
    ap.add_argument("--server", required=True)
    a = ap.parse_args()
    from codex_files import Files, build_server
    Files(a.role, a.case)  # Validate before making any audit directory.
    if a.server not in (*SERVERS[a.role], "tax-files"):
        ap.error("server is not available to this role")
    # MCP processes do not need either provider credential.
    for name in list(os.environ):
        if name.startswith(("OPENAI_", "ANTHROPIC_", "QWEN_")):
            os.environ.pop(name)
    from mcp.server.mcpserver import MCPServer
    original = MCPServer.call_tool

    async def guarded(server, name, arguments, context=None):
        try:
            check_arguments(arguments, a.case)
            if a.server.startswith("tax-read-") and name in ("search", "list"):
                arguments = {**arguments, "filters": {**(arguments.get("filters") or {}), "case_id": a.case}}
            result = await original(server, name, arguments, context)
        except Exception as exc:
            cause = exc
            while cause.__cause__ is not None:
                cause = cause.__cause__
            if not isinstance(cause, (PermissionError, ValueError)):
                raise
            from mcp.types import CallToolResult, TextContent
            result = CallToolResult(content=[TextContent(type="text", text=str(cause))], is_error=True)
        folder = PROJECT / "cases" / a.case / "log" / "codex-tools"
        folder.mkdir(parents=True, exist_ok=True)
        row = {"at": datetime.now(timezone.utc).isoformat(), "role": a.role,
               "server": a.server, "tool": name, "arguments": arguments,
               "is_error": getattr(result, "is_error", False)}
        with (folder / ("%s-%s.jsonl" % (a.role, os.getpid()))).open("a", encoding="utf-8") as f:
            f.write(redact(json.dumps(row, ensure_ascii=False)) + "\n")
        return result

    MCPServer.call_tool = guarded
    if a.server.startswith("tax-read-"):
        import read_core
        original_reader = read_core.Reader

        class BoundReader(original_reader):
            def casefile(self, case_id):
                if case_id != a.case:
                    raise PermissionError("record belongs to another case")
                return super().casefile(case_id)

            def products(self, case_id, run_id):
                if case_id != a.case:
                    raise PermissionError("run belongs to another case")
                return super().products(case_id, run_id)

            def denied(self, rel):
                # Resolve first so traversal and directory links cannot cross cases.
                try:
                    Files(a.role, a.case).path("cases/" + str(rel))
                except (PermissionError, ValueError) as exc:
                    return str(exc)
                return super().denied(rel)

        read_core.Reader = BoundReader
    os.chdir(PROJECT)
    if a.server == "tax-files":
        build_server(a.role, a.case).run(transport="stdio")
    else:
        definition = json.loads((PROJECT / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"][a.server]
        script, *args = definition["args"]
        sys.argv = [str(PROJECT / script), *args]
        sys.path.insert(0, str((PROJECT / script).parent))
        runpy.run_path(str(PROJECT / script), run_name="__main__")


if __name__ == "__main__":
    main()
