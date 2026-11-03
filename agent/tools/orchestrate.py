#!/usr/bin/env python
"""The orchestrator of the four agents (agent/orchestration_cli_spec.en.md): LangGraph picks the next step, Claude Code runs it.

  python agent/tools/orchestrate.py front [case_id]     interactive front session
  python agent/tools/orchestrate.py run <case_id>       walk from the current status to a stop, print one JSON line
  python agent/tools/orchestrate.py status <case_id>    read only: status, next node, last stop
  python agent/tools/orchestrate.py graph               export the node graph to agent/orchestration_graph.mmd
  python agent/tools/orchestrate.py clear <case_id> <agent/B-n>     after a fix: the bug no longer holds the run

Status comes from the case files after every step, so `run` resumes from wherever a case stands and the graph needs no
checkpointer. An agent's own report does not count: a node is complete when its files changed and the self-check is clean.
"""
import argparse
import difflib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

os.environ["LANGSMITH_TRACING"] = "false"              # set before langgraph is imported

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from case_server import Case, closing_answers, draft_files, report_files  # noqa: E402
from make_agents import TOOLS  # noqa: E402

CASES = PROJECT / "cases"
AGENTS_JSON = PROJECT / ".claude" / "agents.json"
MCP_DIR = PROJECT / ".claude" / "mcp"
BASE_URL = "https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic"
FAST_MODEL = "qwen3.7-plus"
MODELS = {"front": "qwen3.7-plus", "analysis": "qwen3.8-max", "polish": "qwen3.7-max", "review": "qwen3.7-plus"}
MAX_TURNS = {"analysis": 80, "polish": 60, "review": 80}
NODE_LIMIT = 4                                         # runs of one node inside one `run`
NODE_TIMEOUT = 10800                                   # seconds; a guard against a hang, since a full analysis can take over an hour
RECURSION_LIMIT = 60
STREAM_FLAGS = ["--output-format", "stream-json", "--verbose", "--include-partial-messages"]
NODE_AGENT = {"review_intake": "review", "analysis": "analysis", "review_draft": "review", "polish": "polish", "review_final": "review"}
TASKS = {
    "review_intake": "Check the intake package of case {case_id}.",
    "analysis": "Write the briefing draft for case {case_id}, run {run_id}.",
    "review_draft": "Check the briefing draft of case {case_id}, run {run_id}.",
    "polish": "Polish the reviewed draft of case {case_id}, run {run_id} and produce the PDF.",
    "review_final": "Compare the polished report with the draft of case {case_id}, run {run_id}.",
}
LEGAL = {
    "dispatch": ("review_intake", "run", "analysis", "review_draft", "polish", "review_final"),
    "review_intake": ("run",),
    "run": ("analysis",),
    "analysis": ("analysis", "review_draft"),
    "review_draft": ("analysis", "polish"),
    "polish": ("analysis", "polish", "review_final"),
    "review_final": ("analysis", "polish"),
}
RATE_LIMIT = re.compile(r"(?i)\b429\b|rate.?limit|too many requests|usage limit|quota")
NETWORK = re.compile(r"(?i)ECONNRESET|ETIMEDOUT|ENOTFOUND|socket hang up|fetch failed|connection error|\b50[234]\b")


class Flow(TypedDict, total=False):
    case_id: str
    next: str
    last_node: str
    stop: str
    detail: str
    reason: str
    redo: str
    counts: dict
    nodes: list


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def say(text):
    print(text, file=sys.stderr, flush=True)


# ------------------------------------------------------------ Claude Code
def qwen_key():
    for line in (PROJECT / ".env").read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("qwen_key="):
            return line.split("=", 1)[1].strip().strip("\"'")
    raise SystemExit("qwen_key is missing from .env")


def claude_bin():
    found = os.environ.get("CLAUDE_BIN") or shutil.which("claude")
    if found:
        return found
    installed = sorted((Path.home() / ".vscode" / "extensions").glob("anthropic.claude-code-*/resources/native-binary/claude.exe"),
                       key=lambda p: p.stat().st_mtime)
    if not installed:
        raise SystemExit("claude was not found: set CLAUDE_BIN")
    return str(installed[-1])


def claude_env(agent):
    env = dict(os.environ)
    env.update({"ANTHROPIC_BASE_URL": BASE_URL, "ANTHROPIC_AUTH_TOKEN": qwen_key(), "ANTHROPIC_MODEL": MODELS[agent],
                "ANTHROPIC_SMALL_FAST_MODEL": FAST_MODEL, "ENABLE_TOOL_SEARCH": "false", "CLAUDE_AGENT_NAME": agent,
                "MCP_SERVER_CONNECTION_BATCH_SIZE": "8", "LANGSMITH_TRACING": "false"})
    env.pop("ANTHROPIC_API_KEY", None)
    return env


def agent_flags(agent):
    """The agent's definition and only its own MCP servers."""
    return ["--agents", str(AGENTS_JSON), "--agent", agent, "--mcp-config", str(MCP_DIR / (agent + ".json")), "--strict-mcp-config"]


def stop_tree(proc):
    """End the process and its children; ending only the outer process leaves claude.exe alive and still writing files."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    else:
        proc.kill()
    proc.wait()


def run_process(cmd, env, out_path, err_path, timeout):
    """Run a command with its output in files; returns (exit code, timed out)."""
    with open(out_path, "wb") as out, open(err_path, "wb") as err:
        proc = subprocess.Popen(cmd, cwd=str(PROJECT), env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err)
        try:
            return proc.wait(timeout=timeout), False
        except subprocess.TimeoutExpired:
            stop_tree(proc)
            return proc.returncode, True
        except BaseException:
            stop_tree(proc)
            raise


def scrub(path):
    """The key must not reach a log, even if a tool echoed it."""
    key = qwen_key()
    data = path.read_bytes() if path.exists() else b""
    if key and key.encode() in data:
        path.write_bytes(data.replace(key.encode(), b"<redacted>"))


def classify(code, timed_out, payload, stderr):
    """None for a clean run, otherwise rate_limited, network or agent_failed."""
    text = "%s\n%s" % (stderr, payload.get("result") or "")
    if timed_out:
        return "agent_failed"
    if code == 0 and not payload.get("is_error") and payload.get("subtype", "success") == "success":
        return None
    if RATE_LIMIT.search(text):
        return "rate_limited"
    if NETWORK.search(text):
        return "network"
    return "agent_failed"


def parse_output(text):
    """The run's result event: the last line of the stream, or the whole output when it is one JSON document."""
    try:
        data = json.loads(text)
    except ValueError:
        data = []
        for line in text.splitlines():
            try:
                data.append(json.loads(line))
            except ValueError:
                continue
    if isinstance(data, list):
        data = next((x for x in reversed(data) if isinstance(x, dict) and x.get("type") == "result"), {})
    return data if isinstance(data, dict) else {}


def next_output_number(folder):
    return len(list(folder.glob("*.json*"))) + 1


def call_agent(agent, task, case_id, label):
    """One headless `claude -p`; its event stream goes live to log/runs/, where the web host reads it. Returns turns, session_id, failure and a short detail."""
    folder = CASES / case_id / "log" / "runs"
    folder.mkdir(parents=True, exist_ok=True)
    stem = folder / ("%03d-%s" % (next_output_number(folder), label))
    out, err = stem.with_suffix(".jsonl"), stem.with_suffix(".err")
    cmd = [claude_bin(), "-p", task] + agent_flags(agent) + STREAM_FLAGS + ["--max-turns", str(MAX_TURNS[agent]), "--allowedTools", ",".join(TOOLS[agent])]
    code, timed_out = run_process(cmd, claude_env(agent), out, err, NODE_TIMEOUT)
    scrub(out)
    scrub(err)
    payload = parse_output(out.read_text(encoding="utf-8", errors="replace"))
    stderr = err.read_text(encoding="utf-8", errors="replace")
    failure = classify(code, timed_out, payload, stderr)
    detail = "timed out after %d seconds" % NODE_TIMEOUT if timed_out else (payload.get("subtype") or stderr[-300:] or "exit %s" % code)
    return {"turns": payload.get("num_turns"), "session_id": payload.get("session_id"), "failure": failure,
            "detail": "" if failure is None else str(detail)}


# ------------------------------------------------------------ the case
_cases = {}


def case():
    """Program steps act as the front identity; one object per root, because it caches the library."""
    return _cases.setdefault(str(CASES), Case(CASES, "front"))


def info(case_id):
    return case().round_current(case_id)


def self_check(case_id, run_id, target):
    return case().report_check(case_id, run_id, target).get("problems", [])


def intake_gate(case_id):
    problems = list(case().intake_check(case_id).get("problems", []))
    if not (CASES / case_id / "intake" / "handoff.md").exists():
        problems.append("handoff.md is missing")
    return problems


def relative(path):
    try:
        return Path(path).resolve().relative_to(PROJECT).as_posix()
    except ValueError:
        return str(path)


def outputs(node, case_id, run_id):
    rd = CASES / case_id / "report" / str(run_id)
    return {"review_intake": [CASES / case_id / "intake" / "review_intake.md"],
            "analysis": list(draft_files(rd)),
            "review_draft": [rd / "review.md"],
            "polish": list(report_files(rd)),
            "review_final": [rd / "review_final.md"]}[node]


def reviewed_files(node, case_id, run_id):
    intake, rd = CASES / case_id / "intake", CASES / case_id / "report" / str(run_id)
    return ([intake / n for n in ("facts.json", "sources.json", "answers.json", "notes.md", "constraints.json")] if node == "review_intake"
            else [rd / "briefing.md", rd / "briefing.sources.json"])


def keep_reviewed(node, case_id, cur):
    """What review has just read, so that a re-check in this round can be given the difference."""
    folder = CASES / case_id / "log" / "reviewed" / node
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)
    for path in reviewed_files(node, case_id, cur.get("run_id")):
        if path.exists():
            shutil.copyfile(path, folder / path.name)
    (folder / "round.txt").write_text(str(cur.get("round")), encoding="utf-8")


def changes_since_review(node, case_id, cur):
    """A file with the difference from what review last read, or None on a first check of the round."""
    folder = CASES / case_id / "log" / "reviewed" / node
    mark = folder / "round.txt"
    if not mark.exists() or mark.read_text(encoding="utf-8") != str(cur.get("round")):
        return None
    out = []
    for path in reviewed_files(node, case_id, cur.get("run_id")):
        before = folder / path.name
        old = before.read_text(encoding="utf-8").splitlines() if before.exists() else []
        new = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        out += list(difflib.unified_diff(old, new, path.name + " (last checked)", path.name + " (now)", lineterm="", n=2))
    target = CASES / case_id / "log" / ("review_changes-%s.md" % node)
    target.write_text("\n".join(out) or "No file changed since your last checklist.", encoding="utf-8")
    return relative(target)


def stamps(paths):
    return [p.stat().st_mtime if p.exists() else 0 for p in paths]


def issues_file(case_id, cur):
    return CASES / case_id / "notes" / "polish" / ("round-%s" % cur["round"]) / "issues.md"


def log_row(case_id, **row):
    path = CASES / case_id / "log" / "runs.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    row["time"] = now()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def last_stop(case_id):
    path = CASES / case_id / "log" / "runs.jsonl"
    if not path.exists():
        return None
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return next((r for r in reversed(rows) if r.get("event") == "stop"), None)


# ------------------------------------------------------------ the optimizer (program step)
def optimizer_tool(tool, args):
    """Same code path as the MCP server, in its own process: the database server shares the module name mcp_server."""
    p = subprocess.run([sys.executable, str(HERE / "mcp_call.py"), "tax-opt-front", tool, json.dumps(args)], cwd=str(PROJECT),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=NODE_TIMEOUT)
    try:
        return json.loads(p.stdout)
    except ValueError:
        return {"error": "internal", "detail": (p.stderr or p.stdout)[-300:]}


def earlier_runs(case_id):
    ledger = json.loads((CASES / case_id / "rounds.json").read_text(encoding="utf-8"))
    return [r["run_id"] for r in ledger["rounds"] if r.get("run_id") and r["round"] != ledger["current"]]


def run_input(case_id):
    """facts.json with the client's answers as they may enter the computation. The file names the input, so the same facts give the same run."""
    intake = CASES / case_id / "intake"
    facts = json.loads((intake / "facts.json").read_text(encoding="utf-8"))
    answers = json.loads((intake / "answers.json").read_text(encoding="utf-8")) if (intake / "answers.json").exists() else {}
    facts["answers"] = closing_answers(answers)
    (intake / "run_input.json").write_text(json.dumps(facts, ensure_ascii=False, sort_keys=True, indent=1), encoding="utf-8")
    return "%s/intake/run_input.json" % case_id


def optimizer_run(case_id):
    """Returns (run_id, stop, detail): the products for the current facts, compared with the previous run if there is one."""
    rel = run_input(case_id)
    checked = optimizer_tool("validate_input", {"input": rel})
    if checked.get("error"):
        return None, "need_front", "facts.json was refused: %s" % checked.get("detail")
    done = optimizer_tool("run", {"case_id": case_id, "input": rel})
    run_id = done.get("run_id")
    if done.get("error") and not (done["error"] == "conflict" and run_id):
        return None, "agent_failed", "optimizer: %s" % done.get("detail")
    earlier = earlier_runs(case_id)
    if run_id in earlier:
        return None, "need_front", "the facts are unchanged since run %s, so a new run would give the same products" % run_id
    registered = case().round_set_run(case_id, run_id)
    if registered.get("error"):
        return None, "agent_failed", "round_set_run: %s" % registered.get("detail")
    if earlier:
        products = "%s/intake/products/" % case_id
        compared = optimizer_tool("diff", {"products": products + run_id, "against": products + earlier[-1]})
        if compared.get("error"):
            return None, "agent_failed", "diff: %s" % compared.get("detail")
    return run_id, None, ""


# ------------------------------------------------------------ the graph
def decide(state):
    """The next step from the files alone; `redo` is the one thing a node passes on directly."""
    if state.get("stop"):
        return {"next": "end"}
    case_id = state["case_id"]
    cur = info(case_id)
    if cur.get("error"):
        return {"next": "end", "stop": "agent_failed", "detail": str(cur.get("detail"))}
    st, back, run_id = cur["status"], cur.get("return_to"), cur.get("run_id")
    reason = ""
    defects = [] if st == "delivered" else case().open_defects(case_id)
    if defects:                                            # a report cannot rest on figures a layer below is known to get wrong
        return {"next": "end", "stop": "system_defect", "detail": "open bugs that affect the result: " + ", ".join(defects)}
    if state.get("redo"):
        node, reason = state["redo"], state.get("reason", "")
    elif st == "delivered":
        return {"next": "end", "stop": "delivered", "detail": relative(CASES / case_id / "report" / run_id / "briefing.pdf")}
    elif back and back["to"] == "front":
        return {"next": "end", "stop": "need_front", "detail": relative(back["path"])}
    elif back:
        node, reason = back["to"], "see %s" % relative(back["path"])
    elif st == "intake":
        problems = intake_gate(case_id)
        if problems:
            return {"next": "end", "stop": "need_front", "detail": "; ".join(problems)}
        node = "review_intake"
    elif st == "intake_ok":
        node = "run"
    elif st == "ran":
        node = "analysis"
    elif st == "reviewed":
        node = "polish"
    else:
        target, author, reviewer = ("draft", "analysis", "review_draft") if st == "drafted" else ("polished", "polish", "review_final")
        problems = self_check(case_id, run_id, target)
        node, reason = (author, "self-check problems: " + "; ".join(problems)) if problems else (reviewer, "")
    if (state.get("counts") or {}).get(node, 0) >= NODE_LIMIT:
        return {"next": "end", "stop": "revision_limit", "detail": "%s has run %d times; last reason: %s" % (node, NODE_LIMIT, reason)}
    return {"next": node, "reason": reason, "redo": ""}


def advance(state, node):
    """Merge the node's result with the next step; a destination the graph does not allow ends the run."""
    state = {**state, **decide(state)}
    if state["next"] != "end" and state["next"] not in LEGAL[node]:
        state.update(stop="agent_failed", detail="unexpected next step %s after %s" % (state["next"], node), next="end")
    return state


def dispatch_node(state):
    return advance(state, "dispatch")


def bump(state, node):
    counts = dict(state.get("counts") or {})
    counts[node] = counts.get(node, 0) + 1
    return {"last_node": node, "counts": counts, "nodes": list(state.get("nodes") or []) + [node]}


def agent_node(node):
    agent = NODE_AGENT[node]

    def run(state):
        case_id = state["case_id"]
        cur = info(case_id)
        files = outputs(node, case_id, cur.get("run_id"))
        before = stamps(files)
        issues = issues_file(case_id, cur)
        issues_before = issues.stat().st_size if issues.exists() else 0
        task = TASKS[node].format(case_id=case_id, run_id=cur.get("run_id"))
        if state.get("reason"):
            task += " Revision %s. Reason: %s" % (cur.get("revision", 0), state["reason"])
        changes = changes_since_review(node, case_id, cur) if node in ("review_intake", "review_draft") else None
        if changes:
            task += " This is a re-check: %s holds the difference from what you last checked. Check those changes and the items you sent back; do not reopen what has not changed." % changes
        step = bump(state, node)
        attempt = step["counts"][node]
        say("%s: %s, attempt %d" % (case_id, node, attempt))
        row = dict(node=node, agent=agent, model=MODELS[agent], round=cur.get("round"), revision=cur.get("revision", 0),
                   attempt=attempt, status_before=cur.get("status"), reason=state.get("reason", "")[:300])
        log_row(case_id, event="start", **row)
        began = time.time()
        result = call_agent(agent, task, case_id, node)
        if result["failure"] == "network":
            result = call_agent(agent, task, case_id, node)
        row.update(session_id=result.get("session_id"), turns=result.get("turns"), seconds=round(time.time() - began))
        state = {**state, **step, "reason": "", "redo": ""}
        grew = issues.exists() and issues.stat().st_size > issues_before
        if result["failure"] in ("rate_limited", "network", "agent_failed"):
            stop = "agent_failed" if result["failure"] == "network" else result["failure"]
            state.update(stop=stop, detail="%s: %s" % (node, result["detail"]))
        elif node == "polish" and grew and stamps(files)[2] == before[2]:
            text = issues.read_text(encoding="utf-8", errors="replace")
            state.update(redo="analysis", reason="polish issues: " + text[issues_before:].strip())
        elif stamps(files) == before and case().open_defects(case_id):          # it found a defect below it and stopped, as it should
            state.update(stop="system_defect", detail="open bugs that affect the result: " + ", ".join(case().open_defects(case_id)))
        elif stamps(files) == before:
            state.update(stop="agent_failed", detail="%s finished without updating %s" % (node, ", ".join(p.name for p in files)))
        else:
            if node in ("review_intake", "review_draft"):
                keep_reviewed(node, case_id, cur)
            back = info(case_id).get("return_to")
            if agent == "review" and back and back["to"] != "front" and back["which"] != "intake":
                case().round_revise(case_id)
        state = advance(state, node)
        row.update(status_after=info(case_id).get("status"), stop=state.get("stop", ""))
        log_row(case_id, event="end", **row)
        return state

    return run


def run_node(state):
    case_id = state["case_id"]
    cur = info(case_id)
    say("%s: run" % case_id)
    row = dict(node="run", agent="program", round=cur.get("round"), revision=cur.get("revision", 0), status_before=cur.get("status"))
    log_row(case_id, event="start", **row)
    began = time.time()
    run_id, stop, detail = optimizer_run(case_id)
    state = {**state, **bump(state, "run")}
    if stop:
        state.update(stop=stop, detail=detail)
    state = advance(state, "run")
    row.update(run_id=run_id, seconds=round(time.time() - began), status_after=info(case_id).get("status"), stop=state.get("stop", ""))
    log_row(case_id, event="end", **row)
    return state


def build_graph():
    from langgraph.graph import END, START, StateGraph
    g = StateGraph(Flow)
    g.add_node("dispatch", dispatch_node)
    g.add_node("run", run_node)
    for node in NODE_AGENT:
        g.add_node(node, agent_node(node))
    g.add_edge(START, "dispatch")
    for node, legal in LEGAL.items():
        g.add_conditional_edges(node, lambda s: s["next"], {**{n: n for n in legal}, "end": END})
    return g.compile()


# ------------------------------------------------------------ one run per case
def pid_alive(pid):
    if os.name == "nt":
        out = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid, "/NH"], capture_output=True, text=True, errors="replace").stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def take_lock(case_id):
    path = CASES / case_id / "log" / "run.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        text = path.read_text(encoding="utf-8").strip()
        if text.isdigit() and pid_alive(int(text)):
            return None
        path.unlink()
    path.write_text(str(os.getpid()), encoding="utf-8")
    return path


def run_case(case_id):
    if not (CASES / case_id / "rounds.json").exists():
        return {"case_id": case_id, "status": None, "stop": "agent_failed", "detail": "no such case", "run_id": None, "nodes": []}
    lock = take_lock(case_id)
    if lock is None:
        return {"case_id": case_id, "status": info(case_id).get("status"), "stop": "busy", "detail": "another run holds this case",
                "run_id": info(case_id).get("run_id"), "nodes": []}
    try:
        end = build_graph().invoke({"case_id": case_id, "counts": {}, "nodes": []}, {"recursion_limit": RECURSION_LIMIT})
    finally:
        lock.unlink(missing_ok=True)
    cur = info(case_id)
    result = {"case_id": case_id, "status": cur.get("status"), "stop": end.get("stop"), "detail": end.get("detail", ""),
              "run_id": cur.get("run_id"), "nodes": end.get("nodes", [])}
    log_row(case_id, event="stop", stop=result["stop"], detail=result["detail"], status=result["status"], nodes=result["nodes"])
    return result


def status_of(case_id):
    cur = info(case_id)
    if cur.get("error"):
        return cur
    step = decide({"case_id": case_id})
    return {"case_id": case_id, "round": cur.get("round"), "revision": cur.get("revision", 0), "run_id": cur.get("run_id"), "status": cur["status"],
            "return_to": cur.get("return_to"), "next": step.get("stop") or step.get("next"), "detail": step.get("detail", ""), "last_stop": last_stop(case_id)}


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("command", choices=("front", "run", "status", "graph", "clear"))
    ap.add_argument("case_id", nargs="?", default="")
    ap.add_argument("bug", nargs="?", default="")
    a = ap.parse_args()
    if a.command == "graph":
        target = PROJECT / "agent" / "orchestration_graph.mmd"
        target.write_text(build_graph().get_graph().draw_mermaid(), encoding="utf-8")
        print(json.dumps({"written": relative(target)}))
        return 0
    if a.command == "front":
        cmd = [claude_bin()] + agent_flags("front") + (["Work on case %s." % a.case_id] if a.case_id else [])
        return subprocess.call(cmd, cwd=str(PROJECT), env=claude_env("front"))
    if not a.case_id:
        ap.error("%s needs a case_id" % a.command)
    if a.command == "clear":
        print(json.dumps(case().clear_defect(a.case_id, a.bug), ensure_ascii=False))
        return 0
    print(json.dumps(run_case(a.case_id) if a.command == "run" else status_of(a.case_id), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
