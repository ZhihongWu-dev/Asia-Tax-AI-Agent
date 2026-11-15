"""Who may read what in a case folder: one rule set for the guard hook (host Read / Grep / Glob), the Codex file server and the
retrieval service (tax-read), so they never disagree (agent/case_mcp_spec.en.md §3, §6; agent/retrieval_spec.en.md §10).

Since 2026-11-12 it is an allowlist: an agent reads what is listed for it (and, where the node is known, for its node: the two
review lanes differ), and nothing else. A file a new feature adds is unreadable until it is listed here. The node comes from
the TAX_NODE environment variable, which the Codex server wrapper sets from its --node argument."""
import json
import os
import re
from pathlib import Path

AGENTS = ("front", "analysis", "polish", "review")
INTAKE_FILES = ("facts.json", "sources.json", "answers.json", "constraints.json", "notes.md", "handoff.md", "dialogue.md", "prompt.md",
                "review_intake.md", "run_input.json", "to_collect.md")
UI_ONLY = ("search.json", "graph.json", "labels.json", "edges", "index")     # the search view's files and the records index
PACK = {"front": "front", "analysis": "analysis", "review_intake": "review_intake", "review_draft": "review_draft", "review_legal": "legal_draft"}
LANE_CHECKLIST = {"review_draft": "review.md", "review_legal": "review_legal.md"}


def current_round(cases_root, case_id):
    """(round, run_id) of the case's current round, or (None, None)."""
    lp = Path(cases_root) / case_id / "rounds.json"
    try:
        ledger = json.loads(lp.read_text(encoding="utf-8")) if lp.exists() else {}
    except ValueError:
        ledger = {}
    cur = next((r for r in ledger.get("rounds", []) if r.get("round") == ledger.get("current")), None) if ledger else None
    return (cur.get("round"), cur.get("run_id")) if cur else (None, None)


def baseline_of(cases_root, case_id, run_id):
    """The run a revised edition starts from (impact.json level revise), else None."""
    imp = Path(cases_root) / case_id / "report" / str(run_id) / "impact.json"
    try:
        d = json.loads(imp.read_text(encoding="utf-8")) if imp.exists() else {}
    except ValueError:
        d = {}
    return d.get("baseline_run") if d.get("level") == "revise" else None


def node_of(agent, node):
    """The node an identity works as: front turns of every kind are 'front'; a review without a known node is any review lane."""
    node = str(node or os.environ.get("TAX_NODE", "")).strip()
    if agent == "front" or node.startswith("front"):
        return "front"
    if agent == "analysis":
        return "analysis"
    return node if node in PACK else ""


def packs_of(agent, node):
    """The prefetch packs this identity may read (its own node's only)."""
    if node:
        return {PACK[node] + ".md"}
    return {"front": {"front.md"}, "analysis": {"analysis.md"}, "polish": set(),
            "review": {"review_intake.md", "review_draft.md", "legal_draft.md"}}.get(agent, set())


def denied(agent, rel, cases_root, node=None):
    """Why `agent` may not read cases/<rel> (a path relative to the cases root, '/'-separated), or None when it may."""
    if agent not in AGENTS:
        return None
    parts = [p for p in str(rel).replace("\\", "/").split("/") if p not in ("", ".")]
    if len(parts) <= 1:
        return None                                            # the cases root or a case folder: a listing shows only what may be read
    case_id, p = parts[0], parts[1:]
    node = node_of(agent, node)
    cur_round, cur_run = current_round(cases_root, case_id)
    no = "%s does not read %s" % (agent, "/".join(p))
    if p[-1].endswith(".prev"):
        return "earlier versions are not read"
    top = p[0]
    if top == "intake":
        if len(p) == 1:
            return None
        if len(p) == 2 and p[1] in INTAKE_FILES:
            return None
        if p[1] == "documents":
            return None
        if p[1] == "withdrawn":
            return None if agent == "front" else no
        if p[1] == "index":
            if len(p) == 2 or (len(p) == 3 and p[2] == "pack"):
                return None
            if len(p) == 4 and p[2] == "pack" and p[3] in packs_of(agent, node):
                return None
            return no
        if p[1] == "products" and agent in ("analysis", "review", "polish"):
            if len(p) == 2:
                return None
            if p[2] != cur_run:
                return "%s does not read earlier runs' products" % agent
            if len(p) >= 4 and p[3] in UI_ONLY:
                return no
            return None
        return no
    if top == "notes":
        if len(p) == 1:
            return None
        owner, rnd = p[1], (p[2] if len(p) >= 3 else "")
        if owner != agent:
            mine = LANE_CHECKLIST.get(node, "review.md")         # each lane compares with the analysis notes after its own checklist
            review_written = bool(cur_run) and (Path(cases_root) / case_id / "report" / cur_run / mine).exists()
            if agent == "review" and owner == "analysis" and review_written and rnd in ("", "round-%s" % cur_round):
                return None
            return "%s may not read %s's notes" % (agent, owner)
        if rnd and cur_round is not None and rnd != "round-%s" % cur_round:
            return "notes of an earlier round are not read (current is round-%s)" % cur_round
        if agent == "review" and len(p) >= 4 and node:          # the two review lanes keep their notebooks apart
            if (node == "review_legal") != (p[3] == "legal.md"):
                return "the %s lane does not read that notebook" % node.replace("review_", "")
        return None
    if top == "report":
        if len(p) == 1:
            return None
        run, rest = p[1], p[2:]
        if run != cur_run:
            base = baseline_of(cases_root, case_id, cur_run) if cur_run else None
            if agent in ("analysis", "polish") and run == base and rest in (["briefing.md"], ["briefing.sources.json"], ["briefing.polished.md"]):
                return None                                    # a revised edition starts from the last delivered one
            return "%s does not read earlier runs' reports" % agent
        if not rest:
            return None
        name = rest[0]
        if agent == "front":
            return None if rest == ["briefing.polished.md"] else no
        if name in ("briefing.md", "briefing.sources.json", "impact.json", "frame"):
            return None
        if name == "sections":
            return None if agent in ("analysis", "polish") else no
        if name == "pack":
            return None if len(rest) == 1 or rest[1] in packs_of(agent, node) else no
        if name in ("review.md", "review_legal.md"):
            if agent in ("analysis", "polish"):
                return None
            return None if not node or LANE_CHECKLIST.get(node) == name else no
        if name in ("briefing.polished.md", "briefing.polished.sources.json"):
            return None if agent == "polish" else no
        return no
    if top == "log":
        if len(p) == 1 and agent == "review":
            return None
        if agent == "review" and len(p) == 2 and re.fullmatch(r"review_changes-[\w-]+\.md", p[1]):
            return None                                        # the orchestrator's change file for a re-check is part of the task
        return no
    return no                                                  # bugs/, chat.json, rounds.json and anything a feature adds later
