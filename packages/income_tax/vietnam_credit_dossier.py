"""Document inventory for Circular89 Article34, not tax entitlement or approval.

Based on visually reviewed pages76-78 of Circular89/2026, effective2026-07-01.
The separate annual return must be reviewed before filing readiness is asserted.
Evidence references are opaque case-local references, never fetched.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator


CreditType = Literal['direct', 'tax_sparing', 'indirect']
DocumentKind = Literal[
    'treaty_credit_application', 'foreign_income_tax_return',
    'foreign_payment_receipt', 'foreign_authority_paid_tax_confirmation',
    'foreign_business_legal_evidence', 'foreign_authority_sparing_confirmation',
    'ownership_legal_evidence', 'distributor_foreign_tax_return',
    'dividend_withholding_return', 'foreign_authority_underlying_tax_confirmation',
    'representative_authorisation',
]

_REQUIRED = {
    'direct': ('foreign_income_tax_return', 'foreign_payment_receipt',
               'foreign_authority_paid_tax_confirmation'),
    'tax_sparing': ('foreign_income_tax_return', 'foreign_business_legal_evidence',
                   'foreign_authority_sparing_confirmation'),
    'indirect': ('ownership_legal_evidence', 'distributor_foreign_tax_return',
                'dividend_withholding_return', 'foreign_authority_underlying_tax_confirmation'),
}


class DossierDocument(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: DocumentKind
    evidence_reference: str = Field(strict=True, min_length=1, max_length=500)
    required_form_and_content_checked: StrictBool

    @field_validator('evidence_reference')
    @classmethod
    def nonblank_reference(cls, value):
        if not value.strip():
            raise ValueError('Evidence reference cannot be blank')
        return value.strip()


class TreatyCreditDossier(BaseModel):
    model_config = ConfigDict(extra='forbid')
    credit_types: list[CreditType] = Field(min_length=1, max_length=3)
    represented: StrictBool
    documents: list[DossierDocument] = Field(max_length=11)
    missing_document_explanations: dict[DocumentKind, str] = Field(default_factory=dict)

    @field_validator('missing_document_explanations')
    @classmethod
    def meaningful_explanations(cls, value):
        if any(not text.strip() or len(text) > 4000 for text in value.values()):
            raise ValueError('Missing-document explanations require nonblank text up to4000 characters')
        return {kind: text.strip() for kind, text in value.items()}

    @field_validator('credit_types')
    @classmethod
    def distinct_credit_types(cls, value):
        if len(set(value)) != len(value):
            raise ValueError('Credit types must be unique')
        return value

    @field_validator('documents')
    @classmethod
    def distinct_document_kinds(cls, value):
        if len({doc.kind for doc in value}) != len(value):
            raise ValueError('Each document kind must have one evidence reference')
        return value


def review_dossier(dossier):
    """Return missing and unchecked items without claiming entitlement.

    Multiple credit types can coexist. Their requirements are unioned; a
    confirmed return may serve both direct and sparing claims. A reference
    alone never proves required certification, originals or legal contents.
    """
    dossier = TreatyCreditDossier.model_validate(dossier)
    required = ['treaty_credit_application']
    for credit_type in dossier.credit_types:
        required.extend(kind for kind in _REQUIRED[credit_type] if kind not in required)
    if dossier.represented:
        required.append('representative_authorisation')
    supplied = {doc.kind: doc for doc in dossier.documents}
    missing = [kind for kind in required if kind not in supplied]
    unchecked = [kind for kind in required if kind in supplied
                 and not supplied[kind].required_form_and_content_checked]
    if any(kind not in missing for kind in dossier.missing_document_explanations):
        raise ValueError('Explanations must identify a missing required document')
    return {
        'policy_version': 'vn-treaty-credit-dossier-circular89-2026-11-18',
        'required_documents': required,
        'missing_documents': missing,
        'unchecked_documents': unchecked,
        'unexplained_missing_documents': [kind for kind in missing
            if kind not in dossier.missing_document_explanations],
        'missing_document_explanations': dict(dossier.missing_document_explanations),
        'document_inventory_complete': not missing and not unchecked,
        'submission_context': 'With annual finalisation return, or the tax return where finalisation is not required (Article34(3)).',
        'explanation_context': 'Missing information or documents must be specifically explained in02/HTQT underArticle34(2); explanation does not establish eligibility.',
        'basis': dossier.model_dump(mode='json'),
        'stage': 'document_inventory_only',
        'unresolved_checks': [
            'Treaty and foreign-law eligibility for each claimed credit type',
            'Tax-year, foreign-payment timing, credit cap and amount reconciliation',
            'Current annual return requirements and any later applicable amendments',
            'Substantive verification of the filed information and supporting evidence',
        ],
        'sources': [{
            'title': 'Circular89/2026/TT-BTC Article34',
            'url': 'https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/7/89-btc.signed.pdf',
            'pages': [76, 77, 78],
            'sha256': '952c45ffc0f10bfc176bd9ae6b3d204fd3a034294ee270278957b9c11e1471dc',
        }],
    }
