import pytest

from packages.income_tax.korea_salary_settlement import national_salary_balance, local_salary_balance


def run(decision=2000000,current=0,former=0,**changes):
    args=dict(tax_year=2026,decision_and_employer_records_verified=True,installment=False)
    args.update(changes)
    return national_salary_balance(decision,current,former,**args)


@pytest.mark.parametrize('balance,payable,waived',[(0,0,0),(1,0,1),(999,0,999),
    (1000,1000,0),(1009,1000,0),(1010,1010,0)])
def test_positive_noncollection_and_ten_won_boundaries(balance,payable,waived):
    result=run(decision=100000+balance,current=100000)
    assert result['settlement']['payable']==payable
    assert result['small_balance_not_collected']==waived


@pytest.mark.parametrize('overpaid,refund',[(1,0),(9,0),(10,10),(999,990),(1009,1000)])
def test_refunds_not_removed_by_positive_noncollection_threshold(overpaid,refund):
    result=run(decision=100000,current=100000+overpaid)
    assert result['small_balance_not_collected']==0
    assert result['settlement']['refundable']==refund


def test_former_settled_tax_and_current_withholding_reconcile():
    result=run(decision=3087500,current=2000000,former=1000000)
    assert result['total_payment_credits']==3000000
    assert result['settlement']['payable']==87500


@pytest.mark.parametrize('changes',[dict(decision_and_employer_records_verified=False),
    dict(installment=True),dict(tax_year=2025),dict(decision='1000.01'),
    dict(current=True),dict(former=-1)])
def test_unverified_and_invalid_receipt_inputs_rejected(changes):
    with pytest.raises(ValueError):run(**changes)


@pytest.mark.parametrize('national,current,former,payable,refund',[
    (999,0,0,90,0),(1000,0,0,100,0),(19999,0,0,1990,0),
    (20000,0,0,2000,0),(3387501,300000,40000,0,1250),
    (10000,2000,500,0,1500)])
def test_local_salary_uses_decision_and_own_payments(national,current,former,payable,refund):
    result=local_salary_balance(national,current,former,tax_year=2026,
        employer_special_collection_verified=True,installment=False)
    assert result['settlement']['payable']==payable
    assert result['settlement']['refundable']==refund


def test_local_employer_mode_cannot_be_assumed_for_assessment_notice():
    with pytest.raises(ValueError):
        local_salary_balance(1000,0,0,tax_year=2026,
            employer_special_collection_verified=False,installment=False)
