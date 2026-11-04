#!/usr/bin/env python
"""Generate the agent definitions from the agent specs (agent/case_mcp_spec.en.md §7, agent/orchestration_cli_spec.en.md §3).

  python agent/tools/make_agents.py

Writes .claude/agents/<name>.md, .claude/agents.json (headless `--agent` does not find project definitions, so the
orchestrator passes this file with `--agents`) and .claude/mcp/<name>.json (only that agent's servers, taken from .mcp.json:
the first turn does not wait for every server, so connecting all eight left some agents without their tools). The body of each definition is the prompt block (```text ... ```) of the
English spec copy (*.en.md), copied verbatim, so the spec stays the single source; rerun after editing a spec. TOOLS is
also what the orchestrator passes as --allowedTools; each allowlist binds an identity to its own tax-case server.
"""
import io
import json
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
SPECS = {"front": "front_agent_spec.en.md", "analysis": "analysis_agent_spec.en.md",
         "polish": "polish_agent_spec.en.md", "review": "review_agent_spec.en.md"}
COMMON_TOOLS = ["Read", "Glob", "Grep", "WebSearch", "WebFetch", "mcp__tax-rule__*"]
TOOLS = {                        # agent/retrieval_spec.en.md §5.3: the library and product readers moved into tax-read
    "front": COMMON_TOOLS + ["Bash", "mcp__tax-read-front__*", "mcp__tax-opt-front__*", "mcp__tax-case-front__*"],
    "analysis": COMMON_TOOLS + ["mcp__tax-read-analysis__*", "mcp__tax-opt-calc__*", "mcp__tax-case-analysis__*"],
    "polish": ["Read", "Glob", "Grep", "mcp__tax-db__*", "mcp__tax-case-polish__*"],
    "review": COMMON_TOOLS + ["mcp__tax-read-review__*", "mcp__tax-opt-calc__*", "mcp__tax-case-review__*"],
}
SERVERS = {
    "front": ("tax-case-front", "tax-read-front", "tax-rule", "tax-opt-front"),
    "analysis": ("tax-case-analysis", "tax-read-analysis", "tax-rule", "tax-opt-calc"),
    "polish": ("tax-case-polish", "tax-db"),
    "review": ("tax-case-review", "tax-read-review", "tax-rule", "tax-opt-calc"),
}
DESC = {
    "front": "Front agent of the cross-border dividend tax planning system: talks to the client, extracts facts, starts the orchestrator and hands the report over",
    "analysis": "Analysis agent: reads the intake package and the optimizer products, writes the recommendation briefing draft; started by the orchestrator at status ran",
    "polish": "Polish agent: rewrites the reviewed draft to a top-firm standard without changing any number, fact or conclusion, and produces the PDF; started by the orchestrator at status reviewed",
    "review": "Review agent: checks the intake package, the briefing draft and the polished report against the draft, writes only checklists; started by the orchestrator",
}
STAGES = ("intake package", "briefing draft", "final comparison", "legal-reasoning lane")
SAVE_TOOLS = {
    "front": "write_intake for the intake package, put_document for documents, dialogue_append for the client's words, to_collect_append for collection requests",
    "analysis": "write_section for one part of a draft built from parts and edit_section to change its sentences; for a draft without parts, write_report (mode=append adds a part or rows) and edit_report",
    "polish": "write_polished for the polished report, edit_polished to change sentences, render_pdf for the PDF",
    "review": "write_review for the checklist (which = intake, draft, final, legal_draft or legal_final, matching your stage)",
}
SAVING = ("How files are saved: you have no Write or Edit tool. Every file named above is saved by calling a tool of your tax-case server: %s, "
          "notes_append for your notebooks, bug_append for bug reports. These tools create the folders. Text in your reply is not saved, "
          "so your work is not done until the tool has returned without an error.")


def prompt_blocks(spec_text):
    # the closing fence is a lone ``` on its own line; the dot references inside the prompt are mid-line, so anchor to full-line fences
    return re.findall(r"^```text$\n(.*?)^```$", spec_text, re.S | re.M)


def prompt_of(name):
    path = PROJECT / "agent" / SPECS[name]
    blocks = prompt_blocks(path.read_text(encoding="utf-8"))
    if not blocks:
        raise SystemExit("no ```text prompt block in %s" % SPECS[name])
    if name != "review":
        return blocks[0].rstrip()
    if len(blocks) != len(STAGES):
        raise SystemExit("%s must have %d prompt blocks, found %d" % (SPECS[name], len(STAGES), len(blocks)))
    parts = ["=== Stage %d: %s ===\n%s" % (i + 1, stage, block.rstrip()) for i, (stage, block) in enumerate(zip(STAGES, blocks))]
    return ("Run the stage your task names: \"Check the intake package\" is stage 1, \"Check the briefing draft\" is stage 2, "
            "\"Compare the polished report\" is stage 3, \"Check the legal reasoning\" is stage 4.\n\n" + "\n\n".join(parts))


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    out_dir = PROJECT / ".claude" / "agents"
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle = {}
    all_servers = json.loads((PROJECT / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]
    mcp_dir = PROJECT / ".claude" / "mcp"
    mcp_dir.mkdir(exist_ok=True)
    for name in SPECS:
        (mcp_dir / (name + ".json")).write_text(json.dumps({"mcpServers": {s: all_servers[s] for s in SERVERS[name]}}, indent=1), encoding="utf-8")
        body = prompt_of(name) + "\n\n" + SAVING % SAVE_TOOLS[name]
        fm = ["---", "name: %s" % name, "description: %s" % DESC[name],
              "tools: " + ", ".join(TOOLS[name]), "model: inherit", "---", ""]
        head = "<!-- generated by agent/tools/make_agents.py from agent/%s; edit the spec, not this file -->\n\n" % SPECS[name]
        (out_dir / (name + ".md")).write_text("\n".join(fm) + head + body + "\n", encoding="utf-8")
        bundle[name] = {"description": DESC[name], "prompt": body, "tools": TOOLS[name]}
        print("wrote", out_dir / (name + ".md"), "(%d chars)" % len(body))
    bundle_path = PROJECT / ".claude" / "agents.json"
    bundle_path.write_text(json.dumps(bundle, ensure_ascii=False), encoding="utf-8")
    print("wrote", bundle_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
