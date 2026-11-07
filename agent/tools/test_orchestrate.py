#!/usr/bin/env python
"""Construction checks of the orchestrator (agent/orchestration_cli_spec.en.md §6): no model is called.

  python agent/tools/test_orchestrate.py

A scripted stand-in replaces call_agent and writes through the real case server, so routing, status and limits run for
real against a temporary case. The render step is replaced by a stand-in that writes the PDF file. run_process is checked
with real child processes.
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

    def __init__(self, root, case_id, intake=("RUNNABLE",), draft=("DELIVERABLE",), legal=("DELIVERABLE",), reason="", replacements=None):
        self.ids = {a: Case(root, a) for a in ("front", "analysis", "review")}
        self.case_id, self.tasks, self.nodes = case_id, [], []
        self.verdicts = {"review_intake": list(intake), "review_draft": list(draft), "review_legal": list(legal)}
        self.reason = reason                                # a sentence stating a legal reason, written into every draft
        self.replacements = replacements                    # a fix-to-order list the draft review adds to its checklist
        self.fail_at, self.silent_at = {}, set()

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
            self.ids["analysis"].write_report(c, run_id, "briefing", "draft %d\n\nThe old sentence.\n\n%s" % (len(self.nodes), self.reason))
            self.ids["analysis"].write_report(c, run_id, "sources", "[]")
        else:
            v = self.verdicts[label]
            verdict = v.pop(0) if len(v) > 1 else v[0]
            which = {"review_intake": "intake", "review_draft": "draft", "review_legal": "legal_draft"}[label]
            back, word = verdict.split(":") if ":" in verdict else ("", verdict)
            body = ("Problem: a scripted finding.\n" if word == "REVISE" else "Problem: none.\n") + ("RETURN: %s\n" % back if back else "")
            if label == "review_draft" and self.replacements:
                body += "```replacements\n%s\n```\n" % json.dumps(self.replacements)
                self.replacements = None                    # given once; a real author acts on a return, the stand-in cannot
            result = self.ids["review"].write_review(c, which, body + "Verdict: %s" % word)
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


def fake_render(case_id, run_id):
    """The render step without xelatex: the client copy and a PDF file, newer than the draft and the checklists."""
    rd = orch.CASES / case_id / "report" / run_id
    time.sleep(0.02)
    orch.case().client_copy(rd, case_id, run_id)
    (rd / "briefing.pdf").write_bytes(b"pdf")
    return {"written": str(rd / "briefing.pdf")}


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    root = Path(tempfile.mkdtemp(prefix="taxorch-")) / "cases"
    orch.CASES = root
    orch.say = lambda text: None
    orch.intake_gate = lambda case_id: []
    orch.optimizer_run = fake_optimizer
    orch.self_check = lambda case_id, run_id, target: []
    orch.case().render_pdf = fake_render
    happy = ["review_intake", "run", "analysis", "review_draft", "render"]

    s = fresh(root, "C1")
    r = orch.run_case("C1")
    check("the whole flow runs in the agreed order", r["nodes"] == happy and r["stop"] == "delivered" and r["status"] == "delivered", r)
    check("the render step wrote the client copy and the PDF", (root / "C1" / "report" / r["run_id"] / "briefing.polished.md").exists() and (root / "C1" / "report" / r["run_id"] / "briefing.pdf").exists())
    r = orch.run_case("C1")
    check("a delivered case does nothing", r["nodes"] == [] and r["stop"] == "delivered", r)
    rows = [json.loads(x) for x in (root / "C1" / "log" / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    check("runs.jsonl has start and end rows and the stop", {x["event"] for x in rows} == {"start", "end", "stop"} and rows[1].get("status_after") == "intake_ok", rows[:2])
    check("run lock released", not (root / "C1" / "log" / "run.lock").exists())
    check("task text is the English sentence of the spec", s.tasks[0].startswith("Check the intake package of case C1."), s.tasks[0])
    check("the task names the prefetch pack and the case's files", "prefetch pack" in s.tasks[0] and "intake/index/pack/review_intake.md" in s.tasks[0].replace("\\", "/"), s.tasks[0][:300])

    s = fresh(root, "C2", draft=("analysis:REVISE", "DELIVERABLE"))
    r = orch.run_case("C2")
    check("stage 2 REVISE goes back to analysis and review again", r["nodes"] == happy[:4] + ["analysis", "review_draft", "render"] and r["stop"] == "delivered", r)
    check("the repeat carries revision, reason and the findings", "Revision 1. Reason: see " in s.tasks[3] and "review.md" in s.tasks[3] and "Problem: a scripted finding." in s.tasks[3], s.tasks[3])
    check("the revision number moved", orch.info("C2")["revision"] == 1, orch.info("C2"))

    s = fresh(root, "C3", replacements=[{"old": "The old sentence.", "new": "The new sentence."}])
    r = orch.run_case("C3")
    text = (root / "C3" / "report" / r["run_id"] / "briefing.md").read_text(encoding="utf-8")
    check("a reviewer's replacement is applied by the program, no return", r["nodes"] == happy and r["stop"] == "delivered" and "The new sentence." in text, (r, text))

    s = fresh(root, "C4", replacements=[{"old": "A sentence that is not there.", "new": "x"}])
    r = orch.run_case("C4")
    check("a replacement the program cannot place goes back to the author", r["nodes"] == happy + ["analysis", "review_draft", "render"] and "could not apply" in s.tasks[3], (r, s.tasks[3][:200]))

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
    s.verdicts["review_draft"] = ["DELIVERABLE"]
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
    orch.case().render_pdf = lambda case_id, run_id: {"error": "internal", "detail": "xelatex failed"}
    r = orch.run_case("C8")
    check("a failed render stops the run at reviewed", r["stop"] == "agent_failed" and "render" in r["detail"] and r["status"] == "reviewed", r)
    orch.case().render_pdf = fake_render
    r = orch.run_case("C8")
    check("the next run resumes at render", r["nodes"] == ["render"] and r["stop"] == "delivered", r)

    s = fresh(root, "C8b")
    renders = []

    def render_text_problem_once(case_id, run_id):
        renders.append(1)
        return {"error": "conflict", "detail": "fix the text first, nothing was rendered: sentence too long, split it: 58 words: x"} if len(renders) == 1 else fake_render(case_id, run_id)

    orch.case().render_pdf = render_text_problem_once
    r = orch.run_case("C8b")
    check("a text problem found at render goes back to the author, not to a stop", r["nodes"] == happy + ["analysis", "review_draft", "render"] and r["stop"] == "delivered" and "sentence too long" in s.tasks[3], (r, s.tasks[3][:200]))
    orch.case().render_pdf = fake_render

    s = fresh(root, "C9")
    s.fail_at["review_draft"] = ["rate_limited"]
    r = orch.run_case("C9")
    check("a rate limit stops the run", r["stop"] == "rate_limited" and r["status"] == "drafted", r)
    r = orch.run_case("C9")
    check("the next run resumes at the review", r["nodes"] == ["review_draft", "render"] and r["stop"] == "delivered", r)

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

    s = fresh(root, "C14", legal=("analysis:REVISE", "DELIVERABLE"), reason="The exemption applies because section 13 requires a headline rate of at least 15%.")
    r = orch.run_case("C14")
    check("the legal lane runs beside the draft review", "review_legal" in s.nodes and s.nodes.index("review_legal") > s.nodes.index("review_draft") - 2, s.nodes)
    check("a lane REVISE sends the draft back although the main review passed", r["nodes"] == happy[:4] + ["analysis", "review_draft", "render"] and r["stop"] == "delivered", r)
    check("the author is pointed at the lane's checklist", "review_legal.md" in s.tasks[s.nodes.index("analysis", 3)], s.tasks)

    s = fresh(root, "C15", draft=("analysis:REVISE", "DELIVERABLE"), legal=("analysis:REVISE", "DELIVERABLE"), reason="Section 13 requires at least 15%.")
    r = orch.run_case("C15")
    check("both reviews sending it back give the author both checklists", "review.md and " in s.tasks[s.nodes.index("analysis", 3)] and "review_legal.md" in s.tasks[s.nodes.index("analysis", 3)], s.tasks)

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

    env = orch.claude_env("analysis")
    check("env carries the analysis model and the gateway settings", env["ANTHROPIC_MODEL"] == orch.MODELS["analysis"] and env["ENABLE_TOOL_SEARCH"] == "false" and env["LANGSMITH_TRACING"] == "false" and env["CLAUDE_AGENT_NAME"] == "analysis")

    flags = orch.agent_flags("analysis")
    servers = json.loads(Path(flags[flags.index("--mcp-config") + 1]).read_text(encoding="utf-8"))["mcpServers"]
    check("each agent connects only its own servers", set(servers) == {"tax-case-analysis", "tax-read-analysis", "tax-rule", "tax-opt-calc"} and "--strict-mcp-config" in flags, sorted(servers))

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
