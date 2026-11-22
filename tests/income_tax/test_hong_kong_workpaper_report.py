from copy import deepcopy
from fractions import Fraction as F
from hashlib import sha256
import json
import pytest
from packages.reporting.income_tax import render
from tests.income_tax.test_hong_kong_saved_credit_constraints import fixture
from tests.income_tax.test_hong_kong_ordinary_credit_workpaper import run as prepare


def snapshot(case,p,result,allocations=None):
    basis=dict(workpaper=p,two_tier_eligible=result['two_tier_eligible'],
        ordinary_annual_basis_and_reduction_ordering_verified=True,
        ongoing_business_unchanged_accounting_year_verified=True,
        allocations=None if allocations is None else {key:dict(numerator=str(value.numerator),
            denominator=str(value.denominator)) for key,value in allocations.items()})
    data=json.loads(json.dumps(dict(inputs=case,basis=basis,result=result),default=str))
    digest=sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return dict(data,id='synthetic-workpaper',case_id='synthetic-case',input_revision=1,
        created_at='2026-11-22T00:00:00Z',status='workpaper',snapshot_hash=digest)


@pytest.mark.parametrize('locale',['zh','en'])
def test_report_distinguishes_rate_base_credit_base_and_display_precision(locale):
    case,p=fixture();case.update(period_start='2025-01-01',period_end='2025-12-31')
    saved=snapshot(case,p,prepare(case,p));original=deepcopy(saved)
    report=render(saved,locale)
    structured=report.split('## 完整资料' if locale=='zh' else '## Complete inputs')[0]
    assert r'2025\-01\-01 / 2025\-12\-31' in structured
    assert '27/200' in structured and r'12215\.57' in structured
    assert ('税率基数' if locale=='zh' else 'credit-rate basis') in structured
    assert ('分配金额唯一' if locale=='zh' else 'allocation is unique') in structured
    assert ('仅便于阅读' if locale=='zh' else 'for readability') in structured
    assert ('非最终评税' if locale=='zh' else 'not final assessment') in structured
    assert '| Final tax |' not in structured and '| 本期最终税额 |' not in structured
    assert 'exact_constraints' in report and '2040000' in report
    for source in saved['result']['sources']:
        assert source['url'] in report
        assert source['sha256'] in report
    assert saved==original


@pytest.mark.parametrize('locale',['zh','en'])
@pytest.mark.parametrize('allocated',[False,True])
def test_ambiguous_and_explicit_allocations_are_labelled_differently(locale,allocated):
    case,p=fixture();case['incomes'][1].update(gross_amount='50000',foreign_tax_paid='10000')
    p['groups'][1]['foreign_credit']['direct_foreign_tax_paid']='10000'
    case['incomes'].append(deepcopy(case['incomes'][1]))
    group=deepcopy(p['groups'][1]);group.update(source_id='receipt_b',income_indexes=[2])
    group['foreign_credit']['source_id']='receipt_b';p['groups'].append(group)
    allocation={'receipt_a':F(1020000,167),'receipt_b':F(1020000,167)} if allocated else None
    report=render(snapshot(case,p,prepare(case,p,allocations=allocation),allocations=allocation),locale)
    structured=report.split('## 完整资料' if locale=='zh' else '## Complete inputs')[0]
    if allocated:
        assert ('通过限额核对' if locale=='zh' else 'supplied allocation passes') in structured
        assert ('待确认：' if locale=='zh' else 'Pending:') not in structured
    else:
        assert ('待确认：' if locale=='zh' else 'Pending:') in structured
        assert ('最小可分配额' if locale=='zh' else 'Minimum allocation') in structured
        assert ('尚未形成逐来源扣除明细' if locale=='zh' else 'source deductions have not been finalized') in structured


def test_source_identifiers_are_escaped_outside_complete_snapshot():
    case,p=fixture();identifier='<img src=x>|source'
    p['groups'][1]['source_id']=identifier
    p['groups'][1]['foreign_credit']['source_id']=identifier
    report=render(snapshot(case,p,prepare(case,p)),'en')
    structured=report.split('## Complete inputs')[0]
    assert '<img' not in structured
    assert '&lt;img src=x&gt;\\|source' in structured


def test_edited_result_cannot_reuse_old_report_hash():
    case,p=fixture();saved=snapshot(case,p,prepare(case,p))
    saved['result']['constraints']['allocation_required']=True
    with pytest.raises(ValueError,match='assessment_snapshot_mismatch'):render(saved)
