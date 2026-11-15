"""Isolated CLI entry point; shares the existing graph, routing and mechanical gates.

  python agent/tools/orchestrate_codex.py run CASE-CODEX-001 --harness codex
  python agent/tools/orchestrate_codex.py run CASE-CODEX-001 --node review=codex:gpt-6-luna
  python agent/tools/orchestrate_codex.py call CASE-CODEX-SMOKE --role analysis --task "..."
"""
import argparse
from contextvars import ContextVar
import json
import uuid
import sys

import harness
import orchestrate as orch


def install(data):
    original, original_env = orch.call_agent, orch.claude_env
    original_log = orch.log_row
    active = ContextVar("claude_selection", default={})
    orch.MAX_TURNS.setdefault("front", 24)

    def claude_env(role):
        env = harness.process_env("claude")
        native = original_env(role)
        env.update({k: v for k, v in native.items() if k in (
            "ANTHROPIC_BASE_URL", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_MODEL", "ANTHROPIC_SMALL_FAST_MODEL",
            "ENABLE_TOOL_SEARCH", "CLAUDE_AGENT_NAME", "MCP_SERVER_CONNECTION_BATCH_SIZE")})
        if active.get().get("model"):
            env["ANTHROPIC_MODEL"] = active.get()["model"]
        home = harness.PROJECT / ".codex" / "claude-runtime" / uuid.uuid4().hex
        home.mkdir(parents=True)
        env["CLAUDE_CONFIG_DIR"] = str(home)
        return env

    def call(role, task, case_id, label):
        chosen = harness.selection(data, role, label)
        if chosen.get("backend", "claude") == "codex":
            import codex_adapter
            return codex_adapter.call_agent(role, task, case_id, label, chosen, orch)
        token = active.set(chosen)
        try:
            result = original(role, task, case_id, label)
            result.update(backend="claude", model=chosen.get("model", orch.MODELS[role]))
            if role == "front":
                for path in sorted((orch.CASES / case_id / "log" / "runs").glob("*-front.jsonl"), reverse=True):
                    payload = orch.parse_output(path.read_text(encoding="utf-8"))
                    if payload.get("session_id") == result.get("session_id"):
                        result["result"] = payload.get("result", "")
                        break
            orch.log_row(case_id, event="harness", node=label, agent=role, **result)
            return result
        finally:
            active.reset(token)

    def log_row(case_id, **row):
        if row.get("agent") in harness.ROLES and row.get("event") in ("start", "end"):
            chosen = harness.selection(data, row["agent"], row.get("node", ""))
            row.update(backend=chosen.get("backend", "claude"),
                       model=chosen.get("model", "gpt-6-luna" if chosen.get("backend") == "codex" else orch.MODELS[row["agent"]]))
        return original_log(case_id, **row)

    orch.claude_env, orch.call_agent, orch.log_row = claude_env, call, log_row
    return call


def front(case_id, message, call):
    from codex_files import Files
    Files("front", case_id)
    if not (orch.CASES / case_id).exists():
        orch.case().case_new(case_id)
    one_shot = message is not None
    while True:
        if message is None:
            try:
                message = input("Client> ")
            except (EOFError, KeyboardInterrupt):
                return {"status": "closed"}
            if message.strip() in ("/exit", "/quit"):
                return {"status": "closed"}
        recorded = orch.case().client_said(case_id, message)
        if recorded.get("error"):
            return {"failure": "case", "detail": recorded.get("detail")}
        task = ("[Host] Work on case %s. The client message below was recorded verbatim in intake/dialogue.md; "
                "do not write a second client entry. Read the dialogue and current intake as needed to continue the conversation. "
                "The host starts orchestration: return [[START_RUN]] when the intake is ready.\nClient message:\n%s" % (case_id, message))
        result = call("front", task, case_id, "front")
        if result.get("failure"):
            return result
        reply = result.get("result", "")
        print(reply.replace("[[START_RUN]]", "").strip(), flush=True)
        if "[[START_RUN]]" in reply:
            stop = orch.run_case(case_id)
            relay = call("front", "[Host] Orchestration ended. Explain its result to the client; do not restart it.\n" + json.dumps(stop), case_id, "front")
            print(relay.get("result", ""), flush=True)
            if relay.get("failure"):
                return relay
        if one_shot:
            return {"status": "replied", "case_id": case_id}
        message = None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=("front", "run", "status", "call"))
    ap.add_argument("case_id")
    ap.add_argument("--config")
    ap.add_argument("--harness", choices=("claude", "codex"))
    ap.add_argument("--node", action="append", default=[])
    ap.add_argument("--role", choices=harness.ROLES, default="front")
    ap.add_argument("--task")
    a = ap.parse_args()
    from codex_files import Files
    Files(a.role, a.case_id)
    data = harness.settings(a.config, a.node)
    if a.harness:
        data["default"] = {"backend": a.harness}
    call = install(data)
    if a.command == "front":
        result = front(a.case_id, a.task, call)
    elif a.command == "call":
        if not a.task:
            ap.error("call requires --task")
        result = call(a.role, a.task, a.case_id, a.role)
    else:
        result = orch.run_case(a.case_id) if a.command == "run" else orch.status_of(a.case_id)
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result.get("failure") else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as exc:
        print(json.dumps({"failure": "configuration", "detail": harness.redact(str(exc))}))
        sys.exit(1)
