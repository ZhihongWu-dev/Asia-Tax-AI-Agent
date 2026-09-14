"""The renderer is pure, deterministic, and the watermark is non-negotiable."""

from __future__ import annotations

import pytest

from packages.reporting.renderer import (
    RESEARCH_WATERMARK,
    NodeRow,
    ReportInput,
    render_markdown,
)

CATALOG = {
    "hk_ird_fsie_landing": {"source_id": "hk_ird_fsie_landing", "title": "FSIE landing", "url": "https://www.ird.gov.hk/eng/tax/bus_fsie.htm"},
}


def _rows() -> tuple[NodeRow, ...]:
    return (
        NodeRow("human_gate", 0, "FSIE-GATE-001", "human_review_required",
                blockers=("expert_decision_status",), source_ids=("hk_ird_fsie_landing",)),
        NodeRow("scope", 1, "FSIE-SCOPE-001", "unknown",
                blockers=("mne_group_status",), source_ids=("hk_ird_fsie_landing",)),
        NodeRow("income_characterisation", 2, "FSIE-INCOME-001", "satisfied"),
        NodeRow("receipt", 3, "FSIE-RECEIPT-001", "unknown", blockers=("receipt_location",)),
        NodeRow("economic_substance", 5, "FSIE-ES-001", "unknown", blockers=("hk_adequate_employees",)),
        NodeRow("participation_basic", 6, "FSIE-PART-001", "unknown",
                blockers=("foreign_tax_on_dividend_or_underlying_profit",)),
    )


def _report(terminal: str, blockers: tuple[str, ...], conflicts: tuple[str, ...] = ()) -> ReportInput:
    return ReportInput(
        case_id="SYN-FSIE-001",
        case_description="A fictional case.",
        synthetic=True,
        execution_batch="SYN-FSIE-001:abc123",
        generated_at="2026-09-03T12:00:00+00:00",
        organization_name="L0 Research Organisation",
        rule_set_version="0.2.0",
        git_commit="7bd436c",
        terminal_state=terminal,
        run_blockers=blockers,
        conflict_fields=conflicts,
        node_rows=_rows(),
        source_catalog=CATALOG,
    )


@pytest.mark.parametrize("terminal,blockers", [
    ("research_only_output", ("mne_group_status", "receipt_location")),
    ("human_review_required", ("foreign_tax_on_dividend_or_underlying_profit",)),
    ("stop_and_escalate", ("receipt_location",)),
])
def test_watermark_is_always_present(terminal, blockers):
    conflicts = ("receipt_location",) if terminal == "stop_and_escalate" else ()
    text = render_markdown(_report(terminal, blockers, conflicts))
    assert RESEARCH_WATERMARK in text
    assert "不构成税务意见" in text


def test_render_is_deterministic():
    report = _report("research_only_output", ("mne_group_status",))
    assert render_markdown(report) == render_markdown(report)


def test_node_trace_lists_all_six_nodes_in_ordinal_order():
    text = render_markdown(_report("research_only_output", ("mne_group_status",)))
    positions = [text.index(f"| {o} |") for o in (0, 1, 2, 3, 5, 6)]
    assert positions == sorted(positions)
    assert "适用范围（`scope`）" in text
    assert "专业验证闸门（`human_gate`）" in text


def test_run_metadata_is_traceable():
    text = render_markdown(_report("research_only_output", ("mne_group_status",)))
    for needle in ("`0.2.0`", "`7bd436c`", "`SYN-FSIE-001:abc123`", "unverified"):
        assert needle in text


def test_human_review_report_lists_judgement_items():
    text = render_markdown(_report("human_review_required", ("main_purpose_tax_benefit_flag",)))
    assert "需人工复核" in text
    assert "`main_purpose_tax_benefit_flag`" in text
    assert "升级人工复核" in text


def test_escalation_report_names_the_conflict():
    text = render_markdown(_report("stop_and_escalate", ("receipt_location",), ("receipt_location",)))
    assert "停止并上报" in text
    assert "`receipt_location`" in text
    assert "冲突" in text


def test_sources_are_deduplicated_and_linked():
    text = render_markdown(_report("research_only_output", ("mne_group_status",)))
    assert text.count("`hk_ird_fsie_landing` | FSIE landing") == 1
    assert "https://www.ird.gov.hk/eng/tax/bus_fsie.htm" in text


def test_unknown_source_id_is_flagged_not_silenced():
    rows = _rows() + (NodeRow("scope", 99, None, "unknown", source_ids=("ghost_source",)),)
    report = _report("research_only_output", ("mne_group_status",))
    report = ReportInput(**{**report.__dict__, "node_rows": rows})
    text = render_markdown(report)
    assert "未登记于 source manifest" in text
