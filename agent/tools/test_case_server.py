#!/usr/bin/env python
"""Construction checks of tax-case (agent/case_mcp_spec.en.md §7): four identities against one temporary case.

  python agent/tools/test_case_server.py [--root <temp cases root>]
"""
import argparse
import asyncio
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
PROJECT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from case_server import Case, build_server  # noqa: E402

PY = sys.executable


async def call(server, name, args):
    r = await server.call_tool(name, args)
    return json.loads(r.content[0].text)


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="")
    a = ap.parse_args()
    root = Path(a.root) if a.root else Path(tempfile.mkdtemp(prefix="taxcase-")) / "cases"
    if root.exists():
        shutil.rmtree(root)
    fails = []

    def check(name, ok, detail=""):
        print(("ok   " if ok else "FAIL ") + name + (("  " + str(detail)[:300]) if detail and not ok else ""))
        if not ok:
            fails.append(name)

    front, _ = build_server(root, "front")
    analysis, _ = build_server(root, "analysis")
    polish, _ = build_server(root, "polish")
    review, _ = build_server(root, "review")
    C = "CASE-T"

    async def run():
        names = {ag: sorted(t.name for t in await s.list_tools()) for ag, s in (("front", front), ("analysis", analysis), ("polish", polish), ("review", review))}
        check("front tools", "case_new" in names["front"] and "write_intake" in names["front"] and "write_report" not in names["front"] and "write_review" not in names["front"], names["front"])
        check("analysis tools", "write_report" in names["analysis"] and "to_collect_append" in names["analysis"] and "write_intake" not in names["analysis"] and "case_new" not in names["analysis"], names["analysis"])
        check("polish tools", "write_polished" in names["polish"] and "render_pdf" in names["polish"] and "write_report" not in names["polish"] and "write_review" not in names["polish"], names["polish"])
        check("review tools", "write_review" in names["review"] and "to_collect_append" not in names["review"] and "write_report" not in names["review"] and "write_polished" not in names["review"], names["review"])
        for ag in names:
            check("%s has notes/bugs/status/checks" % ag, all(t in names[ag] for t in ("notes_append", "bug_append", "round_current", "review_status", "intake_check", "report_check")))

        # case_new and ledger
        r = await call(front, "case_new", {"case_id": C})
        check("case_new creates round 1", r.get("round") == 1 and (root / C / "rounds.json").exists() and (root / C / "notes" / "review" / "round-1").is_dir(), r)
        r = await call(front, "case_new", {"case_id": C})
        check("case_new twice -> conflict", r.get("error") == "conflict")
        r = await call(front, "case_new", {"case_id": "../x"})
        check("bad case_id -> invalid", r.get("error") == "invalid")
        r = await call(front, "round_current", {"case_id": C})
        check("status intake at start", r.get("status") == "intake", r)

        # intake writes and dirty flag
        facts = json.loads((PROJECT / "optimization" / "examples" / "case001.json").read_text(encoding="utf-8"))
        r = await call(front, "write_intake", {"case_id": C, "name": "facts", "content": json.dumps(facts)})
        check("write facts sets dirty", r.get("intake_dirty") is True and (root / C / "intake" / "facts.json").exists(), r)
        r = await call(front, "write_intake", {"case_id": C, "name": "facts", "content": "{not json"})
        check("bad JSON -> invalid", r.get("error") == "invalid")
        r = await call(front, "write_intake", {"case_id": C, "name": "sources", "content": json.dumps([{"key": "amount", "doc": "d.pdf", "page": 1, "quote": "100"}, {"key": "payer", "doc": "d.pdf", "page": 1}])})
        check("sources row lacking quote -> invalid", r.get("error") == "invalid")
        r = await call(front, "write_intake", {"case_id": C, "name": "sources", "content": json.dumps([{"key": "amount", "doc": "d.pdf", "page": 1, "quote": "人民币 1,400 万元", "confidence": 0.9, "confirmed_by_client": False}])})
        check("sources ok", "written" in r, r)
        r = await call(front, "write_intake", {"case_id": C, "name": "facts", "content": json.dumps(facts)})
        check("rewrite keeps .prev", r.get("prev") is True and (root / C / "intake" / "facts.json.prev").exists(), r)
        r = await call(analysis, "notes_append", {"case_id": C, "book": "reading", "text": "x"})
        check("analysis cannot use front's book", r.get("error") == "invalid")

        # dialogue and answers
        r = await call(front, "dialogue_append", {"case_id": C, "speaker": "client", "text": "我们是受益所有人，分红不转付。"})
        r2 = await call(front, "dialogue_append", {"case_id": C, "speaker": "front", "text": "收到。"})
        dlg = (root / C / "intake" / "dialogue.md").read_text(encoding="utf-8")
        check("dialogue appends two entries in order", r.get("entry") == 1 and r2.get("entry") == 2 and dlg.index("受益所有人") < dlg.index("收到"), dlg)
        r = await call(front, "write_intake", {"case_id": C, "name": "answers", "content": json.dumps({"bo": {"value": "yes", "quote": "我们是受益所有人，分红不转付。"}, "ppt": {"value": "unknown_asked", "quote": "不知道"}, "cfc": "unknown_not_asked"})})
        check("answers written", "written" in r, r)
        r = await call(front, "intake_check", {"case_id": C})
        probs = r.get("problems", [])
        check("intake_check runs and flags the quote not in dialogue", any("ppt" in p and "dialogue" in p for p in probs), probs)
        check("intake_check: optimizer accepts the example facts", not any("rejected by the optimizer" in p for p in probs), probs)

        # review of the intake: verdict rules and status derivation
        r = await call(review, "write_review", {"case_id": C, "which": "intake", "content": "All fine.\n\nVerdict: maybe"})
        check("review with unknown verdict -> invalid", r.get("error") == "invalid", r)
        r = await call(front, "round_set_run", {"case_id": C, "run_id": "20261101-abcdef12"})
        check("set_run before RUNNABLE -> conflict", r.get("error") == "conflict", r)
        r = await call(review, "write_review", {"case_id": C, "which": "intake", "content": "Checked.\n\nVerdict: RUNNABLE"})
        check("review intake accepted", r.get("verdict") == "RUNNABLE" and r.get("status") == "intake_ok", r)
        r = await call(front, "write_intake", {"case_id": C, "name": "constraints", "content": json.dumps({"exclude": ["th"]})})
        r = await call(front, "round_current", {"case_id": C})
        check("constraints write dirties the intake again", r.get("status") == "intake", r)
        await call(review, "write_review", {"case_id": C, "which": "intake", "content": "Checked again.\nVerdict: RUNNABLE."})
        r = await call(front, "round_current", {"case_id": C})
        check("re-review -> intake_ok", r.get("status") == "intake_ok", r)
        r = await call(review, "write_review", {"case_id": C, "which": "intake", "content": "Checked.\n\u603b\u5224\u65ad\uff1a\u53ef\u8dd1"})
        check("Chinese verdict tokens are no longer accepted", r.get("error") == "invalid", r)
        await call(front, "write_intake", {"case_id": C, "name": "notes", "content": "x"})
        r = await call(front, "round_current", {"case_id": C})
        check("a notes write sends the package back for review", r.get("status") == "intake", r)
        await call(review, "write_review", {"case_id": C, "which": "intake", "content": "One finding.\nVerdict: REVISE"})
        r = await call(front, "round_current", {"case_id": C})
        check("stage 1 REVISE is an open return to the front", (r.get("return_to") or {}).get("to") == "front" and r.get("status") == "intake", r)
        r = await call(front, "round_new", {"case_id": C})
        check("a stage 1 REVISE does not open a new round", r.get("error") == "conflict", r)
        await call(front, "write_intake", {"case_id": C, "name": "notes", "content": "y"})
        r = await call(front, "round_current", {"case_id": C})
        check("a fix closes the open return", r.get("return_to") is None, r)
        await call(review, "write_review", {"case_id": C, "which": "intake", "content": "Checked.\nVerdict: RUNNABLE"})
        r = await call(front, "round_set_run", {"case_id": C, "run_id": "20261101-abcdef12"})
        check("set_run without products -> not_found", r.get("error") == "not_found", r)
        pd = root / C / "intake" / "products" / "20261101-abcdef12"
        pd.mkdir(parents=True)
        (pd / "version.json").write_text("{}", encoding="utf-8")
        (pd / "ranking.json").write_text(json.dumps({"ranking": [{"cand_id": "c1", "branch_id": "c1.b2"}]}), encoding="utf-8")
        r = await call(front, "round_set_run", {"case_id": C, "run_id": "20261101-abcdef12"})
        check("set_run ok -> status ran", r.get("status") == "ran", r)
        r = await call(front, "round_new", {"case_id": C})
        check("round_new before delivered -> conflict", r.get("error") == "conflict", r)

        # analysis writes the report
        r = await call(analysis, "write_report", {"case_id": C, "run_id": "wrong", "name": "briefing", "content": "x"})
        check("write_report wrong run -> conflict", r.get("error") == "conflict", r)
        briefing = ("# 深圳晨光：2025 年度分红的持股结构建议\n\n客户：深圳市晨光精密制造有限公司 | 2026-11-01\n\n## 一、策略思路\n推荐由新加坡母公司直接持有深圳公司（依据《内地和新加坡协定》第十条第二款）。\n\n"
                                        "## 三、现状\n……\n\n## 四、备选方案\n……\n\n## 五、最优方案\n……\n\n## 六、税负比较\n| 方案 | 税负 |\n|---|---|\n\n## 七、条件与要求\n……\n\n## 八、执行\n……\n\n"
                    "## 附录 A 待确认事项与假设\n\n## 附录 B 法规依据与资料来源\n\n内部编号：CASE-T / 20261101-abcdef12\n")
        r = await call(analysis, "write_report", {"case_id": C, "run_id": "20261101-abcdef12", "name": "briefing", "content": briefing})
        check("write_report ok", "written" in r, r)
        r = await call(analysis, "write_report", {"case_id": C, "run_id": "20261101-abcdef12", "name": "sources", "content": json.dumps([{"id": "S1", "kind": "product", "ref": "intake/products/20261101-abcdef12/ranking.json", "where": "一、策略思路 / 推荐由新加坡母公司直接持有"}, {"id": "S2", "kind": "cite", "ref": "cn.reg.eit#91", "where": "二、法律论证"}, {"id": "S3", "kind": "cite", "ref": "no.such#1", "where": "二、法律论证"}])})
        check("write sources ok", "written" in r, r)
        r = await call(front, "round_current", {"case_id": C})
        check("status drafted after the analysis briefing", r.get("status") == "drafted", r)
        r = await call(review, "write_review", {"case_id": C, "which": "final", "content": "x\nVerdict: DELIVERABLE"})
        check("the old final stage is refused without a polished report", r.get("error") == "conflict", r)
        r = await call(review, "report_check", {"case_id": C, "run_id": "20261101-abcdef12", "target": "draft", "text_only": True})
        probs = r.get("problems", [])
        check("report_check(draft): structure passes, bad cite flagged", any("no.such#1" in p for p in probs) and not any("part missing" in p or "lacks the part" in p or "appendix" in p or "identifiers" in p for p in probs), probs)
        check("report_check(draft) asks for the diagram block", any("flow" in p for p in probs), probs)
        doctored = briefing.replace("推荐由新加坡母公司直接持有深圳公司", "**一句话：** 推荐由新加坡母公司直接持有深圳公司，规则工具如此显示")
        await call(analysis, "write_report", {"case_id": C, "run_id": "20261101-abcdef12", "name": "briefing", "content": doctored})
        r = await call(review, "report_check", {"case_id": C, "run_id": "20261101-abcdef12", "target": "draft", "text_only": True})
        check("report_check(draft) catches system vocabulary and a spoken lead-in", any("规则工具" in p for p in r.get("problems", [])) and any("spoken" in p for p in r.get("problems", [])), r)
        await call(analysis, "write_report", {"case_id": C, "run_id": "20261101-abcdef12", "name": "briefing", "content": briefing})

        # stage 2: the reviewed draft is the client report (2026-11-06)
        R = "20261101-abcdef12"
        r = await call(review, "write_review", {"case_id": C, "which": "draft", "content": "Problem: wrong article.\nVerdict: REVISE"})
        check("REVISE without a RETURN line -> invalid", r.get("error") == "invalid", r)
        r = await call(review, "write_review", {"case_id": C, "which": "draft", "content": "Problem: wrong article.\nRETURN: polish\nVerdict: REVISE"})
        check("stage 2 cannot return to polish", r.get("error") == "invalid", r)
        r = await call(review, "write_review", {"case_id": C, "which": "draft", "content": "Problem: none found.\nRETURN: analysis\nVerdict: REVISE"})
        check("a REVISE with no problem stated -> invalid", r.get("error") == "invalid", r)
        r = await call(review, "write_review", {"case_id": C, "which": "draft", "content": "Problem: wording.\n```replacements\nnot json\n```\nRETURN: analysis\nVerdict: REVISE"})
        check("a malformed replacements block -> invalid", r.get("error") == "invalid", r)
        r = await call(review, "write_review", {"case_id": C, "which": "draft", "content": "Problem: wrong article.\nRETURN: analysis\nVerdict: REVISE"})
        s1 = await call(front, "round_current", {"case_id": C})
        check("stage 2 REVISE keeps drafted and names analysis", s1.get("status") == "drafted" and s1["return_to"]["to"] == "analysis" and s1["return_to"]["which"] == "draft", s1)
        r = await call(analysis, "write_report", {"case_id": C, "run_id": R, "name": "briefing", "content": briefing})
        s1 = await call(front, "round_current", {"case_id": C})
        check("a rewritten draft closes the return", s1.get("status") == "drafted" and s1.get("return_to") is None, s1)
        await call(review, "write_review", {"case_id": C, "which": "draft", "content": "Problem: a fact is wrong.\nRETURN: front\nVerdict: REVISE"})
        s1 = await call(front, "round_current", {"case_id": C})
        check("stage 2 can return to the front", s1["return_to"]["to"] == "front", s1)
        await call(review, "write_review", {"case_id": C, "which": "draft", "content": "Checked.\nVerdict: POLISHABLE"})
        s1 = await call(front, "round_current", {"case_id": C})
        check("the old pass token still counts, DELIVERABLE -> reviewed", s1.get("status") == "reviewed" and s1.get("return_to") is None, s1)
        v = await call(review, "review_status", {"case_id": C, "which": "draft"})
        check("review_status reads the draft checklist", v.get("verdict") == "DELIVERABLE", v)

        # a re-check may not reopen lines that did not change
        snap = root / C / "log" / "reviewed" / "review_draft"
        snap.mkdir(parents=True, exist_ok=True)
        (snap / "briefing.md").write_text(briefing, encoding="utf-8")
        (snap / "run.txt").write_text(R, encoding="utf-8")
        r = await call(review, "write_review", {"case_id": C, "which": "draft", "content": "Problem: line 6 cites the wrong article.\nRETURN: analysis\nVerdict: REVISE"})
        check("a re-check finding on an unchanged line -> invalid", r.get("error") == "invalid", r)
        changed = briefing.replace("推荐由新加坡母公司直接持有深圳公司", "推荐由新加坡母公司持有深圳公司")
        await call(analysis, "write_report", {"case_id": C, "run_id": R, "name": "briefing", "content": changed})
        r = await call(review, "write_review", {"case_id": C, "which": "draft", "content": "Problem: line 6 cites the wrong article.\nRETURN: analysis\nVerdict: REVISE"})
        check("a re-check finding on a changed line is accepted", "written" in r, r)
        shutil.rmtree(snap)

        # fix to order: a replacements block the program applies, no return
        await call(analysis, "write_report", {"case_id": C, "run_id": R, "name": "briefing", "content": briefing})
        rep = json.dumps([{"old": "推荐由新加坡母公司直接持有深圳公司", "new": "建议由新加坡母公司直接持有深圳公司"}], ensure_ascii=False)
        r = await call(review, "write_review", {"case_id": C, "which": "draft", "content": "Problem: wording only.\n```replacements\n%s\n```\nVerdict: DELIVERABLE" % rep})
        check("a DELIVERABLE with a replacements block is accepted", "written" in r, r)
        done = Case(root, "front").apply_replacements(C, R)
        text = (root / C / "report" / R / "briefing.md").read_text(encoding="utf-8")
        s1 = await call(front, "round_current", {"case_id": C})
        check("the program applies the replacement and the review still stands", done.get("applied") == 1 and "建议由新加坡母公司" in text and s1.get("status") == "reviewed", (done, s1))
        done = Case(root, "front").apply_replacements(C, R)
        check("a replacement already applied is counted as done, not as a failure", done.get("applied") == 0 and done.get("already") == 1 and not done.get("failed"), done)

        # the client copy and the PDF decide delivered
        rd = root / C / "report" / R
        (rd / "frame" / "blocks").mkdir(parents=True, exist_ok=True)
        (rd / "frame" / "blocks" / "tax_table.md").write_text("| a | b |\n|---|---|\n| 1 | 2 |", encoding="utf-8")
        await call(analysis, "write_report", {"case_id": C, "run_id": R, "name": "briefing", "content": briefing.replace("## 六、税负比较\n", "## 六、税负比较\n{{block:tax_table}}\n")})
        await call(review, "write_review", {"case_id": C, "which": "draft", "content": "Problem: none.\nVerdict: DELIVERABLE"})
        copy = Case(root, "front").client_copy(rd, C, R).read_text(encoding="utf-8")
        check("the client copy expands the table marker and drops the internal line", "| 1 | 2 |" in copy and "{{block" not in copy and R not in copy, copy[-200:])
        r = await call(analysis, "render_pdf", {"case_id": C, "run_id": R})
        check("render refuses while the text has problems", r.get("error") == "conflict", r)
        time.sleep(0.05)
        (rd / "briefing.pdf").write_bytes(b"pdf")
        s2 = await call(front, "round_current", {"case_id": C})
        check("a PDF newer than draft and checklist -> delivered", s2.get("status") == "delivered", s2)
        time.sleep(0.05)
        await call(analysis, "write_report", {"case_id": C, "run_id": R, "name": "briefing", "content": briefing + "\n"})
        s3 = await call(front, "round_current", {"case_id": C})
        check("a changed draft drops delivered back to drafted", s3.get("status") == "drafted" and s3.get("return_to") is None, s3)
        await call(review, "write_review", {"case_id": C, "which": "draft", "content": "Problem: none.\nVerdict: DELIVERABLE"})
        time.sleep(0.05)
        (rd / "briefing.pdf").write_bytes(b"pdf")
        r = await call(front, "round_new", {"case_id": C})
        check("round_new -> round 2 intake", r.get("round") == 2 and (root / C / "notes" / "analysis" / "round-2").is_dir(), r)

        # notebooks, bugs
        r1 = await call(analysis, "notes_append", {"case_id": C, "book": "precommit", "text": "我凭差额判第一名。"})
        r2 = await call(analysis, "notes_append", {"case_id": C, "book": "precommit", "text": "实际：c1。中。"})
        nb = (root / C / "notes" / "analysis" / "round-2" / "precommit.md").read_text(encoding="utf-8")
        check("notes_append numbers entries in round-2", r1.get("entry") == "precommit-1" and r2.get("entry") == "precommit-2" and "round 2.0" in nb, nb)
        r = await call(review, "notes_append", {"case_id": C, "book": "precommit", "text": "x"})
        check("review cannot write analysis' book", r.get("error") == "invalid")
        b1 = await call(front, "bug_append", {"case_id": C, "layer": "工具", "symptom": "fx timed out", "expected": "rates returned", "repro": "fx --base CNY", "workaround": "used last month"})
        b2 = await call(front, "bug_append", {"case_id": C, "layer": "工具", "symptom": "fx  timed out", "expected": "", "repro": "", "workaround": ""})
        check("bug dedupe by symptom", b1.get("entry") == "B-1" and b2.get("duplicate_of") == "B-1", (b1, b2))
        b3 = await call(analysis, "bug_append", {"case_id": C, "layer": "rule", "symptom": "one holding percentage only", "affects_result": True})
        check("affects_result without the case effect -> invalid", b3.get("error") == "invalid", b3)
        b4 = await call(analysis, "bug_append", {"case_id": C, "layer": "rule", "symptom": "one holding percentage only", "affects_result": True, "effect": "Plan A tax 700,000 -> 1,400,000"})
        bugs = (root / C / "bugs" / "analysis.md").read_text(encoding="utf-8")
        check("affects_result with the effect is recorded", b4.get("entry") == "B-1" and "- affects_result: yes" in bugs and "- effect: Plan A" in bugs, bugs[-200:])
        r = await call(analysis, "to_collect_append", {"case_id": C, "law": "印花税法", "jur": "sg", "url": "", "why": "0.2% 只作参数"})
        check("analysis to_collect ok", "path" in r, r)

    asyncio.run(run())

    # log hook inference
    hook_in = {"session_id": "s1", "cwd": str(root.parent), "tool_name": "mcp__tax-case-analysis__notes_append",
               "tool_input": {"case_id": C, "book": "precommit", "text": "secret body"}}
    p = subprocess.run([PY, str(HERE / "log_hook.py")], input=json.dumps(hook_in), capture_output=True, text=True, encoding="utf-8")
    logp = root / C / "log" / "calls.jsonl"
    line = json.loads(logp.read_text(encoding="utf-8").splitlines()[-1]) if logp.exists() else {}
    check("log_hook writes case log with agent and no body", p.returncode == 0 and line.get("agent") == "analysis" and "text" in line.get("input_summary", {}).get("_other_keys", []) and "secret body" not in logp.read_text(encoding="utf-8"), line)
    hook_in2 = {"session_id": "s1", "cwd": str(root.parent), "tool_name": "Read", "tool_input": {"file_path": str(root / C / "intake" / "products" / "x" / "ranking.json")}}
    p = subprocess.run([PY, str(HERE / "log_hook.py")], input=json.dumps(hook_in2), capture_output=True, text=True, encoding="utf-8")
    line = json.loads(logp.read_text(encoding="utf-8").splitlines()[-1])
    check("log_hook infers case from a Read path", line.get("tool") == "Read" and "ranking.json" in line["input_summary"].get("file_path", ""), line)
    p = subprocess.run([PY, str(HERE / "log_hook.py")], input="not json", capture_output=True, text=True)
    check("log_hook never fails", p.returncode == 0)

    # the checks read an English report as well as a Chinese one
    english = ("# Advice\n\n## 1. Strategy\n**In a sentence:** go direct.\n\n## 2. Current State\nx\n\n## 3. Alternatives\nx\n\n## 4. Optimal\nx\n\n"
               "## 5. Tax Comparison\nx\n\n## 6. Requirements\nx\n\n## 7. Implementation\nThe treaty text is not on file.\n\n## Appendix A Points to confirm\n\n## Appendix B Sources\n")
    C2 = "CASE-EN"

    async def run_english():
        await call(front, "case_new", {"case_id": C2})
        (root / C2 / "rounds.json").write_text(json.dumps({"current": 1, "rounds": [{"round": 1, "revision": 0, "run_id": "r1"}]}), encoding="utf-8")
        rd = root / C2 / "report" / "r1"
        rd.mkdir(parents=True)
        (rd / "briefing.md").write_text(english, encoding="utf-8")
        (rd / "briefing.polished.md").write_text(english, encoding="utf-8")
        return await call(review, "report_check", {"case_id": C2, "run_id": "r1", "target": "polished"})

    r = asyncio.run(run_english())
    probs = r.get("problems", [])
    check("report_check finds all parts of an English report", not any("part missing" in p or "appendix" in p for p in probs), probs)
    check("report_check catches an English spoken lead-in", any("spoken" in p for p in probs), probs)
    check("report_check catches English process wording", any("not on file" in p for p in probs), probs)

    # PDF template: flowchart from a dot block, numbered list, table, plain fenced block
    sample = root / "sample.md"
    flow = (PROJECT / "agent" / "templates" / "flowchart.example.json").read_text(encoding="utf-8")
    sample.write_text("# 标题\n\n**致：** 甲公司\n**日期：** 2026-11-01\n\n## 1. 策略思路\n\n1. 第一项\n2. 第二项\n\n```flow\n" + flow + "\n```\n\n"
                      "| 方案 | 税负 |\n|---|---|\n| A | 10% |\n\n```\nraw   text   keeps   spaces\n```\n", encoding="utf-8")
    out = root / "sample.pdf"
    p = subprocess.run([PY, str(HERE / "render_pdf.py"), str(sample), str(out)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("render_pdf builds a flow diagram, list, table and verbatim block with a layout report", p.returncode == 0 and out.exists() and "latex_errors=0" in p.stdout and "layout=" in p.stdout, (p.stdout + p.stderr)[-300:])
    bad_flow = root / "bad.md"
    bad_flow.write_text("# t\n\n```flow\n{not json\n```\n", encoding="utf-8")
    p = subprocess.run([PY, str(HERE / "render_pdf.py"), str(bad_flow), str(root / "bad.pdf")], capture_output=True, text=True, encoding="utf-8", errors="replace")
    check("a malformed flow block is an error", p.returncode != 0 and "flow block" in p.stderr, p.stderr[-200:])

    print("tax-case checks: %s  (root %s)" % ("PASSED" if not fails else "%d failed" % len(fails), root))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
