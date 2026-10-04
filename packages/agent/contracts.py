"""Versioned C boundary. Unknown permissions fail closed."""
from __future__ import annotations

from datetime import date
from typing import Literal, Protocol
from pydantic import BaseModel, ConfigDict, Field, model_validator

Permission = Literal['allowed', 'denied', 'unknown']


class Contract(BaseModel):
    model_config = ConfigDict(extra='forbid')


class TrustedContext(Contract):
    owner: str = Field(min_length=1)
    case_id: str | None = None


class Reference(Contract):
    evidence_id: str
    source_version_id: str
    unit_id: str


class FactFilter(Contract):
    field_name: Literal['income_type', 'source_analysis', 'entity_hk_business_status', 'receipt_location', 'recipient_type']
    value: str


class SearchRequest(Contract):
    schema_version: Literal['0.1.0'] = '0.1.0'
    request_id: str
    trace_id: str
    query: str = Field(min_length=2, max_length=500)
    intent: Literal['concept', 'reference_lookup', 'case_analysis'] = 'reference_lookup'
    jurisdiction: str | None = 'HK'
    topic: str | None = 'dividend'
    income_type: str | None = None
    entity_type: Literal['company', 'individual', 'unknown', 'not_needed'] = 'not_needed'
    applicable_date: date | None = None
    date_status: Literal['actual', 'planned', 'unknown', 'not_needed'] = 'not_needed'
    reference_number: str | None = None
    fact_filters: list[FactFilter] = Field(default_factory=list, max_length=20)
    language: str = 'zh'
    limit: int = Field(default=7, ge=1, le=7)
    deadline_ms: int = Field(default=3000, ge=1, le=10000)
    # v0.1 compatible optional extensions used by A's search and rules panels.
    kind: Literal['all', 'law', 'ruling', 'guidance'] = 'all'
    locators: list[str] = Field(default_factory=list, max_length=50)

    @model_validator(mode='after')
    def dates(self):
        if (self.date_status in ('actual', 'planned')) != (self.applicable_date is not None):
            raise ValueError('Date and date_status disagree')
        return self


class Evidence(Contract):
    evidence_id: str
    source_version_id: str
    unit_id: str
    source_id: str
    content_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    is_synthetic: bool = False
    title: str
    publisher: str = ''
    source_type: str
    language: str = 'zh'
    url: str | None = None
    locator: str | None = None
    jurisdiction: str | None = None
    topic: str | None = None
    publication_date: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    verification_status: Literal['verified', 'unverified'] = 'unverified'
    drift: bool = False
    heading: str | None = None
    retrieved_at: str | None = None
    coverage_cutoff: str | None = None
    snapshot_sha256: str | None = None
    model_use: Permission = 'unknown'
    display_use: Permission = 'unknown'
    policy_version: str = Field(min_length=1)
    restriction_reason: str | None = None
    model_text: str | None = Field(default=None, max_length=30000)
    display_ref: Reference | None = None

    @model_validator(mode='after')
    def boundary(self):
        if self.model_use != 'allowed' and self.model_text is not None:
            raise ValueError('Unauthorized model text')
        if self.display_use != 'allowed' and self.display_ref is not None:
            raise ValueError('Unauthorized display reference')
        if self.display_ref and self.display_ref != self.reference():
            raise ValueError('Mismatched reference')
        if self.effective_from and self.effective_to and self.effective_from > self.effective_to:
            raise ValueError('Invalid effective interval')
        return self

    def reference(self):
        return Reference(evidence_id=self.evidence_id, source_version_id=self.source_version_id, unit_id=self.unit_id)


class Coverage(Contract):
    status: Literal['unchecked', 'partial', 'sufficient_for_task', 'not_assessed'] = 'not_assessed'
    scope: str = ''
    missing_requirements: list[str] = Field(default_factory=list)
    truncated: bool = False


class ProviderError(Contract):
    code: str
    message: str
    retryable: bool


class Timings(Contract):
    db: float | None = None
    retrieval: float | None = None
    rerank: float | None = None
    total: float | None = None


class SearchResult(Contract):
    schema_version: Literal['0.1.0'] = '0.1.0'
    request_id: str
    trace_id: str
    retrieval_id: str
    provider: Literal['mock', 'c', 'legacy']
    is_synthetic: bool
    corpus_version: str
    status: Literal['ok', 'partial', 'no_match', 'error']
    evidence: list[Evidence] = Field(default_factory=list, max_length=50)
    coverage: Coverage = Field(default_factory=Coverage)
    error: ProviderError | None = None
    timings_ms: Timings = Field(default_factory=Timings)

    @model_validator(mode='after')
    def consistent(self):
        if (self.status == 'error') != (self.error is not None):
            raise ValueError('Error/status mismatch')
        if self.status in ('no_match', 'error') and self.evidence:
            raise ValueError('Unexpected evidence')
        if len({e.evidence_id for e in self.evidence}) != len(self.evidence):
            raise ValueError('Duplicate evidence')
        if self.provider == 'mock' and not self.is_synthetic:
            raise ValueError('Mock must be marked synthetic')
        if any(e.is_synthetic for e in self.evidence) and not self.is_synthetic:
            raise ValueError('Synthetic evidence must mark the result')
        return self


class EvidenceResult(Contract):
    status: Literal['ok', 'not_found', 'restricted', 'version_unavailable', 'error']
    reference: Reference
    text: str | None = Field(default=None, max_length=30000)
    content_hash: str | None = None

    @model_validator(mode='after')
    def permitted(self):
        if (self.status == 'ok') != (self.text is not None):
            raise ValueError('Text/status mismatch')
        return self


class KnowledgeProvider(Protocol):
    def search_evidence(self, request: SearchRequest, context: TrustedContext) -> SearchResult: ...
    def get_evidence(self, reference: Reference, purpose: Literal['display', 'model'], context: TrustedContext) -> EvidenceResult: ...
