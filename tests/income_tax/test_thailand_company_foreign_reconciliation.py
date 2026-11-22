from copy import deepcopy
from decimal import Decimal

import pytest

from packages.contracts.income_tax import IncomeTaxCase
from packages.contracts.income_assessment import THCompany
from packages.income_tax.assessment import calculate


def inputs():
    case = dict(subject='company', jurisdiction='th', currency='THB', residency='resident',
        period_start='2026-01-01', period_end='2026-12-31', claimed_deductions='600000',
        carried_losses='0', facts_confirmed=True, incomes=[
            dict(category='business', source_jurisdiction='th', gross_amount='2000000', description='Domestic business'),
            dict(category='royalty', source_jurisdiction='sg', gross_amount='1000000', foreign_tax_paid='250000', description='Foreign royalty')])
    basis = dict(policy='th_company_2026', net_taxable_profit='2400000', exempt_income='0',
        scheme='ordinary', sme_eligibility_confirmed=False, ordinary_treatment_confirmed=True,
        allowed_tax_credits='200000', prepaid_tax='300000', basis_confirmed=True,
        basis_explanation='Final country expense bases and RD300 election verified against payment evidence.',
        rd300_workpaper=dict(domestic_allowable_expenses='500000',
            thai_incorporation_and_rd300_election_verified=True,
            final_expense_bases_and_foreign_tax_deductions_verified=True,
            source_period_fx_and_certified_payment_evidence_verified=True,
            countries=[dict(basis=dict(country='sg', treatment='company_receipts',
                company_receipts='1000000', company_receipt_foreign_tax_paid='250000'),
                annual_allowable_expenses='100000', foreign_tax_in_annual_expenses='50000')]))
    return case, basis


def run(case, basis):
    return calculate(IncomeTaxCase(**case), THCompany(**basis))


def test_saved_royalty_expenses_credit_and_prepayment_reconcile():
    result = run(*inputs())
    assert Decimal(result['gross_tax']) == 480000
    assert Decimal(result['final_tax']) == 280000
    assert Decimal(result['balance_due']) == -20000
    row = result['foreign_credit_reconciliation']['country_reconciliation'][0]
    assert Decimal(row['uncredited_and_undeducted_foreign_tax']) == 0
    assert {s['doc_id'] for s in result['sources']} >= {'th.rd300.foreign-credit', 'th.notification65.foreign-credit'}


def business_inputs():
    case, basis = inputs()
    case['incomes'][1]['category'] = 'business'
    case['incomes'][1]['foreign_tax_paid'] = '300000'
    case['claimed_deductions'] = '1000000'
    basis.update(net_taxable_profit='2000000', allowed_tax_credits='100000')
    row = basis['rd300_workpaper']['countries'][0]
    row.update(annual_allowable_expenses='500000', foreign_tax_in_annual_expenses='200000',
        basis=dict(country='sg', treatment='business_net', business_revenue='1000000',
            business_allowable_expenses='500000', business_foreign_tax_paid='300000'))
    return case, basis


def test_final_business_expense_basis_used_for_country_limit():
    case, basis = business_inputs()
    result = run(case, basis)
    assert Decimal(result['final_tax']) == 300000
    assert Decimal(result['foreign_credit_reconciliation']['derived_rd300_exemption']) == 100000


def allocated_inputs():
    case, basis = business_inputs()
    basis['rd300_workpaper']['countries'][0]['business_tax_periods'] = [dict(
        evidence_reference='foreign-assessment-1', allocation=dict(
            foreign_period_start='2025-07-01', foreign_period_end='2026-06-30',
            thai_period_start='2026-01-01', thai_period_end='2026-12-31',
            foreign_tax_base='net_profit', total_foreign_period_basis='1000000',
            basis_in_overlapping_period='300000', foreign_tax_paid='200000',
            payment_date='2027-07-01', payment_date_market_thb_per_unit='5',
            thai_return_filed_on='2027-05-25', actual_period_basis_and_payment_evidence_verified=True))]
    return case, basis


def test_period_tax_reconciles_to_saved_income_year_not_payment_year():
    result = run(*allocated_inputs())
    row = result['foreign_credit_reconciliation']['country_reconciliation'][0]
    assert Decimal(row['foreign_tax_paid']) == 300000
    allocation = row['business_tax_period_allocations'][0]
    assert Decimal(allocation['foreign_tax_paid_thb']) == 1000000
    assert Decimal(allocation['tax_outside_thai_period']) == 700000
    assert allocation['amendment_required'] is True
    assert allocation['thai_period_end'] == '2026-12-31'
    assert Decimal(result['final_tax']) == 300000


def test_recurring_period_fractions_reconcile_before_rounding():
    case, basis = allocated_inputs()
    case['incomes'][1]['foreign_tax_paid'] = '1'
    basis['allowed_tax_credits'] = '1'
    row = basis['rd300_workpaper']['countries'][0]
    row['basis']['business_foreign_tax_paid'] = '1'
    row['foreign_tax_in_annual_expenses'] = '0'
    entry = row['business_tax_periods'][0]
    entry['allocation'].update(total_foreign_period_basis='3', basis_in_overlapping_period='1',
        foreign_tax_paid='1', payment_date_market_thb_per_unit='1')
    row['business_tax_periods'] = [dict(evidence_reference=f'assessment-{n}', allocation=deepcopy(entry['allocation'])) for n in range(3)]
    result = run(case, basis)
    assert Decimal(result['allowed_tax_credits']) == 1
    allocations = result['foreign_credit_reconciliation']['country_reconciliation'][0]['business_tax_period_allocations']
    assert all(a['exact_allocated_tax'] == dict(numerator='1', denominator='3') for a in allocations)


@pytest.mark.parametrize('change', ['amount','period','duplicate','unverified'])
def test_period_evidence_inconsistent_with_saved_case_rejected(change):
    case, basis = allocated_inputs()
    periods = basis['rd300_workpaper']['countries'][0]['business_tax_periods']
    if change == 'amount': periods[0]['allocation']['basis_in_overlapping_period'] = '300001'
    elif change == 'period': periods[0]['allocation']['thai_period_start'] = '2025-01-01'
    elif change == 'duplicate': periods.append(deepcopy(periods[0]))
    else: periods[0]['allocation']['actual_period_basis_and_payment_evidence_verified'] = False
    with pytest.raises(ValueError, match='reconcile|saved Thai|unique|require'):
        run(case, basis)


@pytest.mark.parametrize('change', ['double_deduction','paid_tax','gross','expenses','credit','missing_country','duplicate_country','election','sme','loss','exemption'])
def test_inconsistent_or_ineligible_workpapers_rejected(change):
    case, basis = inputs()
    work = basis['rd300_workpaper']
    row = work['countries'][0]
    if change == 'double_deduction': row['foreign_tax_in_annual_expenses'] = '50001'
    elif change == 'paid_tax': row['basis']['company_receipt_foreign_tax_paid'] = '249999'
    elif change == 'gross': row['basis']['company_receipts'] = '999999'
    elif change == 'expenses': row['annual_allowable_expenses'] = '99999'
    elif change == 'credit': basis['allowed_tax_credits'] = '199999'
    elif change == 'missing_country': row['basis']['country'] = 'jp'
    elif change == 'duplicate_country': work['countries'].append(deepcopy(row))
    elif change == 'election': work['thai_incorporation_and_rd300_election_verified'] = False
    elif change == 'sme': basis.update(scheme='sme', sme_eligibility_confirmed=True)
    elif change == 'loss': case['carried_losses'] = '1'
    elif change == 'exemption': basis['exempt_income'] = '1'
    with pytest.raises(ValueError, match='Credited|reconcile|Allowed credits|every saved|require'):
        run(case, basis)


def test_country_source_receipt_split_does_not_change_result():
    case, basis = inputs()
    expected = run(case, basis)
    case['incomes'][1].update(gross_amount='600000', foreign_tax_paid='150000')
    case['incomes'].append(dict(category='royalty', source_jurisdiction='sg',
        gross_amount='400000', foreign_tax_paid='100000', description='Second foreign royalty receipt'))
    assert run(case, basis) == expected


@pytest.mark.parametrize('with_periods', [False, True])
def test_api_persists_workpaper_reopens_and_rejects_double_deduction(tmp_path, with_periods):
    from types import SimpleNamespace
    from uuid import uuid4
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.api import auth, chat
    from packages.chat.store import ChatStore
    from tests.chat.auth_support import fixture_user
    case, basis = allocated_inputs() if with_periods else inputs()
    url = 'sqlite:///' + str(tmp_path/'thai-company.sqlite')
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
            assert created.status_code == 201
            path = f"/api/cases/{created.json()['id']}/income-tax"
            saved = client.put(path, headers=headers, json=dict(revision=0, request_id=str(uuid4()), inputs=case))
            assert saved.status_code == 200, saved.text
            request = dict(revision=saved.json()['revision'], request_id=str(uuid4()), basis=basis)
            response = client.post(path+'/runs', headers=headers, json=request)
            assert response.status_code == 200, response.text
            assessment = response.json()
            assert Decimal(assessment['result']['final_tax']) == (300000 if with_periods else 280000)
            reports = {}
            for locale in ('zh', 'en'):
                report = client.get(path+'/runs/'+assessment['id']+'/report?locale='+locale)
                assert report.status_code == 200
                reports[locale] = report.json()['markdown']
                assert ('泰国企业境外税款与费用核对' if locale == 'zh' else 'Thai company foreign tax and expense reconciliation') in reports[locale]
                table_row = next(line for line in reports[locale].splitlines() if line.startswith('| SG |'))
                values = [Decimal(v.strip().replace('\\', '')) for v in table_row.split('|')[2:-1]]
                assert values == ([1000000, 300000, 500000, 200000, 100000, 0] if with_periods else [1000000, 250000, 100000, 50000, 200000, 0])
                if with_periods:
                    assert ('境外经营税款期间分摊' if locale == 'zh' else 'Foreign business tax period allocation') in reports[locale]
                    assert r'2027\-07\-01' in reports[locale]
                for source in assessment['result']['sources']:
                    assert source['sha256'] in reports[locale]
            service.store.engine.dispose()
            service.store = ChatStore(url)
            assert client.get(path+'/runs/'+assessment['id']).json() == assessment
            assert client.post(path+'/runs', headers=headers, json=request).json() == assessment
            current = client.get(path).json()
            invalid = deepcopy(request)
            invalid.update(revision=current['revision'], request_id=str(uuid4()))
            invalid['basis']['rd300_workpaper']['countries'][0]['foreign_tax_in_annual_expenses'] = '200001' if with_periods else '50001'
            rejected = client.post(path+'/runs', headers=headers, json=invalid)
            assert rejected.status_code == 422, rejected.text
            assert client.get(path).json() == current
            for locale, original in reports.items():
                assert client.get(path+'/runs/'+assessment['id']+'/report?locale='+locale).json()['markdown'] == original
    finally:
        service.store.engine.dispose()
