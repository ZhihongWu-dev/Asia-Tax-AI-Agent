"""CLI selection and credential isolation shared by the optional Codex entry point."""
import json
import os
import re
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
ROLES = ("front", "analysis", "review")          # 2026-11-06: no polish role
SECRET = re.compile(r"(?i)(key|token|secret|password|credential|authorization)")


def settings(path=None, overrides=()):
    path = Path(path or PROJECT / "agent" / "harness.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    for override in overrides:
        node, value = override.split("=", 1)
        backend, _, model = value.partition(":")
        data.setdefault("nodes", {})[node] = {"backend": backend, **({"model": model} if model else {})}
    for item in [data.get("default", {}), *data.get("nodes", {}).values()]:
        if item.get("backend", "claude") not in ("claude", "codex"):
            raise ValueError("backend must be claude or codex")
    return data


def selection(data, role, node=""):
    chosen = dict(data.get("default", {}))
    for layer in (data.get("nodes", {}).get(role, {}), data.get("nodes", {}).get(node, {})):
        if "backend" in layer and layer["backend"] != chosen.get("backend", "claude"):
            chosen = {"backend": layer["backend"]}
        chosen.update(layer)
    if chosen.get("backend", "claude") == "codex":
        chosen = {**data.get("codex", {}), **chosen}
    return chosen


def dotenv(path):
    values = {}
    if Path(path).exists():
        for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip().strip("\"'")
    return values


def openai_key():
    key = os.environ.get("OPENAI_API_KEY") or dotenv(PROJECT / ".env.codex").get("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY is required in the environment or ignored .env.codex")
    return key


def process_env(backend, home=None, provider=None):
    # Keep OS/runtime settings, but do not inherit another harness's identity or credentials.
    env = {k: v for k, v in os.environ.items()
           if not SECRET.search(k) and k.lower() != "gpt"
           and not k.upper().startswith(("ANTHROPIC_", "OPENAI_", "QWEN_", "GPT_", "CLAUDE_", "CODEX_"))}
    env.update(LANGSMITH_TRACING="false", PYTHONIOENCODING="utf-8", HF_HUB_OFFLINE="1", TQDM_DISABLE="1")
    if backend == "codex":
        env["CODEX_HOME"] = str(home)
        if provider and provider.get("key_from"):                  # another OpenAI-compatible provider gets only its own key
            key = dotenv(PROJECT / ".env").get(provider["key_from"])
            if not key:
                raise ValueError("%s is required in .env for the provider at %s" % (provider["key_from"], provider.get("base_url")))
            env[provider.get("env_key", "OPENAI_API_KEY")] = key
        else:
            env["OPENAI_API_KEY"] = openai_key()
    return env


def secrets():
    values = [v for k, v in os.environ.items() if SECRET.search(k)]
    for name in (".env", ".env.codex"):
        values.extend(v for k, v in dotenv(PROJECT / name).items() if SECRET.search(k) or k == "gpt")
    return [v for v in values if len(v) >= 12]


def redact(text):
    for value in secrets():
        text = text.replace(value, "<redacted>")
    return text
