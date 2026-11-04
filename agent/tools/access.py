"""Who may read what in a case folder: one rule set for the guard hook (host Read / Grep / Glob) and the retrieval service
(tax-read), so the two never disagree (agent/case_mcp_spec.en.md §3, §6; agent/retrieval_spec.en.md §10)."""
import json
from pathlib import Path

AGENTS = ("front", "analysis", "polish", "review")


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


def denied(agent, rel, cases_root):
    """Why `agent` may not read cases/<rel> (a path relative to the cases root, '/'-separated), or None when it may."""
    if agent not in AGENTS:
        return None
    parts = [p for p in str(rel).replace("\\", "/").split("/") if p not in ("", ".")]
    if not parts:
        return None
    case_id = parts[0]
    cur_round, cur_run = current_round(cases_root, case_id)
    review_written = bool(cur_run) and (Path(cases_root) / case_id / "report" / cur_run / "review.md").exists()
    if len(parts) >= 3 and parts[1] == "notes":
        owner = parts[2]
        rnd = parts[3] if len(parts) >= 4 else ""
        if owner != agent:
            if agent == "review" and owner == "analysis" and review_written and rnd == "round-%s" % cur_round:
                return None
            return "%s may not read %s's notes" % (agent, owner)
        if rnd and cur_round is not None and rnd != "round-%s" % cur_round:
            return "notes of an earlier round are not read (current is round-%s)" % cur_round
        return None
    if len(parts) >= 3 and parts[1] == "bugs":
        if parts[2].split(".")[0] != agent:
            return "%s may not read %s's bug log" % (agent, parts[2].split(".")[0])
        return None
    if len(parts) >= 2 and parts[1] == "log":
        if agent == "review" and review_written:
            return None
        if agent == "review" and len(parts) == 3 and parts[2].startswith("review_changes-") and parts[2].endswith(".md"):
            return None                                        # the orchestrator's change file for a re-check is part of the task
        return "the call log is read by the review agent only, after its review.md is written"
    if agent in ("analysis", "polish") and cur_run:
        base = baseline_of(cases_root, case_id, cur_run)
        allowed = {"analysis": ("briefing.md", "briefing.sources.json"), "polish": ("briefing.md", "briefing.polished.md")}[agent]
        if len(parts) == 4 and parts[1] == "report" and base and parts[2] == base and parts[3] in allowed:
            return None                                        # a revised edition starts from the last delivered one
        if len(parts) >= 3 and parts[1] == "report" and parts[2] != cur_run:
            return "%s does not read earlier runs' reports" % agent
        if len(parts) >= 4 and parts[1] == "intake" and parts[2] == "products" and parts[3] != cur_run:
            return "%s does not read earlier runs' products" % agent
    return None
