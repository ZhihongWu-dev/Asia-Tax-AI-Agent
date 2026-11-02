#!/usr/bin/env python
"""Construction checks of the orchestrator (agent/orchestration_cli_spec.en.md §6): no model is called.

  python agent/tools/test_orchestrate.py

A scripted stand-in replaces call_agent and writes through the real case server, so routing, status and limits run for
real against a temporary case. run_process is checked with real child processes.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import orchestrate as orch  # noqa: E402
from case_server import Case  # noqa: E402

RUN = "20261101-abcdef12"
fails = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + (("  " + str(detail)[:400]) if detail and not ok else ""))
    if not ok:
        fails.append(name)


class Script:
    """Plays the agents. `verdicts` holds the checklists each review node writes, in order; the last one repeats."""

    def __init__(self, root, case_id, intake=("RUNNABLE",), draft=("POLISHABLE",), final=("DELIVERABLE",)):
        self.ids = {a: Case(root, a) for a in ("front", "analysis", "polish", "review")}
        self.case_id, self.tasks, self.nodes = case_id, [], []
        self.verdicts = {"review_intake": list(intake), "review_draft": list(draft), "review_final": list(final)}
        self.fail_at, self.silent_at, self.issue_at = {}, set(), set()

    def __call__(self, agent, task, case_id, label):
        self.tasks.append(task)
        self.nodes.append(label)
        time.sleep(0.02)                                    # file times must advance
        if self.fail_at.get(label):
            return {"turns": 1, "session_id": "s", "failure": self.fail_at[label].pop(0), "detail": "scripted"}
        if label in self.silent_at:
            self.silent_at.discard(label)
            return {"turns": 1, "session_id": "s", "failure": None, "detail": ""}
        c, cur = self.case_id, self.ids["front"].round_current(self.case_id)
        run_id = cur.get("run_id")
        if label == "analysis":
            self.ids["analysis"].write_report(c, run_id, "briefing", "draft %d" % len(self.nodes))
            self.ids["analysis"].write_report(c, run_id, "sources", "[]")
        elif label == "polish":
            if label in self.issue_at:
                self.issue_at.discard(label)
                self.ids["polish"].notes_append(c, "issues", "the draft cites the wrong article")
            else:
                self.ids["polish"].write_polished(c, run_id, "polished", "report %d" % len(self.nodes))
                pdf = orch.CASES / c / "report" / run_id / "briefing.pdf"
                pdf.write_bytes(b"pdf")
        else:
            v = self.verdicts[label]
            verdict = v.pop(0) if len(v) > 1 else v[0]
            which = {"review_intake": "intake", "review_draft": "draft", "review_final": "final"}[label]
            back, word = verdict.split(":") if ":" in verdict else ("", verdict)
            body = "Finding.\n" + ("RETURN: %s\n" % back if back else "") + "Verdict: %s" % word
            result = self.ids["review"].write_review(c, which, body)
            assert "error" not in result, result
        return {"turns": 3, "session_id": "s", "failure": None, "detail": ""}


def fresh(root, case_id, **kw):
    front = Case(root, "front")
    front.case_new(case_id)
    front.write_intake(case_id, "facts", "{}")
    front.write_intake(case_id, "handoff", "one page")
    script = Script(root, case_id, **kw)
    orch.call_agent = script
    return script


def fake_optimizer(case_id):
    run_id = "%s-%d" % (RUN, len(json.loads((orch.CASES / case_id / "rounds.json").read_text(encoding="utf-8"))["rounds"]))
    products = orch.CASES / case_id / "intake" / "products" / run_id
    products.mkdir(parents=True, exist_ok=True)
    (products / "version.json").write_text("{}", encoding="utf-8")
    return run_id, None, "" if "error" not in orch.case().round_set_run(case_id, run_id) else "set_run failed"


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    root = Path(tempfile.mkdtemp(prefix="taxorch-")) / "cases"
    orch.CASES = root
    orch.say = lambda text: None
    orch.intake_gate = lambda case_id: []
    orch.optimizer_run = fake_optimizer
    orch.self_check = lambda case_id, run_id, target: []
    happy = ["review_intake", "run", "analysis", "review_draft", "polish", "review_final"]

    s = fresh(root, "C1")
    r = orch.run_case("C1")
    check("the whole flow runs in the agreed order", r["nodes"] == happy and r["stop"] == "delivered" and r["status"] == "delivered", r)
    r = orch.run_case("C1")
    check("a delivered case does nothing", r["nodes"] == [] and r["stop"] == "delivered", r)
    rows = [json.loads(x) for x in (root / "C1" / "log" / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    check("runs.jsonl has start and end rows and the stop", {x["event"] for x in rows} == {"start", "end", "stop"} and rows[1].get("status_after") == "intake_ok", rows[:2])
    check("run lock released", not (root / "C1" / "log" / "run.lock").exists())
    check("task text is the English sentence of the spec", s.tasks[0] == "Check the intake package of case C1.", s.tasks[0])

    s = fresh(root, "C2", draft=("analysis:REVISE", "POLISHABLE"))
    r = orch.run_case("C2")
    check("stage 2 REVISE goes back to analysis and review again", r["nodes"] == happy[:4] + ["analysis", "review_draft", "polish", "review_final"] and r["stop"] == "delivered", r)
    check("the repeat carries revision and reason", "Revision 1. Reason: see " in s.tasks[3] and "review.md" in s.tasks[3], s.tasks[3])
    check("the revision number moved", orch.info("C2")["revision"] == 1, orch.info("C2"))

    s = fresh(root, "C3", final=("polish:REVISE", "DELIVERABLE"))
    r = orch.run_case("C3")
    check("stage 3 RETURN polish reruns polish and stage 3 only", r["nodes"] == happy + ["polish", "review_final"] and r["stop"] == "delivered", r)

    s = fresh(root, "C4", final=("analysis:REVISE", "DELIVERABLE"))
    r = orch.run_case("C4")
    check("stage 3 RETURN analysis walks review and polish again", r["nodes"] == happy + ["analysis", "review_draft", "polish", "review_final"] and r["stop"] == "delivered", r)

    s = fresh(root, "C5", intake=("REVISE",))
    r = orch.run_case("C5")
    check("stage 1 REVISE stops at the front", r["stop"] == "need_front" and r["nodes"] == ["review_intake"] and "review_intake.md" in r["detail"], r)
    r = orch.run_case("C5")
    check("no fix, no second review", r["nodes"] == [] and r["stop"] == "need_front", r)
    s.verdicts["review_intake"] = ["RUNNABLE"]
    Case(root, "front").write_intake("C5", "facts", '{"fixed": true}')
    r = orch.run_case("C5")
    check("after the fix the same case goes through", r["stop"] == "delivered" and r["nodes"][0] == "review_intake", r)

    s = fresh(root, "C6", draft=("front:REVISE",))
    r = orch.run_case("C6")
    check("stage 2 RETURN front stops", r["stop"] == "need_front" and r["status"] == "drafted", r)
    n = Case(root, "front").round_new("C6")
    check("RETURN front lets the front open a new round", n.get("round") == 2, n)
    s.verdicts["review_draft"] = ["POLISHABLE"]
    Case(root, "front").write_intake("C6", "facts", '{"fixed": true}')
    r = orch.run_case("C6")
    check("the new round runs under a new run_id", r["stop"] == "delivered" and r["run_id"].endswith("-2") and r["nodes"] == happy, r)

    s = fresh(root, "C7")
    calls = []

    def draft_problem_once(case_id, run_id, target):
        calls.append(target)
        return ["part missing: strategy"] if calls.count("draft") == 1 and target == "draft" else []

    orch.self_check = draft_problem_once
    r = orch.run_case("C7")
    check("a failed self-check reruns the author, before review", r["nodes"] == happy[:3] + ["analysis"] + happy[3:] and "self-check problems: part missing" in s.tasks[2], (r, s.tasks[:3]))
    orch.self_check = lambda case_id, run_id, target: []

    s = fresh(root, "C8")
    s.issue_at.add("polish")
    r = orch.run_case("C8")
    check("polish issues without a PDF go to analysis with the text", r["nodes"] == happy[:5] + ["analysis", "review_draft", "polish", "review_final"] and "polish issues:" in s.tasks[4] and "wrong article" in s.tasks[4], (r, s.tasks[4:5]))

    s = fresh(root, "C9")
    s.fail_at["polish"] = ["rate_limited"]
    r = orch.run_case("C9")
    check("a rate limit stops the run", r["stop"] == "rate_limited" and r["status"] == "reviewed", r)
    r = orch.run_case("C9")
    check("the next run resumes at polish", r["nodes"] == ["polish", "review_final"] and r["stop"] == "delivered", r)

    s = fresh(root, "C10")
    s.silent_at.add("analysis")
    r = orch.run_case("C10")
    check("an agent that reports success but writes nothing is a failure", r["stop"] == "agent_failed" and "without updating" in r["detail"], r)

    s = fresh(root, "C11")
    s.fail_at["analysis"] = ["network"]
    r = orch.run_case("C11")
    check("one network failure is retried", r["stop"] == "delivered" and s.nodes.count("analysis") == 2, r)

    s = fresh(root, "C11b")
    s.fail_at["analysis"] = ["network", "network"]
    r = orch.run_case("C11b")
    check("a second network failure stops the run", r["stop"] == "agent_failed" and s.nodes.count("analysis") == 2, r)

    s = fresh(root, "C12", draft=("analysis:REVISE",))
    r = orch.run_case("C12")
    check("the limit stops an endless return loop", r["stop"] == "revision_limit" and r["nodes"].count("analysis") == orch.NODE_LIMIT, r)
    st = orch.status_of("C12")
    check("status reports the next step and the last stop", st["next"] == "analysis" and st["last_stop"]["stop"] == "revision_limit", st)

    s = fresh(root, "C13")
    (root / "C13" / "log").mkdir(exist_ok=True)
    (root / "C13" / "log" / "run.lock").write_text(str(os.getpid()), encoding="utf-8")
    r = orch.run_case("C13")
    check("a live run holds the case", r["stop"] == "busy" and not s.nodes, r)
    (root / "C13" / "log" / "run.lock").write_text("999999", encoding="utf-8")
    r = orch.run_case("C13")
    check("a dead run's lock is taken over", r["stop"] == "delivered", r)

    drawn = orch.build_graph().get_graph()
    edges = {(e.source, e.target) for e in drawn.edges}
    legal = {(a, b) for a, targets in orch.LEGAL.items() for b in targets} | {(a, "__end__") for a in orch.LEGAL} | {("__start__", "dispatch")}
    check("the graph has exactly the legal edges", edges == legal, edges ^ legal)
    check("the graph exports to Mermaid offline", "review_draft" in drawn.draw_mermaid())

    # the CLI layer
    check("classify: clean run", orch.classify(0, False, {"subtype": "success"}, "") is None)
    check("classify: rate limit", orch.classify(1, False, {"is_error": True, "result": "API Error: 429"}, "") == "rate_limited")
    check("classify: network", orch.classify(1, False, {}, "ECONNRESET") == "network")
    check("classify: turn limit", orch.classify(0, False, {"subtype": "error_max_turns", "is_error": True}, "") == "agent_failed")
    check("classify: timeout", orch.classify(1, True, {}, "") == "agent_failed")
    check("parse_output takes the result event of a list", orch.parse_output('[{"type":"system"},{"type":"result","num_turns":5}]').get("num_turns") == 5)

    env = orch.claude_env("polish")
    check("env carries the polish model and the gateway settings", env["ANTHROPIC_MODEL"] == "qwen3.7-max" and env["ENABLE_TOOL_SEARCH"] == "false" and env["LANGSMITH_TRACING"] == "false" and env["CLAUDE_AGENT_NAME"] == "polish")

    flags = orch.agent_flags("polish")
    servers = json.loads(Path(flags[flags.index("--mcp-config") + 1]).read_text(encoding="utf-8"))["mcpServers"]
    check("each agent connects only its own servers", set(servers) == {"tax-case-polish", "tax-db"} and "--strict-mcp-config" in flags, sorted(servers))

    work = root.parent / "proc"
    work.mkdir()
    marker = work / "child.pid"
    child = ("import subprocess,sys,time;"
             "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);"
             "open(%r,'w').write(str(p.pid));time.sleep(60)" % str(marker))
    began = time.time()
    code, timed_out = orch.run_process([sys.executable, "-c", child], dict(os.environ), work / "o", work / "e", 4)
    check("a timeout returns promptly", timed_out and time.time() - began < 20, (code, timed_out))
    check("a timeout ends the child process too", marker.exists() and not orch.pid_alive(int(marker.read_text())), marker.exists())

    print("orchestrator checks: %s  (root %s)" % ("PASSED" if not fails else "%d failed" % len(fails), root))
    shutil.rmtree(root.parent, ignore_errors=True)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
