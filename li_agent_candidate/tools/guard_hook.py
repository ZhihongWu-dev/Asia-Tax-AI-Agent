#!/usr/bin/env python
"""PreToolUse hook: the read-side isolation of the four case agents (agent/case_mcp_spec.en.md §3, §6).

Only acts when the hook input carries agent_type front / analysis / polish / review (i.e. the call happens inside one of
the four agents' `claude --agent` sessions). Denies, with a reason:
  - any Edit / Write under cases/ (writes go through the tax-case server);
  - Read / Grep / Glob of another agent's notes or bugs, of one's own notes of an earlier round, of the call log
    (review only after its review.md exists), and, for analysis, of an earlier run's report/ or products/;
  - Grep / Glob without a path, or with a path at or above cases/ (it would sweep other agents' notes).
Anything else passes silently (exit 0, no output). Never raises.
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import access  # noqa: E402

AGENTS = ("front", "analysis", "polish", "review")
WRITE_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
READ_TOOLS = ("Read", "Grep", "Glob")


def deny(reason):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": reason}}, ensure_ascii=False))
    return 0


def norm(p):
    return str(p).replace("\\", "/")


def main():
    try:
        d = json.loads(sys.stdin.read() or "{}")
        agent = str(d.get("agent_type") or os.environ.get("CLAUDE_AGENT_NAME") or "")
        if agent not in AGENTS:
            return 0
        tool = d.get("tool_name", "")
        inp = d.get("tool_input") or {}
        cwd = Path(d.get("cwd") or os.getcwd()).resolve()
        cases_root = (cwd / "cases").resolve()
        raw = inp.get("file_path") or inp.get("path") or inp.get("notebook_path") or ""
        target = Path(raw) if raw else None
        if target is not None and not target.is_absolute():
            target = cwd / target
        rel = None
        if target is not None:
            try:
                rel = norm(target.resolve().relative_to(cases_root))
            except ValueError:
                rel = None
        if tool in WRITE_TOOLS:
            if rel is not None:
                return deny("%s may not write under cases/ directly; use the tax-case-%s tools" % (agent, agent))
            return 0
        if tool not in READ_TOOLS:
            return 0
        if agent == "polish" and tool == "Read" and str(raw).lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
            return deny("polish works from the render_pdf layout report; its model cannot take images or PDFs")
        if tool in ("Grep", "Glob"):
            if target is None:
                return deny("give a path inside the case (cases/<case_id>/...) so the search does not sweep other agents' notes")
            try:
                target.resolve().relative_to(cases_root)
                inside = True
            except ValueError:
                inside = False
            if inside and (rel in ("", ".") or "/" not in rel):
                return deny("search inside one sub-folder of the case, not the whole case or the cases root")
            if not inside:
                try:
                    cases_root.relative_to(target.resolve())
                    return deny("search inside one sub-folder of the case, not a folder that contains cases/")
                except ValueError:
                    return 0
        if rel is None:
            return 0
        reason = access.denied(agent, rel, cases_root)
        return deny(reason) if reason else 0
    except Exception:  # noqa: BLE001
        return 0


if __name__ == "__main__":
    sys.exit(main())
