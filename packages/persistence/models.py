"""L0 first-slice relational model — a mechanical translation of the contract.

Only the tables needed to walk the single dividend vertical slice are declared
here; interview, RAG passage, report and user/role tables are added by later
migrations when the slice needs them.

Design rules:
- Business/runtime tables carry ``organization_id`` from day one (roadmap s.5).
- Uncertain state is a controlled enum enforced by a CHECK constraint; the
  allowed values are imported from packages.contracts.enums, never retyped.
- A fact's business value (JSONB) is kept separate from its confirmation status.
- Knowledge definitions (rule sets/nodes, evaluation cases) are global and are
  not owned by an organization; runtime records are.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Sequence

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from packages.contracts.enums import (
    CaseStatus,
    CaseTerminalState,
    FactConfirmationStatus,
    JUDGEMENT_CHAIN,
    LifecycleStatus,
    NodeOutputStatus,
    ProfessionalValidationStatus,
    values,
)
from packages.persistence.base import Base, TimestampMixin

# Deterministic ordering so generated migrations are stable.
NODE_KEYS = sorted(JUDGEMENT_CHAIN.keys())


def _in_list(column: str, allowed: Sequence[str]) -> str:
    rendered = ", ".join(f"'{v}'" for v in sorted(allowed))
    return f"{column} IN ({rendered})"


def _enum_values(enum_cls: type) -> list[str]:
    return sorted(values(enum_cls))


# ---------------------------------------------------------------------------
# Knowledge layer (global, versioned, sourced from the Git knowledge package)
# ---------------------------------------------------------------------------


class RuleSet(Base, TimestampMixin):
    __tablename__ = "rule_sets"
    __table_args__ = (
        UniqueConstraint("jurisdiction", "package", "version", name="uq_rule_set_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    jurisdiction: Mapped[str] = mapped_column(String(8), nullable=False)
    package: Mapped[str] = mapped_column(String(32), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    git_commit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    professional_validation_status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="unverified"
    )
    lifecycle_status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="candidate"
    )


class RuleNode(Base, TimestampMixin):
    __tablename__ = "rule_nodes"
    __table_args__ = (
        UniqueConstraint("rule_set_id", "rule_id", name="uq_rule_node_in_set"),
        CheckConstraint(_in_list("node", NODE_KEYS), name="ck_rule_node_node"),
        CheckConstraint(
            _in_list("status", _enum_values(ProfessionalValidationStatus)),
            name="ck_rule_node_status",
        ),
        CheckConstraint("ordinal BETWEEN 0 AND 10", name="ck_rule_node_ordinal"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rule_set_id: Mapped[int] = mapped_column(
        ForeignKey("rule_sets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_id: Mapped[str] = mapped_column(String(32), nullable=False)
    node: Mapped[str] = mapped_column(String(48), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    purpose: Mapped[str | None] = mapped_column(String, nullable=True)
    required_facts: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    required_evidence: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    depends_on_nodes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    source_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    thresholds: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    outputs: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    human_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    effective_from: Mapped[str | None] = mapped_column(String(16), nullable=True)
    effective_to: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="unverified")


class EvaluationCase(Base, TimestampMixin):
    __tablename__ = "evaluation_cases"
    __table_args__ = (
        UniqueConstraint("case_id", name="uq_evaluation_case_logical_id"),
        CheckConstraint("synthetic = TRUE", name="ck_evaluation_case_synthetic"),
        CheckConstraint(
            _in_list("expected_state", _enum_values(CaseTerminalState)),
            name="ck_evaluation_case_state",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_version: Mapped[str] = mapped_column(String(32), nullable=False)
    case_id: Mapped[str] = mapped_column(String(32), nullable=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    facts: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    expected_state: Mapped[str] = mapped_column(String(48), nullable=False)
    expected_blockers: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    scenario_tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    applicable_date: Mapped[str | None] = mapped_column(String(16), nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)


# ---------------------------------------------------------------------------
# Organization + runtime layer (all business rows belong to an organization)
# ---------------------------------------------------------------------------


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="active")


class CaseFile(Base, TimestampMixin):
    __tablename__ = "cases"
    __table_args__ = (
        CheckConstraint(_in_list("case_status", _enum_values(CaseStatus)), name="ck_case_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    jurisdiction: Mapped[str] = mapped_column(String(8), nullable=False)
    package: Mapped[str] = mapped_column(String(32), nullable=False)
    external_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    case_status: Mapped[str] = mapped_column(String(48), nullable=False, server_default="draft")
    release_level: Mapped[str] = mapped_column(String(4), nullable=False, server_default="L0")
    applicable_date: Mapped[str | None] = mapped_column(String(16), nullable=True)


class Fact(Base, TimestampMixin):
    __tablename__ = "facts"
    __table_args__ = (
        UniqueConstraint("case_id", "field_name", name="uq_fact_case_field"),
        CheckConstraint(
            _in_list("confirmation_status", _enum_values(FactConfirmationStatus)),
            name="ck_fact_confirmation",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[int] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    income_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    field_name: Mapped[str] = mapped_column(String(96), nullable=False)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    confirmation_status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="unknown"
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_quote: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_by: Mapped[str] = mapped_column(String(64), nullable=False, server_default="system")


class FactVersion(Base):
    __tablename__ = "fact_versions"
    __table_args__ = (
        UniqueConstraint("fact_id", "version_no", name="uq_fact_version"),
        CheckConstraint(
            _in_list("confirmation_status", _enum_values(FactConfirmationStatus)),
            name="ck_fact_version_confirmation",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fact_id: Mapped[int] = mapped_column(
        ForeignKey("facts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    confirmation_status: Mapped[str] = mapped_column(String(32), nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_quote: Mapped[str | None] = mapped_column(String, nullable=True)
    updated_by: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RuleExecution(Base):
    __tablename__ = "rule_executions"
    __table_args__ = (
        CheckConstraint(_in_list("node", NODE_KEYS), name="ck_rule_exec_node"),
        CheckConstraint(
            _in_list("output", _enum_values(NodeOutputStatus)), name="ck_rule_exec_output"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[int | None] = mapped_column(
        ForeignKey("cases.id", ondelete="CASCADE"), nullable=True, index=True
    )
    rule_set_id: Mapped[int] = mapped_column(
        ForeignKey("rule_sets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_node_id: Mapped[int | None] = mapped_column(
        ForeignKey("rule_nodes.id", ondelete="SET NULL"), nullable=True
    )
    execution_batch: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    node: Mapped[str] = mapped_column(String(48), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    output: Mapped[str] = mapped_column(String(48), nullable=False)
    inputs_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    blockers: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    __table_args__ = (
        CheckConstraint(
            _in_list("terminal_state", _enum_values(CaseTerminalState)),
            name="ck_eval_run_state",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_set_id: Mapped[int] = mapped_column(
        ForeignKey("rule_sets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evaluation_case_id: Mapped[int] = mapped_column(
        ForeignKey("evaluation_cases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    terminal_state: Mapped[str | None] = mapped_column(String(48), nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"
    __table_args__ = (
        CheckConstraint(_in_list("node", NODE_KEYS), name="ck_eval_result_node"),
        CheckConstraint(
            _in_list("output", _enum_values(NodeOutputStatus)), name="ck_eval_result_output"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evaluation_run_id: Mapped[int] = mapped_column(
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    case_id: Mapped[str] = mapped_column(String(32), nullable=False)
    node: Mapped[str] = mapped_column(String(48), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    output: Mapped[str] = mapped_column(String(48), nullable=False)
    blockers: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AuditEvent(Base):
    """Append-only audit log; ordinary business code never updates/deletes rows."""

    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# Knowledge pipeline layer (S5): official sources and their legal units
# ---------------------------------------------------------------------------

PARSE_STATUSES = ("registered", "snapshotted", "parsed", "failed", "out_of_scope")
UNIT_TYPES = (
    "subsection",
    "section",
    "guidance_block",
    "faq_item",
    "example",
    "ruling_block",
    "pdf_page",
)


class Source(Base, TimestampMixin):
    """A row of the versioned source manifest, mirrored into the DB with
    pipeline state (snapshot location, parse status, drift detection)."""

    __tablename__ = "sources"
    __table_args__ = (
        CheckConstraint(_in_list("parse_status", PARSE_STATUSES), name="ck_source_parse_status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    publisher: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    structured_data_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    jurisdiction: Mapped[str] = mapped_column(String(8), nullable=False, server_default="HK")
    language: Mapped[str] = mapped_column(String(8), nullable=False, server_default="en")
    manifest_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actual_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    snapshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    l0_in_scope: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    parse_status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="registered")
    units_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    professional_validation_status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="unverified"
    )


class LegalUnit(Base):
    """The smallest citable slice of an official source (a subsection, a FAQ
    item, a guidance block). Reports must be able to jump from a citation to
    the unit and back to the source snapshot."""

    __tablename__ = "legal_units"
    __table_args__ = (
        UniqueConstraint("source_db_id", "unit_ref", name="uq_legal_unit_ref"),
        CheckConstraint(_in_list("unit_type", UNIT_TYPES), name="ck_legal_unit_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_db_id: Mapped[int] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True
    )
    unit_ref: Mapped[str] = mapped_column(String(128), nullable=False)
    statute_locator: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    unit_type: Mapped[str] = mapped_column(String(32), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    heading: Mapped[str | None] = mapped_column(String(512), nullable=True)
    text: Mapped[str] = mapped_column(String, nullable=False)
    text_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False, server_default="en")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
