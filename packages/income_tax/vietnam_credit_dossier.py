"""Document inventory for Article62(3), not tax entitlement or filing approval.

Based on visually reviewed pages102-104 of14/VBHN-BTC2026. Later amendments
and the separate annual return must be reviewed before filing readiness is
asserted. Evidence references are opaque case-local references, never fetched.
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
    return {
        'policy_version': 'vn-treaty-credit-dossier-2026-11-18',
        'required_documents': required,
        'missing_documents': missing,
        'unchecked_documents': unchecked,
        'document_inventory_complete': not missing and not unchecked,
        'basis': dossier.model_dump(mode='json'),
        'stage': 'document_inventory_only',
        'unresolved_checks': [
            'Treaty and foreign-law eligibility for each claimed credit type',
            'Tax-year, foreign-payment timing, credit cap and amount reconciliation',
            'Subsequent amendments and current annual return requirements',
            'Tax-authority examination of the submitted application',
        ],
        'sources': [{
            'title': 'Circular80 Article62(3), consolidated14/VBHN-BTC2026',
            'url': 'https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/14-vbhn-btc.pdf',
            'pages': [102, 103, 104],
            'sha256': '0cae81492f8c3af94639d5370469a31860bc81e72e0d07c706a9efbeec13cfa5',
        }],
    }
