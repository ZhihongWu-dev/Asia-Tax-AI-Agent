"""Assemble a ReportInput directly from a RunOutcome (no DB round-trip).

Used by the natural-language intake flow; the evaluation flow rebuilds
reports from persisted runs instead (see reporting.cli).
"""

from __future__ import annotations

from datetime import datetime, timezone

from packages.reporting.cli import source_catalog
from packages.reporting.renderer import NodeRow, ReportInput
from packages.rule_engine.runner import RunOutcome


def report_input_from_outcome(
    outcome: RunOutcome,
    *,
    case_description: str | None,
    execution_batch: str,
    organization_name: str,
    rule_set_version: str,
    git_commit: str | None,
    rule_nodes_meta: dict[str, tuple[str, tuple[str, ...], tuple[str, ...]]],
    statute_units: dict[str, str] | None = None,
    generated_at: datetime | None = None,
) -> ReportInput:
    empty = (None, (), ())
    node_rows = tuple(
        NodeRow(
            node=o.node,
            ordinal=o.ordinal,
            rule_id=rule_nodes_meta.get(o.node, empty)[0],
            output=o.output,
            blockers=o.blockers,
            escalation_blockers=o.escalation_blockers,
            note=o.detail.get("note") if isinstance(o.detail, dict) else None,
            source_ids=rule_nodes_meta.get(o.node, empty)[1],
            statute_locators=rule_nodes_meta.get(o.node, empty)[2],
        )
        for o in outcome.node_outcomes
    )
    return ReportInput(
        case_id=outcome.case_id,
        case_description=case_description,
        synthetic=True,
        execution_batch=execution_batch,
        generated_at=(generated_at or datetime.now(timezone.utc)).isoformat(),
        organization_name=organization_name,
        rule_set_version=rule_set_version,
        git_commit=git_commit,
        terminal_state=outcome.terminal_state,
        run_blockers=outcome.blockers,
        conflict_fields=outcome.conflict_fields,
        node_rows=node_rows,
        source_catalog=source_catalog(),
        statute_units=statute_units or {},
    )
