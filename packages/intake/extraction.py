"""Candidate-fact extraction with dictionary-contract validation.

The model proposes; the contract disposes. Any candidate outside the fact
dictionary is rejected (after one repair round), never silently coerced.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from packages.intake.prompting import (
    PROMPT_VERSION,
    build_repair_prompt,
    build_system_prompt,
    build_user_prompt,
    field_catalog,
)
from packages.model_adapter.client import ModelError, OpenAICompatibleClient


class ExtractionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ExtractionResult:
    facts: dict[str, Any]
    prompt_version: str = PROMPT_VERSION
    model: str = ""
    repair_rounds: int = 0
    warnings: tuple[str, ...] = ()


def validate_candidates(candidates: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Check candidates against the dictionary. Returns (accepted, errors)."""
    fields = {f["field_name"]: f for f in field_catalog()}
    accepted: dict[str, Any] = {}
    errors: list[str] = []

    for name, value in candidates.items():
        spec = fields.get(name)
        if spec is None:
            errors.append(f"字段 {name} 不在事实词典中，必须移除")
            continue
        if value is None or (isinstance(value, str) and not value.strip()):
            continue  # absent, not unknown
        dtype = spec["data_type"]
        if dtype == "enum":
            allowed = spec.get("enum_values", [])
            if value not in allowed:
                errors.append(f"字段 {name} 的值 {value!r} 不在允许值 {allowed} 中")
                continue
            accepted[name] = value
        elif dtype in ("integer", "decimal"):
            if isinstance(value, bool):
                errors.append(f"字段 {name} 需要数值，得到了布尔值")
                continue
            if isinstance(value, (int, float)):
                accepted[name] = value
            else:
                try:
                    accepted[name] = float(value) if dtype == "decimal" else int(value)
                except (TypeError, ValueError):
                    errors.append(f"字段 {name} 需要数值，得到了 {value!r}")
        else:
            # string / date / entity_ref / currency_code / list pass through;
            # deeper checks belong to the rule engine and expert review.
            accepted[name] = value
    return accepted, errors


def extract_facts(
    case_description: str,
    client: OpenAICompatibleClient | None = None,
    *,
    max_repairs: int = 1,
) -> ExtractionResult:
    client = client or OpenAICompatibleClient()
    system = build_system_prompt()
    user = build_user_prompt(case_description)

    raw = client.chat_json(system, user)
    accepted, errors = validate_candidates(raw)
    repairs = 0
    while errors and repairs < max_repairs:
        repairs += 1
        raw = client.chat_json(system, build_repair_prompt(case_description, errors))
        accepted, errors = validate_candidates(raw)
    if errors:
        raise ExtractionError(
            "候选事实未通过词典契约校验：" + "；".join(errors[:5])
        )
    return ExtractionResult(
        facts=accepted,
        model=client.config.model_name,
        repair_rounds=repairs,
    )
