"""Pytest bootstrap: ensure the repository root is importable."""

import sys
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def isolated_agent_logs(monkeypatch):
    # Offline tests never mix their diagnostics into the developer's real runs.
    monkeypatch.setenv('FSIE_AGENT_LOG_DIR', 'off')
    # Unit API tests use injected providers, not a live library subprocess.
    monkeypatch.setenv('FSIE_AGENT_PROVIDER', 'legacy')
    monkeypatch.setenv('FSIE_ACTIVE_WORKFLOW', 'legacy')
