#!/usr/bin/env python
"""Codex PreToolUse / PostToolUse hook (2026-11-17): the guard and the tool-call log of the Claude path, for the Codex path.

codex_adapter.prepare writes it into each call's config.toml with the call's role and case, because Codex's hook input does
not say which agent is calling.
  pre:  denies the built-in shell and patch tools (the sandbox is read-only and shell_tool is off; this names the reason),
        and a tax-files call on a path the role may not read (codex_files.Files, the same check the server makes).
  post: one line per call into cases/<case_id>/log/calls.jsonl through log_hook.
Never fails: any problem lets the call through (pre) or skips the line (post), with exit code 0.
"""
import argparse
import io
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(HERE))

BUILTIN = re.compile(r"(?i)^(bash|shell|local_shell|exec_command|unified_exec|write_stdin|apply_patch)$")
FILES = re.compile(r"^mcp__tax-files__(read_file|list_files|search|read_image)$")


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}, ensure_ascii=False))
    return 0


def pre(a, d):
    tool = d.get("tool_name", "")
    if BUILTIN.match(tool):
        return deny("%s works through its MCP tools only; read files with tax-files and write with tax-case-%s" % (a.role, a.role))
    inp = d.get("tool_input") or {}
    raw = inp.get("path") if isinstance(inp, dict) else None
    if FILES.match(tool) and raw:
        from codex_files import Files
        try:
            Files(a.role, a.case).path(raw)
        except (PermissionError, ValueError) as e:
            return deny(str(e) or "this path is not the %s agent's to read" % a.role)
    return 0


def post(a, d):
    import log_hook
    inp = d.get("tool_input")
    inp = dict(inp) if isinstance(inp, dict) else {}
    inp.setdefault("case_id", a.case)
    d.update(tool_input=inp, agent=a.role, cwd=str(PROJECT))     # Codex runs in the call's runtime folder, not the project
    sys.stdin = io.StringIO(json.dumps(d, ensure_ascii=False))
    return log_hook.main()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--role", required=True)
    p.add_argument("--case", required=True)
    p.add_argument("--event", choices=("pre", "post"), required=True)
    a = p.parse_args()
    try:
        d = json.loads(sys.stdin.read() or "{}")
        return pre(a, d) if a.event == "pre" else post(a, d)
    except Exception:  # noqa: BLE001
        return 0


if __name__ == "__main__":
    sys.exit(main())
