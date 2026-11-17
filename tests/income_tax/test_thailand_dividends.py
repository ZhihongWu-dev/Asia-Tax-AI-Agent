from decimal import Decimal, localcontext

import pytest

from packages.income_tax.thailand_dividends import DividendTranche, prepare_aggregated_dividends


def prepare(*rows, **kwargs):
    return prepare_aggregated_dividends(list(rows), certificates_verified=True,
                                      recipient_eligibility_verified=True, **kwargs)


def test_mixed_certified_rates_and_withholding_are_not_a_fixed_fraction():
    result = prepare(DividendTranche('80000', '20', '8000', True),
                     DividendTranche('70000', '30', '7000', True),
                     DividendTranche('50000', None, '5000', False))
    assert result['gross_dividends'] == 200000
    assert result['dividend_credit'] == 50000
    assert result['assessable_dividends'] == 250000
    assert result['withholding_tax'] == 20000
    assert result['tranches'][0]['net_cash_received'] == 72000
    assert result['tranches'][0]['dividend_credit'] == 20000
    assert result['tranches'][1]['dividend_credit'] == 30000
    assert 'final_tax' not in result  # Annual election/settlement is separate.


def test_zero_rate_and_noncreditable_dividends_remain_distinct():
    result = prepare(DividendTranche('100', '0', '10', True),
                     DividendTranche('100', None, '10', False))
    assert result['dividend_credit'] == 0
    assert result['assessable_dividends'] == 200
    assert result['tranches'][0]['credit_eligible'] is True
    assert result['tranches'][1]['credit_eligible'] is False


def test_repeating_rate_does_not_depend_on_callers_decimal_context():
    with localcontext() as ctx:
        ctx.prec = 6
        result = prepare(DividendTranche('100', '15', '10', True))
    with localcontext() as ctx:
        ctx.prec = 40
        assert result['dividend_credit'] == Decimal('1500') / 85


@pytest.mark.parametrize('rate', [None, '100', '101', '-1', 'NaN', True, 20.0])
def test_invalid_or_missing_eligible_rate(rate):
    with pytest.raises(ValueError):
        prepare(DividendTranche('100', rate, '10', True))


@pytest.mark.parametrize('row', [DividendTranche('100', '20', '101', True),
    DividendTranche('-1', '20', '0', True), DividendTranche('100', '20', '10', False),
    DividendTranche('100', '20', '10', 1), DividendTranche(100.0, '20', '10', True)])
def test_inconsistent_tranches_rejected(row):
    with pytest.raises(ValueError):
        prepare(row)


@pytest.mark.parametrize('flag', [False, 1, 'true', None])
def test_certificates_and_eligibility_are_strict(flag):
    row = DividendTranche('100', '20', '10', True)
    for field in ('certificates_verified', 'recipient_eligibility_verified'):
        args = dict(certificates_verified=True, recipient_eligibility_verified=True)
        args[field] = flag
        with pytest.raises(ValueError):
            prepare_aggregated_dividends([row], **args)


def test_empty_tranches_rejected():
    with pytest.raises(ValueError):
        prepare()


def annual(rows, **changes):
    from packages.income_tax.thailand_dividends import annual_dividend_assessment
    args = dict(tax_year=2026, election='aggregate', employment_gross='0',
                other_nonemployment_gross='0', allowed_expenses_and_allowances='60000',
                other_prepaid_tax='0', certificates_verified=True,
                recipient_eligibility_verified=True, election_scope_verified=True)
    return annual_dividend_assessment(rows, **{**args, **changes})


def test_refundable_credit_is_not_capped_at_zero_tax():
    result = annual([DividendTranche('80000', '20', '8000', True)])
    assert result['annual_assessable_income'] == 100000
    assert result['net_taxable_income'] == 40000
    assert result['gross_tax'] == 0
    assert result['net_assessed_tax'] == -20000
    assert result['final_tax'] == 0
    assert result['refundable_dividend_credit'] == 20000
    assert result['refund_due'] == 28000


def test_final_election_does_not_refund_dividend_withholding():
    result = annual([DividendTranche('80000', '20', '8000', True)], election='final_withholding')
    assert result['annual_assessable_income'] == 0
    assert result['dividend_credit'] == 0
    assert result['separate_final_dividend_tax'] == 8000
    assert result['prepaid_tax'] == 0
    assert result['refund_due'] == 0


def test_minimum_tax_includes_grossed_up_nonemployment_income():
    result = annual([DividendTranche('800001', '20', '80000.1', True)],
                    allowed_expenses_and_allowances='2000000')
    assert result['minimum_tax_before_exemption'] == Decimal('5000.00625')
    assert result['minimum_tax'] == Decimal('5000.00625')
    exact = annual([DividendTranche('800000', '20', '80000', True)],
                   allowed_expenses_and_allowances='2000000')
    assert exact['minimum_tax_before_exemption'] == 5000
    assert exact['minimum_tax'] == 0


def test_combined_salary_and_dividend_gross_up():
    result = annual([DividendTranche('80000', '20', '8000', True)],
                    employment_gross='1000000', allowed_expenses_and_allowances='160000',
                    other_prepaid_tax='100000')
    assert result['net_taxable_income'] == 940000
    assert result['gross_tax'] == 103000
    assert result['final_tax'] == 83000
    assert result['prepaid_tax'] == 108000
    assert result['refund_due'] == 25000


@pytest.mark.parametrize('changes', [dict(tax_year=True), dict(tax_year=2025),
    dict(election='best'), dict(election_scope_verified=False), dict(election_scope_verified=1)])
def test_unverified_election_or_year_rejected(changes):
    with pytest.raises(ValueError):
        annual([DividendTranche('100', '20', '10', True)], **changes)


def test_final_election_requires_each_tranche_to_be_fully_withheld():
    with pytest.raises(ValueError):
        annual([DividendTranche('100', '20', '5', True),
                DividendTranche('100', '20', '15', True)], election='final_withholding')
