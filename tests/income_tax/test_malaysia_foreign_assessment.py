from decimal import Decimal

import pytest

from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.malaysia_foreign_assessment import assess


def fixture():
    case = IncomeTaxCase(subject='company', jurisdiction='my', currency='MYR', residency='resident',
        period_start='2026-01-01', period_end='2026-12-31', facts_confirmed=True,
        claimed_deductions='85000', carried_losses='0', incomes=[
            dict(description='Synthetic consultancy receipt for source reconciliation', category='business', source_jurisdiction='my', gross_amount='500000', foreign_tax_paid='0'),
            dict(description='Synthetic consultancy receipt for source reconciliation', category='business', source_jurisdiction='my', gross_amount='75000', foreign_tax_paid='7500'),
            dict(description='Synthetic domestic property rental receipt', category='rental', source_jurisdiction='my', gross_amount='30000', foreign_tax_paid='0')])
    def receipt(index, method='none', country=None, tax='0'):
        return dict(income_index=index, exempt_income='0', method=method, taxing_country=country,
            eligible_foreign_tax=tax, taxable_status_and_credit_eligibility_verified=True)
    def group(id, receipts, expenses):
        return dict(source_id=id, receipts=receipts, additions='0', expenses=expenses,
            statutory_charges='0', statutory_allowances='0', same_source_allocation_verified=True)
    paper = dict(groups=[group('business', [receipt(0), receipt(1, 'bilateral', 'in', '7500')], '80000'),
        group('rent', [receipt(2)], '5000')], total_income_deductions='0', scheme='ordinary',
        sme_eligibility_verified=False, ordinary_resident_company_no_losses_verified=True,
        deductions_and_source_allocation_verified=True, treaty_tax_period_fx_and_no_duplicate_claim_verified=True)
    return case, paper


def test_saved_business_reconciliation_and_settlement():
    case, p = fixture()
    r = assess(case, p, '120000')
    assert r['chargeable_income'] == 520000
    assert r['gross_tax'] == 124800
    assert r['allowed_foreign_tax_credit'] == 7500
    assert r['final_tax'] == 117300
    assert r['balance_due'] == -2700
    assert r['source_reconciliation'][0]['statutory_income'] == 495000


@pytest.mark.parametrize('change', ['duplicate', 'missing', 'overclaim', 'deductions', 'exempt_credit',
    'unverified', 'loss', 'negative_adjusted', 'unilateral_domestic', 'sme', 'nonresident'])
def test_unreconciled_or_ineligible_saved_inputs_rejected(change):
    case, p = fixture()
    group = p['groups'][0]
    receipt = group['receipts'][1]
    if change == 'duplicate': receipt['income_index'] = 0
    if change == 'missing': receipt['income_index'] = 3
    if change == 'overclaim': receipt['eligible_foreign_tax'] = '7501'
    if change == 'deductions': case.claimed_deductions = Decimal(0)
    if change == 'exempt_credit': receipt['exempt_income'] = '1'
    if change == 'unverified': receipt['taxable_status_and_credit_eligibility_verified'] = False
    if change == 'loss': case.carried_losses = Decimal(1)
    if change == 'negative_adjusted':
        group.update(expenses='600000', statutory_charges='100000')
        case.claimed_deductions = Decimal('605000')
    if change == 'unilateral_domestic': receipt['method'] = 'unilateral'
    if change == 'sme': p['scheme'] = 'sme'
    if change == 'nonresident': case.residency = 'nonresident'
    with pytest.raises(ValueError): assess(case, p, '0')


def test_saved_api_reopen_replay_and_invalid_claim_atomicity(tmp_path):
    from copy import deepcopy
    from types import SimpleNamespace
    from uuid import uuid4
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.api import auth, chat
    from packages.chat.store import ChatStore
    from tests.chat.auth_support import fixture_user
    case, p = fixture()
    basis = dict(policy='my_company_foreign_direct_ya2026', workpaper=p, prepaid_tax='120000',
        basis_confirmed=True, basis_explanation='Verified source expenses, taxable status and India bilateral credit')
    url = 'sqlite:///' + str(tmp_path/'my-foreign.sqlite')
    service = SimpleNamespace(store=ChatStore(url))
    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user] = fixture_user
    app.dependency_overrides[chat.get_service] = lambda: service
    headers = {'x-asiatax-request': '1'}
    try:
        with TestClient(app) as client:
            client.get('/api/auth/session')
            created = client.post('/api/cases', headers=headers)
            assert created.status_code == 201, created.text
            path = f"/api/cases/{created.json()['id']}/income-tax"
            saved = client.put(path, headers=headers, json=dict(revision=0, request_id=str(uuid4()),
                inputs=case.model_dump(mode='json')))
            assert saved.status_code == 200, saved.text
            request = dict(revision=saved.json()['revision'], request_id=str(uuid4()), basis=basis)
            response = client.post(path+'/runs', headers=headers, json=request)
            assert response.status_code == 200, response.text
            run = response.json()
            assert Decimal(run['result']['final_tax']) == 117300
            assert Decimal(run['result']['balance_due']) == -2700
            reports = {}
            for locale in ('en', 'zh'):
                report = client.get(path+'/runs/'+run['id']+'/report?locale='+locale)
                assert report.status_code == 200, report.text
                reports[locale] = report.json()['markdown']
                assert run['snapshot_hash'] in reports[locale]
                assert ('Malaysia bilateral and unilateral credits' if locale == 'en' else '马来西亚双边及单边抵免') in reports[locale]
                assert ('Overall cap reduction' if locale == 'en' else '总税额上限调减') in reports[locale]
                assert '| business | IN |' in reports[locale]
                for source in run['result']['sources']:
                    assert source['sha256'] in reports[locale]
            service.store.engine.dispose()
            service.store = ChatStore(url)
            assert client.get(path+'/runs/'+run['id']).json() == run
            assert client.post(path+'/runs', headers=headers, json=request).json() == run
            current = client.get(path).json()
            invalid = deepcopy(request)
            invalid.update(revision=current['revision'], request_id=str(uuid4()))
            invalid['basis']['workpaper']['groups'][0]['receipts'][1]['eligible_foreign_tax'] = '7501'
            rejected = client.post(path+'/runs', headers=headers, json=invalid)
            assert rejected.status_code == 422, rejected.text
            assert client.get(path).json() == current
            for locale, original in reports.items():
                assert client.get(path+'/runs/'+run['id']+'/report?locale='+locale).json()['markdown'] == original
    finally:
        service.store.engine.dispose()
