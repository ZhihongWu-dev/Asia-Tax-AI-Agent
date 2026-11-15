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
import hashlib
import json
import os
import re
import shutil
import subprocess
import threading
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
import impact as impact_mod  # noqa: E402
import sections as sections_mod  # noqa: E402
import read_core  # noqa: E402
import read_index  # noqa: E402
import pack as pack_mod  # noqa: E402
import reasons as reasons_mod  # noqa: E402
from make_agents import TOOLS  # noqa: E402

CASES = PROJECT / "cases"
AGENTS_JSON = PROJECT / ".claude" / "agents.json"
MCP_DIR = PROJECT / ".claude" / "mcp"
BASE_URL = "https://token-plan.cn-beijing.maas.aliyuncs.com/apps/anthropic"
FAST_MODEL = "qwen3.8-flash"
MODELS = {"front": "qwen3.8-flash", "analysis": "qwen3.8-flash", "review": "qwen3.8-flash"}   # 2026-11-03: all on flash; 2026-11-06: no polish agent
MAX_TURNS = {"analysis": 150, "review": 80}
NODE_LIMIT = 6                                         # runs of one node inside one `run` (2026-11-05: 4 stopped a trial one wording fix short; a run past the limit is resumed by a person)
NODE_TIMEOUT = 10800                                   # seconds; a guard against a hang, since a full analysis can take over an hour
RECURSION_LIMIT = 60
STREAM_FLAGS = ["--output-format", "stream-json", "--verbose", "--include-partial-messages"]
NODE_AGENT = {"review_intake": "review", "analysis": "analysis", "review_draft": "review"}   # 2026-11-06: the reviewed draft is the client report; the program renders it
TASKS = {
    "review_intake": "Check the intake package of case {case_id}.",
    "analysis": "Write the client report (the briefing) for case {case_id}, run {run_id}, and render its PDF.",
    "review_draft": "Check the briefing draft of case {case_id}, run {run_id}.",
}
REVISE_TASKS = {
    "analysis": " Mode: revise against run {base}; see {case_id}/report/{run_id}/impact.json. Start from report/{base}/briefing.md and briefing.sources.json, "
                "rewrite what impact.json lists under sections and stale, carry the rest after checking it against this run's products, keep the structure names "
                "of the last edition, and open Part 1 with a short note of what changed since the last edition, taken from impact.json only. "
                "If the carried text cannot be reconciled with the new facts, record the line REWRITE: full with notes_append and stop.",
    "review_draft": " Mode: revised edition against run {base}; see {case_id}/report/{run_id}/impact.json. Check the sections and stale sentences it lists, the "
                    "changes note and every figure; read the carried parts only for contradictions with the changes. If the edition cannot stand as a revision, "
                    "write REWRITE: full on the line before RETURN: analysis.",
}
LANES = {"review_draft": ("review_legal", "legal_draft", "draft")}
LANE_AGENT = {lane: "review" for lane, _, _ in LANES.values()}       # the legal-reasoning lane: the review identity with its own stage
LANE_TASK = ("Check the legal reasoning of the {what} of case {case_id}, run {run_id}. The program's extract is {extract}: {n} sentences that state "
             "a legal reason, each with the sources rows, provisions, rules, parameters and decisions it rests on. Save your checklist with "
             "write_review(which={which}).")
LANE_RECHECK = (" This is a re-check: the extract holds only the sentences on lines changed since your last checklist ({last}); check those and "
                "whether the items you sent back are fixed.")
FINDING_LABEL = re.compile(r"(?i)^\s*(?:[-*]\s*)?(?:\d+\.\s*)?\**\s*(location|category|problem|evidence|suggestion|位置|类别|问题|证据|建议)\s*\**\s*[:：]")
FINDINGS_CAP = 6000                                     # characters of checklist findings carried into a return task
REWRITE = re.compile(r"(?m)^\s*REWRITE:\s*full\s*$")
SECTIONED = False                                      # the analysis node drafts in parts (spec §10); False = one agent writes the whole draft
WORKER_TASK = ("Write {parts} of the briefing draft for case {case_id}, run {run_id}. You are one of several section writers working at the same time: "
               "the other parts, the heading and Part 1 are written by others, Appendix B and the internal reference line by the program. Read "
               "report/{run_id}/frame/frame.md first: it gives the names of the structures, which you use exactly, and the program tables with their "
               "markers; put a table into your part by writing its marker on a line of its own and never retype its figures. Then read what your parts "
               "need from the intake and this run's products. Save each part with write_section (section = {ids}; the content starts with the part's "
               "heading line; sources = the sources of that part as a JSON list); every figure, citation and factual assertion you write outside the "
               "tables needs a source row. Correct a part with edit_section or by writing it again; never write another part, the whole draft or "
               "precommit.md. Stop when your parts are saved.")
INTEGRATOR_TASK = ("Finish the briefing draft for case {case_id}, run {run_id}. It is built from parts: {made}; Appendix B and the internal reference "
                   "line are generated by the program from the sources, and the program tables come from report/{run_id}/frame/frame.md. {todo}"
                   "First write precommit.md as your instructions say, before you open frame.md, the ranking or the parts. Then read the assembled "
                   "report/{run_id}/briefing.md and write the heading with the opening declaration of assumptions (section head) and Part 1 (section 1) "
                   "with write_section. Then make the whole read as one opinion: the same names and figures everywhere, no contradiction and no passage "
                   "repeated across parts, the declaration matching Appendix A, every judgment point that replaces the first structure in Part 7 and "
                   "Appendix A. Change sentences with edit_section and a whole part with write_section; never resend the whole draft or the whole "
                   "sources table. End with report_check(target=draft) and fix what it reports.")
INTEGRATOR_REVISE = (" This is a revised edition against run {base}: the program carried {carried} over from it and had {rewritten} rewritten because "
                     "of what report/{run_id}/impact.json lists. Open Part 1 with a short note of what changed since the last edition, taken from "
                     "impact.json and the intake only; check the carried parts against this run's products and correct with edit_section what no "
                     "longer holds. If the carried text cannot be reconciled with the new facts, record the line REWRITE: full with notes_append and stop.")
LEGAL = {
    "dispatch": ("review_intake", "run", "analysis", "review_draft", "render"),
    "review_intake": ("run",),
    "run": ("analysis",),
    "analysis": ("analysis", "review_draft"),
    "review_draft": ("analysis", "render"),
    "render": ("analysis",),                           # the program's render step: replacements applied, PDF made, delivered; a failed check goes back
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


NUMBERING = threading.Lock()


TEXT_CALL = re.compile(r"\[tool_use id=|<tool_call>|\"name\":\s*\"(?:Read|mcp__)")   # a tool call written as text: it never ran and the turn ended
RESUME_NOTE = ("Your last message wrote tool calls as plain text, so they did not run and nothing was saved. Continue the task from where "
               "you are: call the tools themselves.")
RESUMES = 2


def call_agent(agent, task, case_id, label):
    """One headless `claude -p`; its event stream goes live to log/runs/, where the web host reads it. A session that ended on
    tool calls written as text is resumed with a note, at most RESUMES times. Returns turns, session_id, failure and a short detail."""
    folder = CASES / case_id / "log" / "runs"
    folder.mkdir(parents=True, exist_ok=True)
    turns, resumed, prompt, extra = 0, 0, task, []
    while True:
        with NUMBERING:                                # section writers start together
            stem = folder / ("%03d-%s" % (next_output_number(folder), label))
            stem.with_suffix(".jsonl").touch()
        out, err = stem.with_suffix(".jsonl"), stem.with_suffix(".err")
        cmd = ([claude_bin(), "-p", prompt] + extra + agent_flags(agent) + STREAM_FLAGS +
               ["--max-turns", str(MAX_TURNS[agent]), "--allowedTools", ",".join(TOOLS[agent])])
        code, timed_out = run_process(cmd, claude_env(agent), out, err, NODE_TIMEOUT)
        scrub(out)
        scrub(err)
        payload = parse_output(out.read_text(encoding="utf-8", errors="replace"))
        stderr = err.read_text(encoding="utf-8", errors="replace")
        failure = classify(code, timed_out, payload, stderr)
        turns += payload.get("num_turns") or 0
        if failure is None and resumed < RESUMES and payload.get("session_id") and TEXT_CALL.search(str(payload.get("result") or "")[-4000:]):
            resumed += 1
            say("%s: %s wrote tool calls as text; resuming its session (%d)" % (case_id, label, resumed))
            prompt, extra = RESUME_NOTE, ["--resume", payload["session_id"]]
            continue
        break
    detail = "timed out after %d seconds" % NODE_TIMEOUT if timed_out else (payload.get("subtype") or stderr[-300:] or "exit %s" % code)
    return {"turns": turns or payload.get("num_turns"), "session_id": payload.get("session_id"), "failure": failure,
            "detail": "" if failure is None else str(detail), "resumed": resumed}


# ------------------------------------------------------------ the case
_cases = {}


def imp():
    """The impact module on the same cases root as the orchestrator (tests move it)."""
    impact_mod.CASES = CASES
    return impact_mod


def secs():
    """The sections module on the same cases root."""
    sections_mod.CASES = CASES
    return sections_mod


def sectioned_analysis(case_id, cur, mode):
    """The analysis node in parts: frame, section writers in parallel, assembly, one integrator pass (spec §10). Returns call_agent's result shape."""
    sm, run_id = secs(), cur["run_id"]
    base = mode.get("base") if mode["level"] == "revise" else None
    last = imp().baseline(case_id)
    sd = sm.sec_dir(case_id, run_id)
    if not (sm.frame_dir(case_id, run_id) / "frame.md").exists():
        sm.build_frame(case_id, run_id, (last or {}).get("run_id"))
    rewrite = set(sm.ORDER)
    carried = []
    if base and not sd.exists():
        rewrite = set(json.loads((CASES / case_id / "report" / run_id / "impact.json").read_text(encoding="utf-8")).get("sections") or [])
        keep = [x for x in sm.ORDER if x not in sm.PROGRAM and not any(x in parts and set(parts) & rewrite for parts in sm.GROUPS.values())]
        carried = sm.carry(case_id, run_id, base, keep)
    sd.mkdir(parents=True, exist_ok=True)
    (sd / ".sectioned").write_text(now(), encoding="utf-8")     # the case server accepts write_section only for such a run
    groups = {g: parts for g, parts in sm.GROUPS.items() if set(parts) & rewrite and sm.missing(case_id, run_id, parts)}
    began, results = time.time(), {}

    def work(g, parts):
        words = " and ".join(("Appendix %s" if x in "AB" else "Part %s") % x for x in parts)
        task = WORKER_TASK.format(parts=words, ids=" / ".join(parts), case_id=case_id, run_id=run_id)
        t0 = time.time()
        results[g] = call_agent("analysis", task, case_id, "analysis-%s" % g)
        log_row(case_id, event="sub", label="analysis-%s" % g, seconds=round(time.time() - t0), failure=results[g]["failure"] or "")

    threads = [threading.Thread(target=work, args=(g, parts)) for g, parts in groups.items()]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    say("%s: section writers %s done in %ds" % (case_id, ", ".join(groups) or "none", time.time() - began))
    (sd / ".assembled").write_text(now(), encoding="utf-8")
    sm.assemble(case_id, run_id, sm.products_version(case_id, run_id))
    for r in results.values():
        if r["failure"] in ("rate_limited",):
            return r
    gone = sm.missing(case_id, run_id, [x for parts in sm.GROUPS.values() for x in parts])
    made = "the section writers wrote %s in parallel" % ", ".join(sorted(set(sm.ORDER) - set(gone) - set(carried) - set(sm.PROGRAM) - set(sm.INTEGRATOR))) if groups else "no section writer ran"
    todo = ("These parts are still missing and are yours to write with write_section: %s. " % ", ".join(gone)) if gone else ""
    task = INTEGRATOR_TASK.format(case_id=case_id, run_id=run_id, made=made, todo=todo)
    if base:
        task += INTEGRATOR_REVISE.format(base=base, run_id=run_id, carried=", ".join(carried) or "nothing", rewritten=", ".join(sorted(rewrite)) or "nothing")
    t0 = time.time()
    result = call_agent("analysis", task, case_id, "analysis-integrate")
    log_row(case_id, event="sub", label="analysis-integrate", seconds=round(time.time() - t0), failure=result["failure"] or "")
    sm.assemble(case_id, run_id, sm.products_version(case_id, run_id))
    return result


def case():
    """Program steps act as the front identity; one object per root, because it caches the library."""
    return _cases.setdefault(str(CASES), Case(CASES, "front"))


def info(case_id):
    return case().round_current(case_id)


def self_check(case_id, run_id, target):
    if target == "draft":                                  # 2026-11-06: what the program can settle itself is not sent back
        fixes = case().autofix_draft(case_id, run_id).get("fixes") or []
        for f in fixes:
            say("%s: autofix: %s" % (case_id, f))
    return case().report_check(case_id, run_id, target).get("problems", [])


def checklist_findings(paths):
    """The findings of the checklists (location, problem, evidence, suggestion lines), for the author's return task."""
    out = []
    for p in paths:
        if not Path(p).exists():
            continue
        lines = [l.rstrip() for l in Path(p).read_text(encoding="utf-8", errors="replace").splitlines() if FINDING_LABEL.match(l)]
        if lines:
            out.append("%s:\n%s" % (Path(p).name, "\n".join(lines)))
    text = "\n".join(out)
    return text[:FINDINGS_CAP] + ("\n..." if len(text) > FINDINGS_CAP else "")


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
            "review_draft": [rd / "review.md"]}[node]


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
    (folder / "run.txt").write_text(str(cur.get("run_id")), encoding="utf-8")
    docs = CASES / case_id / "intake" / "documents"
    (folder / "documents.txt").write_text("\n".join(sorted(p.name for p in docs.iterdir())) if docs.exists() else "", encoding="utf-8")


def changes_since_review(node, case_id, cur):
    """A file with the difference from what review last read, or None on a first check of the round."""
    folder = CASES / case_id / "log" / "reviewed" / node
    mark = folder / "round.txt"
    if not mark.exists() or mark.read_text(encoding="utf-8") != str(cur.get("round")):
        return None
    run_mark = folder / "run.txt"
    if node != "review_intake" and (not run_mark.exists() or run_mark.read_text(encoding="utf-8") != str(cur.get("run_id"))):
        return None                                        # a draft of another run of this round: a first check
    out, size = [], 0
    for path in reviewed_files(node, case_id, cur.get("run_id")):
        before = folder / path.name
        old = before.read_text(encoding="utf-8").splitlines() if before.exists() else []
        new = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        out += list(difflib.unified_diff(old, new, path.name + " (last checked)", path.name + " (now)", lineterm="", n=2))
        size += sum(len(x) + 1 for x in new)
    if node != "review_intake" and sum(len(x) + 1 for x in out) > 0.6 * size:
        return None                                        # most of it was rewritten: check it as new rather than read a diff larger than the files
    target = CASES / case_id / "log" / ("review_changes-%s.md" % node)
    target.write_text("\n".join(out) or "No file changed since your last checklist.", encoding="utf-8")
    return relative(target)


def light_intake(case_id, cur):
    """The change file for a light intake review: the snapshot of an earlier round's passed review exists and little changed."""
    folder = CASES / case_id / "log" / "reviewed" / "review_intake"
    mark = folder / "round.txt"
    if not mark.exists() or mark.read_text(encoding="utf-8") == str(cur.get("round")) or not imp().baseline(case_id):
        return None
    text, why = imp().intake_light(case_id, folder, mark.read_text(encoding="utf-8"))
    if text is None:
        say("%s: full intake review (%s)" % (case_id, why))
        return None
    target = CASES / case_id / "log" / "review_changes-review_intake.md"
    target.write_text(text, encoding="utf-8")
    return relative(target)


def stamps(paths):
    return [p.stat().st_mtime if p.exists() else 0 for p in paths]


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


CONSTRAINT_KEYS = ("exclude", "consider", "allow_restructure", "payback_max", "allowed_subjects")


def run_input(case_id):
    """facts.json with the client's answers as they may enter the computation. The file names the input, so the same facts give the same run."""
    intake = CASES / case_id / "intake"
    facts = json.loads((intake / "facts.json").read_text(encoding="utf-8"))
    answers = json.loads((intake / "answers.json").read_text(encoding="utf-8")) if (intake / "answers.json").exists() else {}
    facts["answers"] = closing_answers(answers)
    cons = json.loads((intake / "constraints.json").read_text(encoding="utf-8")) if (intake / "constraints.json").exists() else {}
    cons = cons if isinstance(cons, dict) else {}
    own = facts.get("constraints") if isinstance(facts.get("constraints"), dict) else {}
    merged = {k: v for k, v in cons.items() if k in CONSTRAINT_KEYS} | own        # the client's constraints reach the optimizer
    if merged:
        facts["constraints"] = merged
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
        return None, "no_change", "the facts are unchanged since run %s, so the report stands" % run_id
    found = imp().impact(case_id, run_id)                      # before registering: a run that changes nothing does not open a report
    say("%s: impact %s (%s)" % (case_id, found["level"], "; ".join(found["reasons"])))
    if found["level"] == "none":
        return None, "no_change", "nothing the report uses changed since run %s, so the report stands" % found["baseline_run"]
    registered = case().round_set_run(case_id, run_id)
    if registered.get("error"):
        return None, "agent_failed", "round_set_run: %s" % registered.get("detail")
    index_products(case_id, run_id)
    if earlier:
        products = "%s/intake/products/" % case_id
        compared = optimizer_tool("diff", {"products": products + run_id, "against": products + earlier[-1]})
        if compared.get("error"):
            return None, "agent_failed", "diff: %s" % compared.get("detail")
    return run_id, None, ""


def index_products(case_id, run_id):
    """The records index of a run's products (agent/retrieval_spec.en.md §5); the agents read the products through it."""
    try:
        read_index.build_products(CASES / case_id / "intake" / "products" / run_id)
    except Exception as e:                                      # noqa: BLE001  (the agents can still read the files)
        say("%s: products index failed: %s: %s" % (case_id, type(e).__name__, e))


def index_case(case_id, ocr=False):
    """The case-file index; with ocr the scanned documents are read once (cached by file hash)."""
    try:
        read_index.build_case(CASES / case_id, ocr=ocr)
    except Exception as e:                                      # noqa: BLE001
        say("%s: case index failed: %s: %s" % (case_id, type(e).__name__, e))


READ_NOTE = (" Before anything else read the prefetch pack %s: it holds what this step always needs, each item with its id, which is "
             "the ref you cite. Find anything else with tax-read (map instead of Glob; search with several questions in one call; list, "
             "get, expand) rather than reading whole product files. The case's files: %s.")


def read_hint(case_id, node):
    """The pack of `node` and the case's file list, for the task text."""
    agent = NODE_AGENT.get(node, "analysis")
    try:
        r = read_core.Reader(agent, cases_root=CASES, log=False)
        made = r.pack(case_id, node)
        if made.get("error"):
            raise RuntimeError(made["detail"])
        note = READ_NOTE % (relative(made["path"]), pack_mod.inventory(r, case_id))
        rnd = info(case_id).get("round")
        books = sorted((CASES / case_id / "notes" / agent / ("round-%s" % rnd)).glob("*.md"))
        if books:                                               # what this round's notebooks already hold, so they are not reread whole
            note += (" Your notebooks of this round already hold: %s. Append to them; read an entry again only when you need it." %
                     ", ".join("%s (%d entries)" % (b.name, len(re.findall(r"(?m)^### ", b.read_text(encoding="utf-8", errors="replace")))) for b in books))
        return note
    except Exception as e:                                      # noqa: BLE001  (the agent can still map the case itself)
        say("%s: no pack for %s: %s: %s" % (case_id, node, type(e).__name__, e))
        return ""


def lane_prepare(node, case_id, cur):
    """The lane's task, or (None, why) when nothing it checks has changed since a checklist that passed (the program carries that one)."""
    lane, which, target = LANES[node]
    run_id = cur.get("run_id")
    rd = CASES / case_id / "report" / str(run_id)
    (rd / ".lanes").touch()
    md = rd / "briefing.md"
    last = rd / "review_legal.md"
    lines, recheck = None, False
    snap = CASES / case_id / "log" / "reviewed" / "review_draft"
    mark = snap / "round.txt"
    same_run = (snap / "run.txt").exists() and (snap / "run.txt").read_text(encoding="utf-8") == str(run_id)
    if last.exists() and same_run and mark.exists() and mark.read_text(encoding="utf-8") == str(cur.get("round")) and (snap / "briefing.md").exists():
        lines = reasons_mod.changed_lines((snap / "briefing.md").read_text(encoding="utf-8"), md.read_text(encoding="utf-8"))
        recheck = True
    path, n = reasons_mod.build(case_id, run_id, target, lines, cases_root=CASES)
    if n == 0 and (not recheck or case_mod_passed(last, which)):
        why = "no sentence stating a legal reason changed" if recheck else "no sentence of the draft states a legal reason"
        content = ("# Legal-reasoning check (carried by the program)\n\n%s since %s; nothing to check.\n\nDELIVERABLE\n" %
                   (why[0].upper() + why[1:], "the last passed checklist" if recheck else "the draft review"))
        if last.exists():
            shutil.copyfile(last, last.with_name(last.name + ".prev"))
        last.write_text(content, encoding="utf-8")
        return None, why
    task = LANE_TASK.format(what="briefing draft", case_id=case_id, run_id=run_id, extract=relative(path), n=n, which=which)
    if recheck:
        task += LANE_RECHECK.format(last=relative(last))
    return task, lane


def reasons_mod_checklist(which):
    from case_server import CHECKLISTS
    return CHECKLISTS[which]


def case_mod_passed(path, which):
    from case_server import passed
    return passed(path, which, 0)


def mode_of(case_id, run_id):
    """{"level", "base"} of this run from impact.json; full when there is none."""
    p = CASES / case_id / "report" / str(run_id) / "impact.json"
    if not run_id or not p.exists():
        return {"level": "full", "base": None}
    d = json.loads(p.read_text(encoding="utf-8"))
    return {"level": d.get("level", "full"), "base": d.get("baseline_run")}


def asked_full(case_id, cur):
    """A full rewrite asked by the analysis (its notebook) or by the draft review (its checklist)."""
    texts = []
    rd = CASES / case_id / "report" / str(cur.get("run_id"))
    if (rd / "review.md").exists():
        texts.append((rd / "review.md").read_text(encoding="utf-8", errors="replace"))
    nd = CASES / case_id / "notes" / "analysis" / ("round-%s" % cur.get("round"))
    if nd.exists():
        texts += [p.read_text(encoding="utf-8", errors="replace") for p in nd.glob("*") if p.is_file()]
    return any(REWRITE.search(t) for t in texts)


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
        node, reason = back["to"], "see %s" % " and ".join(relative(x) for x in [back["path"]] + back.get("also", []))
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
        node = "render"
    else:
        problems = self_check(case_id, run_id, "draft")
        node, reason = ("analysis", "self-check problems: " + "; ".join(problems)) if problems else ("review_draft", "")
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
        task = TASKS[node].format(case_id=case_id, run_id=cur.get("run_id"))
        mode = mode_of(case_id, cur.get("run_id")) if node != "review_intake" else {"level": "full"}
        if mode["level"] == "revise" and node in REVISE_TASKS:
            task += REVISE_TASKS[node].format(case_id=case_id, run_id=cur.get("run_id"), base=mode["base"])
        if state.get("reason"):
            task += " Revision %s. Reason: %s" % (cur.get("revision", 0), state["reason"])
            if node == "analysis" and "self-check" not in state["reason"]:      # the findings themselves, so the author applies rather than re-derives
                rd = CASES / case_id / "report" / str(cur.get("run_id"))
                found = checklist_findings([rd / "review.md", rd / "review_legal.md"])
                if found:
                    task += " The findings, each with its location and the suggested wording; change those sentences and nothing else:\n" + found
        changes = changes_since_review(node, case_id, cur) if node in ("review_intake", "review_draft") else None
        if changes:
            task += " This is a re-check: %s holds the difference from what you last checked. Check those changes and the items you sent back; do not reopen what has not changed." % changes
        elif node == "review_intake":
            light = light_intake(case_id, cur)
            if light:
                task += (" This round adds client feedback to a package you passed in an earlier round: %s holds every change since then. Check those changes "
                         "against the documents and the client's words in dialogue.md, and that they do not contradict the rest; do not re-check what has not changed." % light)
        if node == "review_intake":
            index_case(case_id, ocr=True)                       # the documents are read before the intake is checked
            try:
                run_input(case_id)                              # the program's input file follows the package the review reads
            except (OSError, ValueError) as e:
                say("%s: run_input not refreshed: %s" % (case_id, e))
        task += read_hint(case_id, node)
        step = bump(state, node)
        attempt = step["counts"][node]
        say("%s: %s, attempt %d" % (case_id, node, attempt))
        row = dict(node=node, agent=agent, model=MODELS[agent], round=cur.get("round"), revision=cur.get("revision", 0),
                   attempt=attempt, status_before=cur.get("status"), reason=state.get("reason", "")[:300])
        log_row(case_id, event="start", **row)
        began = time.time()
        if node == "analysis" and SECTIONED and not state.get("reason") and (secs().products_dir(case_id, cur.get("run_id")) / "brief.json").exists():
            result = sectioned_analysis(case_id, cur, mode)
        else:
            if node == "analysis" and (secs().sec_dir(case_id, cur.get("run_id")) / ".sectioned").exists():
                task += " The draft is built from parts: change it with edit_section or write_section, never resend the whole draft or the whole sources table."
            lane_task, lane = lane_prepare(node, case_id, cur) if node in LANES else (None, None)
            lane_out, lane_file = {}, None
            if lane_task:                                           # the legal-reasoning lane runs beside the review (spec §12)
                lane_file = CASES / case_id / "report" / str(cur.get("run_id")) / reasons_mod_checklist(LANES[node][1])
                lane_before = stamps([lane_file])
                lane_began = time.time()

                def lane_run():
                    out = call_agent("review", lane_task, case_id, lane)
                    if out["failure"] == "network":
                        out = call_agent("review", lane_task, case_id, lane)
                    out["seconds"] = round(time.time() - lane_began)
                    lane_out.update(out)
                worker = threading.Thread(target=lane_run, daemon=True)
                worker.start()
            elif lane:
                say("%s: legal lane carried (%s)" % (case_id, lane))
            result = call_agent(agent, task, case_id, node)
            if result["failure"] == "network":
                result = call_agent(agent, task, case_id, node)
            if lane_task:
                worker.join()
                row.update(lane_turns=lane_out.get("turns"), lane_seconds=lane_out.get("seconds"), lane_session_id=lane_out.get("session_id"))
                if result["failure"] is None and lane_out.get("failure"):
                    result = {**result, "failure": lane_out["failure"], "detail": "%s: %s" % (LANES[node][0], lane_out.get("detail"))}
                elif result["failure"] is None and stamps([lane_file]) == lane_before:
                    result = {**result, "failure": "agent_failed", "detail": "%s finished without updating %s" % (LANES[node][0], lane_file.name)}
        row.update(session_id=result.get("session_id"), turns=result.get("turns"), seconds=round(time.time() - began))
        state = {**state, **step, "reason": "", "redo": ""}
        if result["failure"] in ("rate_limited", "network", "agent_failed"):
            stop = "agent_failed" if result["failure"] == "network" else result["failure"]
            state.update(stop=stop, detail="%s: %s" % (node, result["detail"]))
        elif stamps(files) == before and case().open_defects(case_id):          # it found a defect below it and stopped, as it should
            state.update(stop="system_defect", detail="open bugs that affect the result: " + ", ".join(case().open_defects(case_id)))
        elif stamps(files) == before:
            state.update(stop="agent_failed", detail="%s finished without updating %s" % (node, ", ".join(p.name for p in files)))
        else:
            if node in ("review_intake", "review_draft"):
                keep_reviewed(node, case_id, cur)
            if mode["level"] == "revise" and node in ("analysis", "review_draft") and asked_full(case_id, cur):
                imp().impact(case_id, cur.get("run_id"), review_says_full=True)          # the edition falls back to a full rewrite
                say("%s: %s asked for a full rewrite" % (case_id, node))
                state.update(redo="analysis", reason="the revised edition cannot stand; write the briefing in full from this run's products")
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


def render_node(state):
    """The program's last step (2026-11-06): the reviewers' replacements applied, the client copy rendered to PDF, the draft checked once
    more with the fresh PDF; a check that fails sends the author the problems, a render that fails stops the run."""
    case_id = state["case_id"]
    cur = info(case_id)
    run_id = cur.get("run_id")
    say("%s: render" % case_id)
    row = dict(node="render", agent="program", round=cur.get("round"), revision=cur.get("revision", 0), status_before=cur.get("status"))
    log_row(case_id, event="start", **row)
    began = time.time()
    state = {**state, **bump(state, "render"), "reason": "", "redo": ""}
    done = case().apply_replacements(case_id, run_id)
    if done.get("applied"):
        say("%s: %d replacement(s) applied from the checklists" % (case_id, done["applied"]))
    if done.get("failed"):
        state.update(redo="analysis", reason="replacements the program could not apply (sentence not found once): " + "; ".join(done["failed"][:6]))
    else:
        made = case().render_pdf(case_id, run_id)
        if made.get("error") == "conflict":                # the text fails a check (a replacement can leave a long sentence): the author fixes it
            state.update(redo="analysis", reason="self-check problems after the reviewers' replacements: " + str(made.get("detail")).replace("fix the text first, nothing was rendered: ", ""))
        elif made.get("error"):
            state.update(stop="agent_failed", detail="render: %s" % made.get("detail"))
        else:
            problems = self_check(case_id, run_id, "draft")
            if problems:
                state.update(redo="analysis", reason="self-check problems: " + "; ".join(problems))
    state = advance(state, "render")
    row.update(seconds=round(time.time() - began), applied=done.get("applied", 0), status_after=info(case_id).get("status"), stop=state.get("stop", ""))
    log_row(case_id, event="end", **row)
    return state


def build_graph():
    from langgraph.graph import END, START, StateGraph
    g = StateGraph(Flow)
    g.add_node("dispatch", dispatch_node)
    g.add_node("run", run_node)
    g.add_node("render", render_node)
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


def preview(case_id):
    """The preview card of the current intake: (card, "") or (None, why not). Program only; registers nothing."""
    if not imp().baseline(case_id):
        return None, "no delivered report yet"
    problems = intake_gate(case_id)
    if problems:
        return None, "intake_check: " + "; ".join(problems[:3])
    rel = run_input(case_id)
    answers_p = CASES / case_id / "intake" / "answers.json"
    answers = json.loads(answers_p.read_text(encoding="utf-8")) if answers_p.exists() else {}
    seen = CASES / case_id / "log" / "preview_last.txt"
    stamp = hashlib.sha256((CASES / rel).read_bytes() + json.dumps(answers, sort_keys=True).encode()).hexdigest()
    if seen.exists() and seen.read_text(encoding="utf-8") == stamp:
        return None, "nothing changed since the last preview"
    done = optimizer_tool("run", {"case_id": case_id, "input": rel})
    run_id = done.get("run_id")
    if done.get("error") and not (done["error"] == "conflict" and run_id):
        return None, "optimizer: %s" % done.get("detail")
    seen.write_text(stamp, encoding="utf-8")
    index_products(case_id, run_id)
    return imp().card(case_id, CASES / case_id / "intake" / "products" / run_id, answers), ""


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
