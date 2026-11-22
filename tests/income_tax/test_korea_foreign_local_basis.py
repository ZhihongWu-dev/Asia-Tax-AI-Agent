import hashlib
from pathlib import Path
import pytest
from packages.income_tax.korea_foreign_local_basis import reconcile_local_base


def calc(base='1000',addback='0',direct='150',fund='0'):
    return reconcile_local_base(national_taxable_base=base,
        expired_foreign_tax_deducted_nationally=addback,article57_foreign_tax=direct,
        article57_2_eligible_fund_credit=fund,
        local_eligibility_addback_and_no_duplicate_amounts_verified=True,
        no_prior_local_foreign_tax_deductions_verified=True)


def test_local_deduction_is_foreign_tax_not_national_credit():
    result=calc()
    assert result['current_local_foreign_tax_deduction']==150
    assert result['local_taxable_base']==850
    assert result['excess_current_local_deduction']==0


def test_expired_national_tax_is_added_back_before_local_deduction():
    result=calc(base='900',addback='100')
    assert result['local_base_before_foreign_tax_deduction']==1000
    assert result['local_taxable_base']==850


@pytest.mark.parametrize('base,direct,used,excess',[('100','150',100,50),('0','150',0,150),('150','150',150,0),('100','0',0,0)])
def test_nonnegative_base_and_separate_local_carry(base,direct,used,excess):
    result=calc(base=base,direct=direct)
    assert result['current_local_foreign_tax_deduction']==used
    assert result['excess_current_local_deduction']==excess
    assert result['local_carryforward_years']==15


def test_distinct_fund_credit_deduction():
    result=calc(direct='100',fund='25')
    assert result['local_taxable_base']==875


def test_sources_and_evidence_gate():
    root=Path(__file__).resolve().parents[2]
    for source in calc()['sources']:
        assert hashlib.sha256((root/source['file']).read_bytes()).hexdigest()==source['sha256']
    with pytest.raises(ValueError):
        reconcile_local_base(national_taxable_base='1000',expired_foreign_tax_deducted_nationally='0',
            article57_foreign_tax='150',article57_2_eligible_fund_credit='0',
            local_eligibility_addback_and_no_duplicate_amounts_verified=False,
            no_prior_local_foreign_tax_deductions_verified=True)
