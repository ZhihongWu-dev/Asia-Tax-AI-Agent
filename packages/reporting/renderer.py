"""Pure, deterministic Markdown rendering of L0 research reports.

Design rules (PRD s.3.4 / s.11.1):
- Every report carries the research watermark; there is no parameter to
  remove it.
- Chinese body, English legal-source names preserved.
- Every substantive element is traceable: rule version, execution batch,
  node outputs, blockers, and official sources.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence

RESEARCH_WATERMARK = (
    "【L0 内部研究原型】本报告由未经专业验证的候选规则自动生成，"
    "仅供内部研究与工程验证，不构成税务意见，不得用于客户案件。"
)

NODE_LABELS_ZH = {
    "human_gate": "专业验证闸门",
    "scope": "适用范围",
    "income_characterisation": "收入定性",
    "receipt": "在港收取",
    "financial_entity_exclusion": "金融实体排除",
    "economic_substance": "经济实质",
    "participation_basic": "参股条件（基础）",
    "foreign_tax_switchover": "境外税收转换",
    "anti_hybrid": "反混合错配",
    "main_purpose": "主要目的",
    "compliance_filing": "合规申报",
}

OUTPUT_LABELS_ZH = {
    "satisfied": "确立",
    "not_satisfied": "不确立",
    "unknown": "未知",
    "condition_not_demonstrated": "条件未能证明",
    "conflict": "冲突",
    "human_review_required": "需人工复核",
}

TERMINAL_LABELS_ZH = {
    "research_only_output": "研究性输出（仅供内部研究）",
    "human_review_required": "需人工复核",
    "stop_and_escalate": "停止并上报",
}

_NEXT_STEPS_ZH = {
    "research_only_output": (
        "本案未产生任何专业结论。请补充第 2 节所列证据缺口中的事实后重新运行；"
        "即使补齐事实，所有候选规则在专家验证前仍只可用于研究。"
    ),
    "human_review_required": (
        "本案已升级人工复核：判断链进入了需要专业判断的区域（如境外纳税资格、"
        "主要目的等），这些判断不能由机器作出。请合资格人士处理第 2 节所列事项。"
    ),
    "stop_and_escalate": (
        "检测到事实冲突，自动分析已停止。必须先解决冲突事实、重新确认事实卡，"
        "才可继续分析；冲突本身会被完整记录，不会被静默转换为否定答案。"
    ),
}


@dataclass(frozen=True)
class NodeRow:
    node: str
    ordinal: int
    rule_id: str | None
    output: str
    blockers: tuple[str, ...] = ()
    escalation_blockers: tuple[str, ...] = ()
    note: str | None = None
    source_ids: tuple[str, ...] = ()
    statute_locators: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReportInput:
    case_id: str
    case_description: str | None
    synthetic: bool
    execution_batch: str
    generated_at: str
    organization_name: str
    rule_set_version: str
    git_commit: str | None
    terminal_state: str
    run_blockers: tuple[str, ...] = ()
    conflict_fields: tuple[str, ...] = ()
    node_rows: tuple[NodeRow, ...] = ()
    source_catalog: Mapping[str, Mapping[str, str]] = field(default_factory=dict)
    statute_units: Mapping[str, str] = field(default_factory=dict)


def _zh_node(node: str) -> str:
    return NODE_LABELS_ZH.get(node, node)


def _zh_output(output: str) -> str:
    return OUTPUT_LABELS_ZH.get(output, output)


def _fmt_list(items: Sequence[str]) -> str:
    return "、".join(f"`{i}`" for i in items) if items else "无"


def render_markdown(report: ReportInput) -> str:
    terminal_zh = TERMINAL_LABELS_ZH.get(report.terminal_state, report.terminal_state)

    lines: list[str] = []
    lines.append(f"> ⚠️ {RESEARCH_WATERMARK}")
    lines.append("")
    lines.append("# 香港 FSIE 境外股息 — 内部研究分析稿")
    lines.append("")

    lines.append("## 1. 案件与运行信息")
    lines.append("")
    lines.append("| 项目 | 内容 |")
    lines.append("|---|---|")
    lines.append(f"| 案件编号 | `{report.case_id}` |")
    if report.case_description:
        lines.append(f"| 案件描述 | {report.case_description} |")
    lines.append(f"| 虚构案例标记 | {'是（合成数据，非真实客户案件）' if report.synthetic else '否'} |")
    lines.append(f"| 运行批次 | `{report.execution_batch}` |")
    lines.append(f"| 生成时间（以运行完成时间为准） | {report.generated_at} |")
    lines.append(f"| 运行组织 | {report.organization_name} |")
    lines.append(f"| 规则包版本 | `{report.rule_set_version}`（专业验证状态：unverified） |")
    lines.append(f"| 规则包 Git 提交 | `{report.git_commit or 'unknown'}` |")
    lines.append("")

    lines.append("## 2. 运行结论")
    lines.append("")
    lines.append(f"- **终态**：{terminal_zh}（`{report.terminal_state}`）")
    if report.terminal_state == "stop_and_escalate":
        lines.append(f"- **冲突事实**：{_fmt_list(report.conflict_fields)}")
        lines.append(f"- **上报阻断项**：{_fmt_list(report.run_blockers)}")
    elif report.terminal_state == "human_review_required":
        lines.append(f"- **需人工判断的事项**：{_fmt_list(report.run_blockers)}")
    else:
        lines.append(f"- **证据缺口（阻断项）**：{_fmt_list(report.run_blockers)}")
    lines.append("")

    lines.append("## 3. 判断链节点轨迹")
    lines.append("")
    lines.append("| 序号 | 节点 | 规则 | 结果 | 阻断/备注 |")
    lines.append("|---|---|---|---|---|")
    for row in sorted(report.node_rows, key=lambda r: (r.ordinal, r.node)):
        node_cell = f"{_zh_node(row.node)}（`{row.node}`）"
        rule_cell = f"`{row.rule_id}`" if row.rule_id else "—"
        output_cell = f"{_zh_output(row.output)}（`{row.output}`）"
        remarks: list[str] = []
        if row.blockers:
            remarks.append(f"阻断：{_fmt_list(row.blockers)}")
        if row.escalation_blockers:
            remarks.append(f"需人工判断：{_fmt_list(row.escalation_blockers)}")
        if row.note:
            remarks.append(row.note)
        lines.append(f"| {row.ordinal} | {node_cell} | {rule_cell} | {output_cell} | {'；'.join(remarks) or '—'} |")
    lines.append("")

    cited: list[tuple[str, str]] = []
    seen_locators: set[str] = set()
    for row in sorted(report.node_rows, key=lambda r: (r.ordinal, r.node)):
        for locator in row.statute_locators:
            if locator not in seen_locators and locator in report.statute_units:
                seen_locators.add(locator)
                cited.append((locator, report.statute_units[locator]))
    if cited:
        lines.append("## 4. 法条级依据（已切分法律单元，供核对原文）")
        lines.append("")
        lines.append("| 条文 | 法律单元节选（Cap. 112 现行版本） |")
        lines.append("|---|---|")
        for locator, snippet in cited:
            lines.append(f"| `{locator}` | {snippet[:160]}{'…' if len(snippet) > 160 else ''} |")
        lines.append("")

    used_source_ids = sorted({sid for row in report.node_rows for sid in row.source_ids})
    if used_source_ids:
        lines.append("## 5. 依据来源（候选规则映射，未经专家确认完整性）")
        lines.append("")
        lines.append("| 来源 | 标题 | 链接 |")
        lines.append("|---|---|---|")
        for sid in used_source_ids:
            meta = report.source_catalog.get(sid)
            if meta is None:
                lines.append(f"| `{sid}` | （未登记于 source manifest，须排查） | — |")
            else:
                url = meta.get("url") or meta.get("structured_data_url") or "—"
                lines.append(f"| `{sid}` | {meta.get('title', '—')} | {url} |")
        lines.append("")

    lines.append("## 6. 下一步")
    lines.append("")
    lines.append(f"- {_NEXT_STEPS_ZH.get(report.terminal_state, '按项目规程处理。')}")
    gate_rows = [r for r in report.node_rows if r.node == "human_gate"]
    if gate_rows:
        gate = gate_rows[0]
        lines.append(
            f"- 专业验证闸门：{_zh_output(gate.output)}。L0 阶段无香港税务专家，"
            "所有候选规则与案例结论均显示“待香港税务专家验证”。"
        )
    lines.append("- 本报告可按运行批次从数据库完整重建（同一数据库状态重渲染结果逐字节一致）。")
    lines.append("")

    lines.append("## 7. 责任与限制声明")
    lines.append("")
    lines.append("- 本报告基于候选规则（状态 `unverified`）生成，规则解释与阈值未经香港税务专家确认；")
    lines.append("- 报告不判断免税或应税，不替代专业意见，不得对外交付；")
    lines.append("- 最终专业判断由合资格人士负责（PRD 第 3、11 节）。")
    lines.append("")

    return "\n".join(lines)
