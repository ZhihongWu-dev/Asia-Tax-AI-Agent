"""Native Codex CLI execution with private invocation homes and JSONL parsing."""
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

import harness
from make_agents import SERVERS
from make_codex import instruction

PROJECT = harness.PROJECT


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


def prepare(role, case_id, chosen, instructions=""):
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
        'web_search = ' + q("disabled" if role == "polish" else "live"),
        '[features]', 'shell_tool = false', 'view_image = false',
        'multi_agent = false', 'apps = false', 'plugins = false', 'remote_plugin = false', 'shell_snapshot = false',
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
                                          "--role", role, "--case", case_id, "--server", server]),
                   'cwd = ' + q(PROJECT), 'required = true',
                   'startup_timeout_sec = 120', 'tool_timeout_sec = 1200']
        for name in tool_names(server):
            config += ['[mcp_servers.' + q(server) + '.tools.' + q(name) + ']', 'approval_mode = "approve"']
    (folder / "config.toml").write_text("\n".join(config) + "\n", encoding="utf-8")
    env = harness.process_env("codex", folder, provider)
    return folder, work, env


def command(work):
    return [executable(), "--no-daemon", "exec", "--strict-config", "--ignore-rules", "--json", "--color", "never",
            "--skip-git-repo-check", "--cd", str(work), "-"]


def call_agent(role, task, case_id, label, chosen, orch):
    from codex_files import Files
    Files(role, case_id)
    if role == "front" and not (orch.CASES / case_id).exists():
        created = orch.case().case_new(case_id)
        if created.get("error"):
            raise ValueError(created.get("detail", "could not create case"))
    folder = orch.CASES / case_id / "log" / "runs"
    folder.mkdir(parents=True, exist_ok=True)
    with orch.NUMBERING:
        stem = folder / ("%03d-%s" % (orch.next_output_number(folder), label))
        stem.with_suffix(".jsonl").touch()
    out, err = stem.with_suffix(".jsonl"), stem.with_suffix(".err")
    home, work, env = prepare(role, case_id, chosen)
    with out.open("wb") as stdout, err.open("wb") as stderr:
        proc = subprocess.Popen(command(work), cwd=work, env=env, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr)
        timed_out = False
        try:
            proc.communicate(task.encode("utf-8"), timeout=chosen.get("timeout", orch.NODE_TIMEOUT))
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
    result = {"turns": payload["num_turns"], "session_id": payload.get("session_id"), "failure": failure,
              "detail": "timeout" if timed_out else (payload.get("result") or stderr[-500:]) if failure else "",
              "resumed": 0, "backend": "codex", "model": chosen.get("model", "gpt-6-luna"), "usage": payload.get("usage", {}),
              "result": payload.get("result", "")}
    orch.log_row(case_id, event="harness", node=label, agent=role, home=str(home.relative_to(PROJECT)), **result)
    return result
