#!/usr/bin/env python
"""PostToolUse hook: one line per tool call into cases/<case_id>/log/calls.jsonl (agent/case_mcp_spec.en.md §5).

Reads the hook's JSON from stdin, infers the case from any `cases/<case_id>/` path or a `case_id` argument in tool_input,
infers the agent from the tool name prefix `mcp__tax-case-<agent>__` or the hook's agent field, and appends
{time, session_id, agent, tool, input_summary}. Logs only calls made by the three case agents or touching a case; a plain development session writes nothing.
Never fails: any problem is swallowed and the exit code is 0.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

KEEP = ("case_id", "run_id", "name", "book", "which", "path", "file_path", "pattern", "glob", "products", "against", "input",
        "cand_id", "branch_id", "cite_id", "param_id", "doc_id", "slot", "rule", "variable", "predicate", "payer_jur",
        "payee_jur", "target_jur", "home_jur", "subject", "date", "mode", "words", "jur", "jur_a", "jur_b", "url", "speaker",
        "layer", "offset", "max_chars", "changes_rank", "src_path")
CASE_RE = re.compile(r"cases[\\/]+([A-Za-z0-9][A-Za-z0-9_.-]{0,63})[\\/]")


def main():
    try:
        raw = sys.stdin.read()
        d = json.loads(raw) if raw.strip() else {}
        tool = d.get("tool_name", "")
        inp = d.get("tool_input") or {}
        cwd = Path(d.get("cwd") or os.getcwd())
        case_id = inp.get("case_id") if isinstance(inp, dict) else None
        if not case_id:
            m = CASE_RE.search(json.dumps(inp, ensure_ascii=False))
            case_id = m.group(1) if m else None
        agent = None
        m = re.match(r"mcp__tax-case-(front|analysis|polish|review)__", tool)
        if m:
            agent = m.group(1)
        for k in ("agent_name", "agent_type", "subagent_type", "agent"):
            if not agent and d.get(k):
                agent = str(d[k])
        agent = agent or os.environ.get("CLAUDE_AGENT_NAME") or "unknown"
        if agent not in ("front", "analysis", "polish", "review") and not case_id:
            return 0                                   # a development session outside any case: nothing to log
        summary = {}
        if isinstance(inp, dict):
            for k, v in inp.items():
                if k in KEEP:
                    summary[k] = v if not isinstance(v, str) or len(v) <= 200 else v[:200] + "…"
                else:
                    summary.setdefault("_other_keys", []).append(k)
        line = {"time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"), "session_id": d.get("session_id", ""),
                "agent": agent, "tool": tool, "input_summary": summary}
        root = cwd / "cases"
        target = (root / case_id / "log" / "calls.jsonl") if case_id else (root / "_log" / "calls.jsonl")
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
