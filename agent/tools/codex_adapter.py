"""Native Codex CLI execution with private invocation homes and JSONL parsing."""
import ast
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

import harness
from make_agents import SERVERS
from make_codex import instruction

PROJECT = harness.PROJECT
# 2026-11-17: within one round (and one run) a node goes on in its own session instead of re-reading the case each time.
CONTEXT_FULL = re.compile(r"(?i)context.?(length|window)|maximum context|too many tokens|input (is )?too long|prompt is too long"
                          r"|exceeds? (the )?(model'?s )?(context|maximum)")
SCHEMA_REJECTED = re.compile(r"(?i)output.?schema|response_format|json_schema|text\.format|structured output")
SAME_SESSION = ("[Same session] This continues your session on this case: you already have what you read earlier in it. Re-read only "
                "what this task names or what has changed since; the files on disk are the current state.\n\n")
FORKED = ("[Forked session] This session goes on from your first draft of this run. The draft on disk may already hold the edits of "
          "later revisions: read each part the findings name as it is now before you change it.\n\n")


def tool_names(server):
    if server == "tax-files":
        return ("read_file", "list_files", "search", "read_image")
    definition = json.loads((PROJECT / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"][server]
    tree = ast.parse((PROJECT / definition["args"][0]).read_text(encoding="utf-8"))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr == "tool":
                    names.append(next((kw.value.value for kw in dec.keywords if kw.arg == "name" and isinstance(kw.value, ast.Constant)), node.name))
    return list(dict.fromkeys(names))               # a tool defined under two identities (render_pdf since 2026-11-06) is one key


def executable():
    configured = os.environ.get("TAX_CODEX_BIN")
    if configured:
        return configured
    # The app ships a newer standalone CLI than some npm installations.
    installs = sorted((Path(os.environ.get("LOCALAPPDATA", "")) / "OpenAI" / "Codex" / "bin").glob("*/codex.exe"),
                      key=lambda p: p.stat().st_mtime)
    found = str(installs[-1]) if installs else shutil.which("codex")
    if not found:
        raise ValueError("Codex CLI was not found; set TAX_CODEX_BIN")
    return found


def parse_output(text):
    result = {"is_error": True, "subtype": "incomplete", "num_turns": 0, "result": ""}
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind = event.get("type")
        if kind == "thread.started":
            result["session_id"] = event.get("thread_id")
        elif kind == "item.completed" and event.get("item", {}).get("type") == "agent_message":
            result["result"] = event["item"].get("text", "")
        elif kind == "turn.completed":
            result.update(is_error=False, subtype="success", num_turns=result["num_turns"] + 1, usage=event.get("usage", {}))
        elif kind in ("error", "turn.failed"):
            error = event.get("error") or event
            result.update(is_error=True, subtype="error", result=error.get("message", str(error)))
    return result


def model_metadata(chosen):
    """config.toml lines that tell Codex what the model is (2026-11-13): the official model catalog of Alibaba Cloud's 'Codex
    接入 Token Plan' page (context window 983,616 for qwen3.8-max and qwen3.8-flash, 95% usable), and the history size at
    which Codex compacts it. Without the catalog Codex does not know qwen's window and cannot compact in time. The limit:
    context 1,000,000 less the maximum output 131,072 = 868,928, less room for one more turn's input = 840,000 (harness.json)."""
    catalog = chosen.get("model_catalog")
    if not catalog:
        return []
    path = (PROJECT / catalog).resolve()
    slugs = {m.get("slug") for m in json.loads(path.read_text(encoding="utf-8")).get("models", [])}
    out = ['model_catalog_json = ' + json.dumps(str(path))]
    limit = (chosen.get("auto_compact_token_limit") or {}).get(chosen.get("model"))
    if chosen.get("model") in slugs and limit:
        out.append('model_auto_compact_token_limit = %d' % int(limit))
    return out


def prepare(role, case_id, chosen, instructions="", node=""):
    from codex_files import Files
    Files(role, case_id)
    folder = PROJECT / ".codex" / "runtime" / case_id / (role + "-" + uuid.uuid4().hex)
    work = folder / "work"
    work.mkdir(parents=True)
    # Store a copy so parallel generations or spec edits cannot change a live node.
    prompt = folder / "instructions.md"
    prompt.write_text(instruction(role) + "\n" + instructions, encoding="utf-8")
    q = lambda v: json.dumps(str(v))
    # 2026-11-05: an OpenAI-compatible provider other than OpenAI (e.g. Qwen through Token Plan's compatible-mode, wire_api
    # "chat") is given as chosen["provider"] = {base_url, wire_api, env_key, key_from}; key_from names the .env entry.
    provider = chosen.get("provider") or {}
    config = [
        'model = ' + q(chosen.get("model", "gpt-6-luna")),
        'model_reasoning_effort = ' + q(chosen.get("reasoning", "medium")),
        'model_provider = "tax_openai"',
        'forced_login_method = "api"', 'approval_policy = "never"',
        'sandbox_mode = "read-only"', 'project_doc_max_bytes = 0',
        'developer_instructions = ' + q(prompt.read_text(encoding="utf-8")),
        *model_metadata(chosen),
        'web_search = ' + q("disabled" if role == "polish" else "live"),
        # 2026-11-25: Codex cuts the middle out of a tool result above its default limit ("…N tokens truncated…"); a reader
        # page is at most 32,000 characters, which in Japanese or Chinese law text is more tokens than that default
        'tool_output_token_limit = %d' % int(chosen.get("tool_output_token_limit") or 40000),
        '[features]', 'shell_tool = false', 'view_image = false',
        'multi_agent = false', 'apps = false', 'plugins = false', 'remote_plugin = false', 'shell_snapshot = false',
        'browser_use = true', 'hooks = ' + ('true' if chosen.get("hooks", True) else 'false'),   # 2026-11-17: browser kept on, by the owner's choice
        '[skills]', 'include_instructions = false', '[skills.bundled]', 'enabled = false',
        '[analytics]', 'enabled = false', '[feedback]', 'enabled = false',
        '[model_providers.tax_openai]', 'name = "OpenAI-compatible API (isolated tax harness)"',
        'base_url = ' + q(provider.get("base_url", "https://api.openai.com/v1")),
        'env_key = ' + q(provider.get("env_key", "OPENAI_API_KEY")),
        'wire_api = ' + q(provider.get("wire_api", "responses")),
    ]
    for server in (*SERVERS[role], "tax-files"):
        config += ['[mcp_servers.' + q(server) + ']',
                   'command = ' + q(sys.executable),
                   'args = ' + json.dumps([str(PROJECT / "agent" / "tools" / "codex_mcp.py"),
                                          "--role", role, "--case", case_id, "--server", server, "--node", node]),
                   'cwd = ' + q(PROJECT), 'required = true',
                   'startup_timeout_sec = 600', 'tool_timeout_sec = 1200']   # the remote library loads slowly over a thin link
        for name in tool_names(server):
            config += ['[mcp_servers.' + q(server) + '.tools.' + q(name) + ']', 'approval_mode = "approve"']
    if chosen.get("hooks", True):                       # 2026-11-17: the tool-call log and guard of the Claude path (codex_hook.py)
        for event, kind in (("PreToolUse", "pre"), ("PostToolUse", "post")):
            config += ['[[hooks.%s]]' % event, '[[hooks.%s.hooks]]' % event, 'type = "command"',
                       'command = ' + q(hook_command(role, case_id, kind)), 'timeout = 10']
    (folder / "config.toml").write_text("\n".join(config) + "\n", encoding="utf-8")
    env = harness.process_env("codex", folder, provider)
    return folder, work, env


def hook_command(role, case_id, kind):
    # Unquoted on purpose: the shell Codex runs a hook in differs by platform, and neither path has a space.
    parts = [Path(sys.executable).as_posix(), (PROJECT / "agent" / "tools" / "codex_hook.py").as_posix(),
             "--role", role, "--case", case_id, "--event", kind]
    if any(" " in p for p in parts):
        raise ValueError("a hook path contains a space: %s" % parts)
    return " ".join(parts)


def command(work, how="fresh", session_id=None, schema=None, hooks=True):
    """A fresh session (`exec ... -`), or `exec resume|fork <session_id> -`, which take neither --cd nor --color: the
    process runs in `work` either way. Hooks are generated per call, so their hash is never trusted ahead of time."""
    flags = ["--strict-config", "--ignore-rules", "--json", "--skip-git-repo-check"]
    flags += ["--dangerously-bypass-hook-trust"] if hooks else []
    flags += ["--output-schema", str(schema)] if schema else []
    if how == "fresh":
        return [executable(), "--no-daemon", "exec", *flags, "--color", "never", "--cd", str(work), "-"]
    return [executable(), "--no-daemon", "exec", how, *flags, session_id, "-"]


# ------------------------------------------------------------ sessions within a round (2026-11-17)
def session_record(role, case_id, label, orch):
    """cases/<case>/log/sessions/<scope>/<key>.json: the front's per round, every other node's per round and run. A new round
    (or run) finds no record and starts fresh, so no context crosses rounds. One file per key: the parallel lanes and the host
    never write the same file."""
    try:
        cur = orch.info(case_id)
    except Exception:  # noqa: BLE001 - a case not created yet has no round
        return None
    if not isinstance(cur, dict) or cur.get("error") or cur.get("round") is None:
        return None
    scope = "round-%s" % cur["round"] if role == "front" else "round-%s-%s" % (cur["round"], cur.get("run_id") or "none")
    return orch.CASES / case_id / "log" / "sessions" / scope / ("%s.json" % ("front" if role == "front" else label))


def recall(record):
    try:
        saved = json.loads(record.read_text(encoding="utf-8"))
    except (OSError, ValueError, AttributeError):
        return None
    return saved if saved.get("last") and (PROJECT / saved.get("home", "") / "config.toml").exists() else None


def remember(record, home, session_id, first=None):
    if not record or not session_id:
        return
    record.parent.mkdir(parents=True, exist_ok=True)
    saved = {"home": Path(home).relative_to(PROJECT).as_posix(), "first": first or session_id, "last": session_id,
             "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    fresh = record.with_suffix(".tmp")
    fresh.write_text(json.dumps(saved), encoding="utf-8")
    os.replace(fresh, record)


def forget(record):
    if record:
        try:
            record.unlink()
        except OSError:
            pass


def schema_file(chosen, label):
    path = (chosen.get("output_schemas") or {}).get(label)
    return (PROJECT / path).resolve() if path and (PROJECT / path).exists() else None


def plan(role, case_id, label, chosen, orch, instructions="", fresh=False, schema=True):
    """How this call runs: resume the node's session of this round, fork the first one (a node listed in sessions.fork:
    each revision starts from the first draft's context, not from the pile of earlier revisions), or a fresh session."""
    conf = chosen.get("sessions") or {}
    record = session_record(role, case_id, label, orch) if conf.get("resume", True) else None
    saved = None if fresh or not record else recall(record)
    use = schema_file(chosen, label) if schema else None
    hooks = chosen.get("hooks", True)
    if saved:
        home = PROJECT / saved["home"]
        how, sid = ("fork", saved["first"]) if label in conf.get("fork", ()) else ("resume", saved["last"])
        env = harness.process_env("codex", home, chosen.get("provider") or {})
        return {"home": home, "work": home / "work", "env": env, "how": how, "sid": sid, "first": saved["first"],
                "record": record, "schema": use, "cmd": command(home / "work", how, sid, use, hooks)}
    home, work, env = prepare(role, case_id, chosen, instructions, node=label)
    return {"home": home, "work": work, "env": env, "how": "fresh", "sid": None, "first": None, "record": record,
            "schema": use, "cmd": command(work, schema=use, hooks=hooks)}


def opening(p):
    return {"resume": SAME_SESSION, "fork": FORKED}.get(p["how"], "")


def retry_fresh(p, payload, failure, stderr):
    """A resumed or forked call that hit the context limit, or that could not start the old session, goes again fresh."""
    if p["how"] == "fresh" or failure != "agent_failed":
        return False
    return bool(CONTEXT_FULL.search("%s\n%s" % (stderr, payload.get("result") or ""))) or not payload.get("num_turns")


def retry_plain(p, payload, failure, stderr):
    """The provider refused the output schema (untested on Token Plan as of 2026-11-17): go again without it."""
    return bool(p["schema"]) and failure == "agent_failed" and bool(SCHEMA_REJECTED.search("%s\n%s" % (stderr, payload.get("result") or "")))


def settle(p, payload, failure, stderr=""):
    """After a run: keep the session for the next call of this node, or drop a record that can no longer be resumed."""
    if failure is None:
        sid = payload.get("session_id") or (p["sid"] if p["how"] == "resume" else None)
        remember(p["record"], p["home"], sid, p["first"])
    elif retry_fresh(p, payload, failure, stderr):
        forget(p["record"])


def structured(p, payload):
    """The final reply under --output-schema as a dict, or None (no schema, or the model did not keep to it)."""
    if not p["schema"]:
        return None
    try:
        reply = json.loads(payload.get("result") or "")
    except ValueError:
        return None
    return reply if isinstance(reply, dict) else None


def call_agent(role, task, case_id, label, chosen, orch):
    from codex_files import Files
    Files(role, case_id)
    if role == "front" and not (orch.CASES / case_id).exists():
        created = orch.case().case_new(case_id)
        if created.get("error"):
            raise ValueError(created.get("detail", "could not create case"))
    folder = orch.CASES / case_id / "log" / "runs"
    folder.mkdir(parents=True, exist_ok=True)
    p = plan(role, case_id, label, chosen, orch)
    tries = []
    while True:
        with orch.NUMBERING:
            stem = folder / ("%03d-%s" % (orch.next_output_number(folder), label))
            stem.with_suffix(".jsonl").touch()
        out, err = stem.with_suffix(".jsonl"), stem.with_suffix(".err")
        with out.open("wb") as stdout, err.open("wb") as stderr:
            proc = subprocess.Popen(p["cmd"], cwd=p["work"], env=p["env"], stdin=subprocess.PIPE, stdout=stdout, stderr=stderr)
            timed_out = False
            try:
                proc.communicate((opening(p) + task).encode("utf-8"), timeout=chosen.get("timeout", orch.NODE_TIMEOUT))
            except subprocess.TimeoutExpired:
                timed_out = True
                orch.stop_tree(proc)
            except BaseException:
                orch.stop_tree(proc)
                raise
        for path in (out, err):
            path.write_text(harness.redact(path.read_text(encoding="utf-8", errors="replace")), encoding="utf-8")
        payload = parse_output(out.read_text(encoding="utf-8"))
        stderr = err.read_text(encoding="utf-8")
        failure = orch.classify(proc.returncode, timed_out, payload, stderr)
        tries.append(p["how"] + ("+schema" if p["schema"] else ""))
        if not timed_out and len(tries) < 4 and retry_plain(p, payload, failure, stderr):
            orch.say("%s: %s: the provider refused the output schema; going again without it" % (case_id, label))
            p = plan(role, case_id, label, {**chosen, "output_schemas": {}}, orch)
            continue
        if not timed_out and len(tries) < 4 and retry_fresh(p, payload, failure, stderr):
            orch.say("%s: %s: the %s session could not go on; starting a fresh one" % (case_id, label, p["how"]))
            forget(p["record"])
            p = plan(role, case_id, label, chosen, orch, fresh=True, schema=bool(p["schema"]))
            continue
        break
    settle(p, payload, failure, stderr)
    result = {"turns": payload["num_turns"], "session_id": payload.get("session_id") or p["sid"], "failure": failure,
              "detail": "timeout" if timed_out else (payload.get("result") or stderr[-500:]) if failure else "",
              "resumed": int(p["how"] != "fresh"), "backend": "codex", "model": chosen.get("model", "gpt-6-luna"),
              "usage": payload.get("usage", {}), "result": payload.get("result", ""), "reply": structured(p, payload)}
    orch.log_row(case_id, event="harness", node=label, agent=role, home=str(p["home"].relative_to(PROJECT)), session=p["how"],
                 tries=tries, **result)
    return result
