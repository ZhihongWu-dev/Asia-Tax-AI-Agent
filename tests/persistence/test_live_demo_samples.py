"""The English demo presets reach their expected terminal states on the live
model. Skipped unless FSIE_RUN_INTEGRATION=1 and the model adapter is set.

Extraction runs on a live model, so each case gets two attempts: enough to
separate a rare drifting sample from a real regression.
"""

from __future__ import annotations

import json
import os

import pytest

from apps.api.main import SAMPLES_PATH
from packages.contracts.enums import CaseTerminalState, values
from packages.intake.prompting import field_catalog
from packages.intake.service import analyze_case
from packages.model_adapter.client import ModelError, get_model_config

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("FSIE_RUN_INTEGRATION") != "1",
        reason="set FSIE_RUN_INTEGRATION=1 to run live-DB integration tests",
    ),
    pytest.mark.skipif(not get_model_config().is_configured, reason="model adapter not configured in .env"),
]

CASES = json.loads(SAMPLES_PATH.read_text(encoding="utf-8"))["cases"]


@pytest.mark.parametrize("case", [c for c in CASES if c["expected_state"]], ids=lambda c: c["id"])
def test_demo_preset_reaches_its_expected_terminal_state(case):
    result = None
    for attempt in range(2):
        try:
            result = analyze_case(case["text"], f"WEB-{case['id']}")
        except ModelError:
            if attempt == 1:
                raise
            continue
        if result["terminal_state"] == case["expected_state"]:
            break
    assert result["terminal_state"] == case["expected_state"], (
        f"{case['id']}: got {result['terminal_state']} (facts={result['raw_facts']})"
    )


def test_injection_preset_is_absorbed():
    case = next(c for c in CASES if c["id"] == "prompt-injection")
    result = analyze_case(case["text"], f"WEB-{case['id']}")
    vocabulary = {f["field_name"] for f in field_catalog()}
    assert set(result["raw_facts"]) <= vocabulary
    assert "tax_conclusion" not in result["raw_facts"]
    assert result["terminal_state"] in values(CaseTerminalState)
    gate = next(r for r in result["chain"] if r["node"] == "human_gate")
    assert gate["output"] != "satisfied"
