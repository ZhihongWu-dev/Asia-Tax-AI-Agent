"""Generate Codex role instructions from the same English specifications as Claude."""
from pathlib import Path
from make_agents import PROJECT, SPECS, SAVE_TOOLS, SAVING, prompt_of

BRIDGE = """You run in the native Codex CLI as the {role} case agent.
The business specification below is shared with the Claude harness. Tool translation:
Read -> tax-files.read_file; Glob -> tax-files.list_files; Grep -> tax-files.search.
Paths in those tools are relative to the project, including cases/<case_id>/....
Use tax-read for retrieval and parsed document pages, tax-rule for rule evaluation,
tax-opt for calculations, and your tax-case server for all writes. An instruction
to call a tool means an actual MCP tool invocation, never tool syntax in prose.
Read images with tax-files.read_image where your role permits. There is no shell.
The host starts the orchestrator. Front returns [[START_RUN]] when intake is ready;
it must not launch or imitate an optimizer or orchestration command itself.
Do not use built-in subagents; the host gives each node a fresh isolated CLI session.
AI-authored working papers, reports and logs are English; client replies follow
the client's language. Quotes retain their original language.
"""


def instruction(role):
    return BRIDGE.format(role=role) + "\n" + prompt_of(role) + "\n\n" + SAVING % SAVE_TOOLS[role] + "\n"


def generate():
    out = PROJECT / ".codex" / "agents"
    out.mkdir(parents=True, exist_ok=True)
    for role in SPECS:
        text = instruction(role)
        (out / (role + ".md")).write_text(text, encoding="utf-8")
    return out


if __name__ == "__main__":
    print("Generated:", generate())
