from decimal import Decimal

import pytest

from packages.income_tax.korea_company import national_company_settlement
from packages.income_tax.korea_reliefs import CompanyRelief


def calculate(base='100000000', **changes):
    args = dict(tax_year=2026, minimum_regime='sme', article60_2_1_1_company=False,
        reliefs=[], annual_standard_schedule_confirmed=True, minimum_regime_verified=True,
        eligibility_caps_and_expiry_verified=True, no_base_changing_incentives=True,
        additions_and_payments_verified=True, penalty_tax=0, relief_recapture=0,
        interim_tax=0, occasional_assessment_tax=0, withheld_tax=0, installment=False)
    args.update(changes)
    return national_company_settlement(base, **args)


def test_full_national_path_limits_relief_adds_penalties_then_offsets_payments():
    result = calculate(reliefs=[CompanyRelief('limited', 4000000, 'reduction', 2026, True),
        CompanyRelief('exempt', 1000000, 'carry_credit', 2025, False)],
        penalty_tax='1009.9', relief_recapture=200, interim_tax=5000000,
        occasional_assessment_tax=500000, withheld_tax=500000)
    assert result['gross_tax'] == 10000000
    assert result['minimum_reference_tax'] == 7000000
    assert result['tax_after_reliefs'] == 6000000
    assert result['relief_allocation'][0]['unused'] == 1000000
    assert result['liability_before_cash_rounding'] == Decimal('6001209.9')
    assert result['settlement']['payable'] == 1200
    assert result['settlement']['refundable'] == 0


def test_excess_payment_produces_refund_without_minimum_tax_uplift():
    result = calculate(minimum_regime='general', interim_tax=10000019)
    assert result['settlement']['refundable'] == 10
    assert result['settlement']['discarded_fraction'] == -9


def test_credits_cannot_absorb_penalty_or_recapture():
    result = calculate(reliefs=[CompanyRelief('exempt', 100000000, 'carry_credit', 2026, False)],
        penalty_tax=123, relief_recapture=456)
    assert result['tax_after_reliefs'] == 0
    assert result['settlement']['payable'] == 570


def test_national_result_does_not_claim_local_assessment():
    result = calculate()
    assert result['tax_scope'] == 'national_corporate_income_tax_only'
    assert not any(s['doc_id'].startswith('kr.local-tax') for s in result['sources'])
    assert any('Article64' in s['provisions'] for s in result['sources'])
    assert 'local_tax' not in result and 'final_tax' not in result


@pytest.mark.parametrize('field', ['annual_standard_schedule_confirmed', 'minimum_regime_verified',
    'eligibility_caps_and_expiry_verified', 'no_base_changing_incentives', 'additions_and_payments_verified'])
def test_missing_basis_confirmation_rejected(field):
    with pytest.raises(ValueError): calculate(**{field: False})


@pytest.mark.parametrize('field', ['penalty_tax', 'relief_recapture', 'interim_tax',
    'occasional_assessment_tax', 'withheld_tax'])
def test_negative_credit_or_addition_rejected(field):
    with pytest.raises(ValueError): calculate(**{field: '-1'})


def test_installments_not_silently_given_single_payment_rounding():
    with pytest.raises(ValueError): calculate(installment=True)
