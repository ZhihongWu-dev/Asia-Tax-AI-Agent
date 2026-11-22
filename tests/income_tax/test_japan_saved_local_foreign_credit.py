import hashlib
from pathlib import Path
import pytest
from packages.contracts.income_tax import IncomeTaxCase,CURRENCIES
from packages.income_tax.japan_foreign_reconciliation import current_standard_local_workpaper
from packages.income_tax.japan_local_foreign_credit import allocate_standard_current
from tests.income_tax.test_japan_foreign_reconciliation import fixture
from tests.income_tax.test_japan_foreign_credit import args


def local_paper():
    return dict(
        prefectures=[dict(filing_id='Osaka prefecture',verified_employee_weight=10,
            available_corporation_levy_before_final_rounding=464000)],
        municipalities=[dict(filing_id='Osaka city',verified_employee_weight=10,
            available_corporation_levy_before_final_rounding=1902400)],
        standard_limits_without_actual_rate_election_verified=True,
        employee_weights_and_available_levies_verified=True,
        no_history_groups_reorganizations_or_tokyo_special_ward_composition_verified=True)


def calculate(case,p,local=None):
    # Exercise the actual contract's persisted JSON representation, too.
    saved=IncomeTaxCase.model_validate_json(IncomeTaxCase(**case).model_dump_json())
    return current_standard_local_workpaper(saved,p,local or local_paper(),
        rate_regime='ordinary',rate_classification_verified=True,
        no_other_tax_credits_additions_or_history_verified=True)


@pytest.mark.parametrize('country',[c for c in CURRENCIES if c!='jp'])
def test_saved_foreign_source_derives_national_and_standard_local_limits(country):
    case,p=fixture(country);result=calculate(case,p)
    r=result['current_foreign_credit']
    assert r['prefectural_credit_limit']==92800
    assert r['municipal_credit_limit']==556800
    assert r['prefectural']['current_credit']==92800
    assert r['municipal']['current_credit']==556800
    assert r['foreign_tax_above_all_current_limits']==823360
    assert r['national_credit']['total_current_national_credit']==10527040
    assert result['source_reconciliation']['statutory_worldwide_income']==100000000


def test_saved_exempt_income_changes_both_local_caps_without_changing_worldwide_base():
    case,p=fixture();p['groups'][1]['foreign_income_exempt_from_foreign_tax']='10000000'
    result=calculate(case,p);r=result['current_foreign_credit']
    assert result['source_reconciliation']['statutory_worldwide_income']==100000000
    assert r['prefectural_credit_limit']==69600
    assert r['municipal_credit_limit']==417600


def test_standard_local_caps_use_corporation_limit_not_total_national_limit():
    n=args();n['corporation_tax_reference']=10199
    n['foreign_income_before_exempt']=100000000
    r=allocate_standard_current(n,local_paper())
    assert r['national_credit']['corporation_credit_limit']==9179
    assert r['prefectural_credit_limit']==91
    assert r['municipal_credit_limit']==550


@pytest.mark.parametrize('field',[
    'standard_limits_without_actual_rate_election_verified',
    'employee_weights_and_available_levies_verified',
    'no_history_groups_reorganizations_or_tokyo_special_ward_composition_verified'])
def test_local_evidence_cannot_be_inferred_from_saved_national_facts(field):
    case,p=fixture();local=local_paper();local[field]=False
    with pytest.raises(ValueError):calculate(case,p,local)


@pytest.mark.parametrize('field',['prefectural_credit_limit','municipal_credit_limit'])
def test_manual_caps_cannot_override_saved_standard_derivation(field):
    case,p=fixture();local=local_paper();local[field]=999999
    with pytest.raises(ValueError):calculate(case,p,local)


def test_saved_foreign_payment_mismatch_rejected_before_local_allocation():
    case,p=fixture();case['incomes'][1]['foreign_tax_paid']='1'
    with pytest.raises(ValueError):calculate(case,p)


def test_combined_sources_include_rounding_and_local_authorities_with_valid_hashes():
    case,p=fixture();result=calculate(case,p)
    sources=result['sources'];ids=[s['doc_id'] for s in sources]
    assert len(ids)==len(set(ids))
    assert 'jp.nta.tsusoku119.20261122' in ids
    assert 'jp.osaka.foreign-form20-4.instructions.2026' in ids
    root=Path(__file__).resolve().parents[2]
    for source in sources:
        assert hashlib.sha256((root/source['file']).read_bytes()).hexdigest()==source['sha256']
