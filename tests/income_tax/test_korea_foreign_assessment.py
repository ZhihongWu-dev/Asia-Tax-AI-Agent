from decimal import Decimal
import pytest
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.korea_foreign_assessment import assess
from tests.income_tax.test_korea_foreign_reconciliation import fixture
from tests.income_tax.test_korea_assessment_workflow import basis


def arguments():
    case, workpaper = fixture()
    for item in case['incomes']:
        for key in ('gross_amount', 'foreign_tax_paid'):
            if key in item: item[key] = str(Decimal(item[key]) * 100000)
    case['claimed_deductions'] = '20000000'
    for group in workpaper['groups']:
        for key in ('expenses_already_in_foreign_income', 'corresponding_expenses', 'eligible_direct_foreign_tax'):
            group[key] = str(Decimal(group[key]) * 100000)
    payload = basis()
    return dict(case=IncomeTaxCase.model_validate(case), workpaper=workpaper,
        national_inputs=payload['national_inputs'], local_inputs=payload['local_inputs'],
        current_direct_credit_and_local_deduction_eligibility_verified=True,
        no_prior_foreign_balances_other_reliefs_or_separate_taxes_verified=True)


def test_national_refund_and_local_payables_remain_separate():
    r = assess(**arguments())
    assert r['national']['gross_tax'] == 10000000
    assert r['national']['allowed_foreign_tax_credit'] == 4000000
    assert r['national']['liability_before_cash_rounding'] == 6000000
    assert r['national']['settlement']['refundable'] == 5000000
    assert r['local_taxable_base'] == 85000000
    assert r['local']['filings']['HQ']['settlement']['payable'] == 510000
    assert r['local']['filings']['Branch']['settlement']['payable'] == 340000
    assert r['total_payable'] == 850000
    assert r['total_refundable'] == 5000000
    row = r['foreign_credit']['country_credits'][0]
    assert row['expense_related_excess_not_carried'] == 1000000
    assert row['eligible_current_year_carryforward'] == 10000000


def test_additions_are_not_absorbed_by_foreign_credit():
    args = arguments()
    args['national_inputs'].update(penalty_tax='123', relief_recapture='456', interim_tax='0')
    r = assess(**args)
    assert r['national']['liability_before_cash_rounding'] == 6000579
    assert r['national']['settlement']['payable'] == 6000570


def test_repeating_country_limit_keeps_internal_precision_until_cash_settlement():
    args = arguments()
    data = args['case'].model_dump()
    data['incomes'][0]['gross_amount'] = '260000003'
    args['case'] = IncomeTaxCase.model_validate(data)
    r = assess(**args)
    assert r['national']['allowed_foreign_tax_credit'].as_tuple().exponent < -6
    assert r['national']['settlement']['payable'] % 10 == 0


def test_all_statutory_citations_are_preserved_when_sources_merge():
    r = assess(**arguments())
    sources = {s['doc_id']: s for s in r['sources']}
    assert len(sources) == len(r['sources'])
    provisions = sources['kr.corporate-tax-act.20260701.ko']['provisions']
    assert 'Article64' in provisions and 'Article57(1),(2),(7)' in provisions
    assert 'kr.local-tax.article103-19.20260701' in sources


@pytest.mark.parametrize('change', ['manual_credit', 'eligibility', 'prior_balances', 'installment'])
def test_unreconciled_reliefs_and_unsupported_settlement_rejected(change):
    args = arguments()
    if change == 'manual_credit':
        args['national_inputs']['reliefs'] = [dict(identifier='foreign-again', value='4000000',
            category='carry_credit', origin_year=2026, minimum_tax_subject=False)]
    elif change == 'eligibility': args['current_direct_credit_and_local_deduction_eligibility_verified'] = False
    elif change == 'prior_balances': args['no_prior_foreign_balances_other_reliefs_or_separate_taxes_verified'] = False
    else: args['national_inputs']['installment'] = True
    with pytest.raises(ValueError): assess(**args)


def test_saved_http_case_replays_after_database_reopen(tmp_path):
    from types import SimpleNamespace
    from uuid import uuid4
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.api import auth, chat
    from packages.chat.store import ChatStore
    from tests.chat.auth_support import fixture_user
    args = arguments()
    case = args.pop('case')
    payload = dict(policy='kr_company_foreign_direct_2026', basis_confirmed=True,
        basis_explanation='Verified saved country incomes, expenses, tax payments and local filing groups.', **args)
    url = 'sqlite:///' + str(tmp_path / 'foreign.db')
    service = SimpleNamespace(store=ChatStore(url))
    app = FastAPI(); app.include_router(auth.router); app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user] = fixture_user
    app.dependency_overrides[chat.get_service] = lambda: service
    headers = {'x-asiatax-request': '1'}
    with TestClient(app) as client:
        client.get('/api/auth/session')
        case_id = client.post('/api/cases', headers=headers).json()['id']
        path = f'/api/cases/{case_id}/income-tax'
        saved = client.put(path, headers=headers, json=dict(revision=0,
            request_id=str(uuid4()), inputs=case.model_dump(mode='json')))
        assert saved.status_code == 200, saved.text
        request = dict(revision=1, request_id=str(uuid4()), basis=payload)
        response = client.post(path+'/runs', headers=headers, json=request)
        assert response.status_code == 200, response.text
        run = response.json()
        assert Decimal(run['result']['total_refundable']) == 5000000
        assert Decimal(run['result']['total_payable']) == 850000
        service.store.engine.dispose(); service.store = ChatStore(url)
        assert client.get(path+'/runs/'+run['id']).json() == run
        assert client.post(path+'/runs', headers=headers, json=request).json() == run
        for locale, heading in [('en', 'Korean country credits and local tax'), ('zh', '韩国分国抵免与地方税')]:
            report = client.get(path+'/runs/'+run['id']+'/report?locale='+locale)
            assert report.status_code == 200, report.text
            assert heading in report.json()['markdown']
            assert '| SG | 40000000 | 4000000 | 4000000 | 1000000 | 10000000 |' in report.json()['markdown']
        request['request_id'] = str(uuid4())
        request['revision'] = client.get('/api/cases/'+case_id).json()['revision']
        request['basis']['workpaper']['groups'][1]['eligible_direct_foreign_tax'] = '15000001'
        assert client.post(path+'/runs', headers=headers, json=request).status_code == 422
    service.store.engine.dispose()
