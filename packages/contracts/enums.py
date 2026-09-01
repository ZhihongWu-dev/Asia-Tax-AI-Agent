"""Shared contract enums for the Asia Tax AI Agent.

This module is the Python-side mirror of
``packages/contracts/json_schemas/definitions.schema.json``. The JSON Schema is
the authoritative source for structure; these constants let application code,
migrations and scripts avoid magic strings. ``scripts/validate_fsie_package.py``
cross-checks the two and fails if they drift apart.

Zero third-party dependencies.
"""

from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    """String enum whose members compare/serialize as plain strings."""

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


class ReleaseLevel(StrEnum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"


class LifecycleStatus(StrEnum):
    DISCOVERED = "discovered"
    CAPTURED = "captured"
    PARSED = "parsed"
    CANDIDATE = "candidate"
    MACHINE_CHECKED = "machine_checked"
    HUMAN_REVIEW = "human_review"
    VERIFIED = "verified"
    ACTIVE = "active"
    REJECTED = "rejected"
    STALE = "stale"
    POTENTIALLY_STALE = "potentially_stale"
    BLOCKED = "blocked"


class ProfessionalValidationStatus(StrEnum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    REJECTED = "rejected"


class FactConfirmationStatus(StrEnum):
    CLIENT_STATEMENT = "client_statement"
    AI_CANDIDATE = "ai_candidate"
    ADVISOR_CONFIRMED = "advisor_confirmed"
    EXTERNALLY_EVIDENCED = "externally_evidenced"
    ASSUMED = "assumed"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"


# Values allowed inside a candidate case's inline facts map when no business
# value is asserted.
class InlineFactSentinel(StrEnum):
    UNKNOWN = "unknown"
    CONFLICT = "conflict"
    ASSUMED = "assumed"
    NOT_APPLICABLE = "not_applicable"


class NodeOutputStatus(StrEnum):
    SATISFIED = "satisfied"
    NOT_SATISFIED = "not_satisfied"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"
    CONDITION_NOT_DEMONSTRATED = "condition_not_demonstrated"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class CaseTerminalState(StrEnum):
    RESEARCH_ONLY_OUTPUT = "research_only_output"
    STOP_AND_ESCALATE = "stop_and_escalate"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class EvidenceStatus(StrEnum):
    PROVIDED = "provided"
    MISSING = "missing"
    CONFLICT = "conflict"
    NOT_APPLICABLE = "not_applicable"


class BlockingLevel(StrEnum):
    SCOPE_BLOCKING = "scope_blocking"
    CONCLUSION_BLOCKING = "conclusion_blocking"
    SUPPORTING = "supporting"


class CaseStatus(StrEnum):
    DRAFT = "draft"
    INTERVIEWING = "interviewing"
    WAITING_CLIENT_EVIDENCE = "waiting_client_evidence"
    WAITING_FACT_CONFIRMATION = "waiting_fact_confirmation"
    ANALYZING = "analyzing"
    NEEDS_HUMAN_JUDGMENT = "needs_human_judgment"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    INVALIDATED = "invalidated"
    ARCHIVED = "archived"


class FactDomain(StrEnum):
    ENTITY_AND_GROUP = "entity_and_group"
    DIVIDEND_IDENTITY = "dividend_identity"
    RECEIPT_PATH = "receipt_path"
    PARTICIPATION_HOLDING = "participation_holding"
    FOREIGN_TAXATION = "foreign_taxation"
    HK_ECONOMIC_SUBSTANCE = "hk_economic_substance"
    COMMERCIAL_PURPOSE_ANTI_ABUSE = "commercial_purpose_anti_abuse"
    EVIDENCE_DOCUMENTS = "evidence_documents"


class FactDataType(StrEnum):
    ENUM = "enum"
    STRING = "string"
    DECIMAL = "decimal"
    INTEGER = "integer"
    DATE = "date"
    BOOLEAN = "boolean"
    ENTITY_REF = "entity_ref"
    CURRENCY_CODE = "currency_code"
    LIST = "list"


# Canonical ten-step judgement chain (PRD s.5.2). Ordinal 0 is the
# cross-cutting human gate, which is not a sequential step.
JUDGEMENT_CHAIN: dict[str, int] = {
    "scope": 1,
    "income_characterisation": 2,
    "receipt": 3,
    "financial_entity_exclusion": 4,
    "economic_substance": 5,
    "participation_basic": 6,
    "foreign_tax_switchover": 7,
    "anti_hybrid": 8,
    "main_purpose": 9,
    "compliance_filing": 10,
    "human_gate": 0,
}


def values(enum_cls: type[Enum]) -> set[str]:
    """Return the set of string values for an enum class."""
    return {member.value for member in enum_cls}
