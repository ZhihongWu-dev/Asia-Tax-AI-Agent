from decimal import Decimal
import pytest
from packages.contracts.income_tax import IncomeTaxCase
from packages.contracts.income_assessment import THCompany
from packages.income_tax.assessment import calculate


def inputs(gross='1000000', deductions='0', losses='0', base='1000000', exempt='0'):
    case = IncomeTaxCase(subject='company', jurisdiction='th', currency='THB',
        residency='resident', period_start='2026-01-01', period_end='2026-12-31',
        claimed_deductions=deductions, carried_losses=losses, facts_confirmed=True,
        incomes=[dict(category='business', source_jurisdiction='th',
                      gross_amount=gross, description='Statutory business income')])
    basis = THCompany(policy='th_company_2026', net_taxable_profit=base,
        exempt_income=exempt, scheme='ordinary', sme_eligibility_confirmed=False,
        ordinary_treatment_confirmed=True, allowed_tax_credits='0', prepaid_tax='0',
        basis_confirmed=True, basis_explanation='Verified statutory income, expenses, exemptions and eligible loss vintages.')
    return case, basis


@pytest.mark.parametrize('changes', [dict(gross='100'), dict(deductions='1'),
    dict(losses='1'), dict(exempt='1'), dict(exempt='1000001')])
def test_manual_base_cannot_disagree_with_saved_facts(changes):
    with pytest.raises(ValueError, match='reconcile|Exempt income'):
        calculate(*inputs(**changes))


@pytest.mark.parametrize('scheme', ['ordinary', 'sme'])
def test_exemption_expenses_and_prior_losses_reconcile(scheme):
    case, basis = inputs(gross='5000000', deductions='1000000', losses='200000',
                         exempt='500000', base='3300000')
    basis = basis.model_copy(update=dict(scheme=scheme, sme_eligibility_confirmed=scheme=='sme'))
    result = calculate(case, basis)
    assert Decimal(result['gross_tax']) == (660000 if scheme=='ordinary' else 465000)
    rec = result['basis_reconciliation']
    assert Decimal(rec['income_before_loss_relief']) == 3500000
    assert Decimal(rec['prior_losses_used']) == 200000
    assert Decimal(rec['taxable_income']) == 3300000
    assert any(s['doc_id']=='th.rc3b.th' and s['sha256'] for s in result['sources'])


def test_current_loss_does_not_consume_previous_losses():
    result = calculate(*inputs(gross='100', deductions='200', losses='50', base='0'))
    rec = result['basis_reconciliation']
    assert Decimal(rec['current_period_loss']) == 100
    assert Decimal(rec['prior_losses_used']) == 0
    assert Decimal(rec['prior_losses_unused']) == 50
    assert Decimal(result['gross_tax']) == 0


def test_excess_prior_loss_is_separate_from_current_period_loss():
    result = calculate(*inputs(gross='100', losses='150', base='0'))
    rec = result['basis_reconciliation']
    assert Decimal(rec['current_period_loss']) == 0
    assert Decimal(rec['prior_losses_used']) == 100
    assert Decimal(rec['prior_losses_unused']) == 50
