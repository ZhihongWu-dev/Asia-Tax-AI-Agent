"""Pure, database-free parsing of the Git-versioned FSIE knowledge package.

Keeping file IO and shaping separate from ORM persistence makes the loader
unit-testable without a live database.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
FSIE_DIR = REPO_ROOT / "knowledge" / "hong_kong" / "fsie"
RULES_PATH = FSIE_DIR / "rules.json"
CASES_PATH = REPO_ROOT / "tests" / "fsie" / "candidate_cases.json"
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_fsie_package.py"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_rules_payload() -> dict[str, Any]:
    return _read_json(RULES_PATH)


def load_cases_payload() -> dict[str, Any]:
    return _read_json(CASES_PATH)


def current_git_commit() -> str | None:
    """Best-effort short HEAD commit for provenance; None if unavailable."""
    try:
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return None
