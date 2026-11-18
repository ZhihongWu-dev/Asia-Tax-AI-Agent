import pytest
from pydantic import ValidationError

from packages.income_tax.vietnam_credit_dossier import review_dossier


def document(kind, checked=True):
    return dict(kind=kind, evidence_reference='case-document-17',
                required_form_and_content_checked=checked)


def review(types=None, documents=None, represented=False):
    return review_dossier(dict(credit_types=types or ['direct'],
                              documents=documents or [], represented=represented))


def test_direct_credit_requires_receipt_and_authority_confirmation():
    result = review(documents=[document('treaty_credit_application'),
                              document('foreign_income_tax_return')])
    assert result['missing_documents'] == [
        'foreign_payment_receipt', 'foreign_authority_paid_tax_confirmation']
    assert not result['document_inventory_complete']


def test_sparing_is_not_proven_by_actual_payment_receipt():
    result = review(['tax_sparing'], [document('foreign_payment_receipt')])
    assert 'foreign_authority_sparing_confirmation' in result['missing_documents']
    assert 'foreign_business_legal_evidence' in result['missing_documents']
    assert 'foreign_payment_receipt' not in result['required_documents']


def test_indirect_credit_needs_underlying_tax_and_ownership_evidence():
    result = review(['indirect'])
    assert result['missing_documents'] == [
        'treaty_credit_application', 'ownership_legal_evidence',
        'distributor_foreign_tax_return', 'dividend_withholding_return',
        'foreign_authority_underlying_tax_confirmation']


def test_combined_claim_reuses_common_return_and_keeps_distinct_proofs():
    result = review(['direct', 'tax_sparing', 'indirect'], represented=True)
    required = result['required_documents']
    assert len(required) == len(set(required)) == 11
    complete = review(['direct', 'tax_sparing', 'indirect'],
                      [document(kind) for kind in required], represented=True)
    assert complete['document_inventory_complete']
    assert complete['stage'] == 'document_inventory_only'
    assert complete['unresolved_checks']
    assert 'allowed_tax_credits' not in complete
    assert 'approved' not in complete


def test_reference_without_content_review_is_incomplete():
    required = review()['required_documents']
    result = review(documents=[document(kind, kind != 'foreign_payment_receipt')
                               for kind in required])
    assert result['missing_documents'] == []
    assert result['unchecked_documents'] == ['foreign_payment_receipt']
    assert not result['document_inventory_complete']


@pytest.mark.parametrize('changes', [
    {'represented': 1}, {'represented': 'false'},
    {'credit_types': []}, {'credit_types': ['direct', 'direct']},
    {'credit_types': ['ordinary']}, {'approved': True},
    {'documents': [document('foreign_payment_receipt')]*2},
    {'documents': [document('unknown')]},
    {'documents': [dict(document('foreign_payment_receipt'), evidence_reference='  ')]},
    {'documents': [dict(document('foreign_payment_receipt'), required_form_and_content_checked=1)]},
])
def test_ambiguous_or_invalid_dossier_rejected(changes):
    values = dict(credit_types=['direct'], documents=[], represented=False)
    values.update(changes)
    with pytest.raises(ValidationError):
        review_dossier(values)


def test_result_mutation_does_not_modify_later_reviews():
    result = review()
    result['required_documents'].clear()
    result['sources'][0]['pages'].clear()
    assert review()['required_documents']
    assert review()['sources'][0]['pages'] == [102, 103, 104]
