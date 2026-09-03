"""Prompt construction for candidate-fact extraction (dictionary-anchored)."""

from __future__ import annotations

import json
from typing import Any

from packages.knowledge_loader import parser as knowledge_parser

PROMPT_VERSION = "intake-v1"

_DICTIONARY_CACHE: dict[str, Any] | None = None


def _dictionary() -> dict[str, Any]:
    global _DICTIONARY_CACHE
    if _DICTIONARY_CACHE is None:
        path = (
            knowledge_parser.REPO_ROOT
            / "packages/contracts/fact_dictionary/hk_fsie_fact_fields.v0.json"
        )
        _DICTIONARY_CACHE = json.loads(path.read_text(encoding="utf-8"))
    return _DICTIONARY_CACHE


def field_catalog() -> list[dict[str, Any]]:
    return _dictionary()["fields"]


def build_system_prompt() -> str:
    return (
        "你是香港 FSIE 研究的候选事实提取器，服务于 L0 内部研究原型。\n"
        "任务：从用户给出的虚构案件描述中，提取与给定字段词典匹配的事实。\n"
        "严格规则：\n"
        "1. 只输出一个 JSON 对象，键必须是字段词典中出现的 field_name，禁止自造字段；\n"
        "2. 只提取描述中明确给出、或明确声明“未知/不清楚”的事实；不要猜测、不要用常识补全；\n"
        "3. 描述中明确说“未知、不清楚、尚未确认”的字段，值写 \"unknown\"；\n"
        "4. 描述中自相矛盾的字段，值写 \"conflict\"；\n"
        "5. enum 类型字段的值必须取自该字段的 enum_values；数值字段输出数字；日期用 ISO 格式字符串；\n"
        "6. 没有提到的字段不要出现在输出里；\n"
        "7. 不输出 JSON 以外的任何文字。\n"
        "你的输出只是候选事实（ai_candidate），将由确定性规则与人工复核处理，不会直接成为税务结论。"
    )


def build_user_prompt(case_description: str) -> str:
    catalog_lines = []
    for f in field_catalog():
        enum_part = ""
        if f.get("enum_values"):
            enum_part = "；允许值: " + "/".join(f["enum_values"])
        catalog_lines.append(
            f"- {f['field_name']} ({f['data_type']}{enum_part})：{f.get('description_zh', '')}"
        )
    return (
        "字段词典（共 %d 个字段）：\n%s\n\n"
        "案件描述（虚构，仅供研究）：\n\"\"\"\n%s\n\"\"\"\n\n"
        "请输出候选事实 JSON。"
    ) % (len(catalog_lines), "\n".join(catalog_lines), case_description.strip())


def build_repair_prompt(case_description: str, errors: list[str]) -> str:
    return (
        build_user_prompt(case_description)
        + "\n\n你上一次的输出存在以下问题，请纠正后重新输出完整 JSON：\n"
        + "\n".join(f"- {e}" for e in errors)
    )
