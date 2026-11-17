"""Korean ordinary company calculations through saved case and HTTP contracts."""
from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import TypeAdapter, ValidationError

from apps.api import auth, chat
from packages.chat.store import ChatStore
from packages.contracts.income_assessment import Assessment
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.assessment import calculate
from tests.chat.auth_support import fixture_user


def inputs():
    return dict(subject='company', jurisdiction='kr', currency='KRW',
        residency='resident', period_start='2026-01-01', period_end='2026-12-31',
        facts_confirmed=True, claimed_deductions='0', carried_losses='0',
        incomes=[dict(category='business', source_jurisdiction='kr',
                      gross_amount='100000000', description='Annual ordinary income')])


def basis():
    adjustment = dict.fromkeys(('relief', 'penalty', 'additional_tax', 'other_payments',
        'rate_adjustment_increase', 'rate_adjustment_decrease'), '0')
    return dict(policy='kr_company_ordinary_2026', basis_confirmed=True,
        basis_explanation='Reconciled ordinary income and independently established local tax base.',
        national_taxable_base='100000000', local_taxable_base='200000000',
        ordinary_domestic_scope_confirmed=True,
        national_inputs=dict(minimum_regime='general', article60_2_1_1_company=False,
            reliefs=[], annual_standard_schedule_confirmed=True, minimum_regime_verified=True,
            eligibility_caps_and_expiry_verified=True, no_base_changing_incentives=True,
            additions_and_payments_verified=True, penalty_tax='0', relief_recapture='0',
            interim_tax='11000000', occasional_assessment_tax='0', withheld_tax='0', installment=False),
        local_inputs=dict(total_withheld='0', filing_ratios={'HQ': '0.6', 'Branch': '0.4'},
            adjustments={'HQ': deepcopy(adjustment), 'Branch': deepcopy(adjustment)},
            head_office='HQ', initial_return_and_filing_groups_verified=True,
            relief_caps_rate_adjustments_and_payments_verified=True, installment=False))


def run(data=None, payload=None):
    return calculate(IncomeTaxCase(**(data or inputs())),
                     TypeAdapter(Assessment).validate_python(payload or basis()))


def test_independent_bases_and_authorities_do_not_net_refunds_against_payments():
    result = run()
    assert Decimal(result['national']['gross_tax']) == 10000000
    assert Decimal(result['total_refundable']) == 1000000
    assert Decimal(result['total_payable']) == 2000000
    assert result['tax_scope'] == 'ordinary_national_and_local_corporate_income_tax'
    assert result['sources']


@pytest.mark.parametrize('change', [dict(subject='individual'), dict(residency='nonresident'),
    dict(period_start='2025-01-01'), dict(claimed_deductions='1'), dict(facts_confirmed=False)])
def test_saved_case_mismatch_rejected(change):
    data = inputs(); data.update(change)
    with pytest.raises(ValueError):
        run(data)


@pytest.mark.parametrize('change', [dict(category='capital_gain'),
    dict(source_jurisdiction='jp'), dict(foreign_tax_paid='1')])
def test_unhandled_income_is_not_silently_taxed(change):
    data = inputs(); data['incomes'][0].update(change)
    with pytest.raises(ValueError):
        run(data)


@pytest.mark.parametrize('ratio', [0.6, '0.600000001', '1.1', '-0.1'])
def test_ratio_contract_preserves_decimal_precision(ratio):
    payload = basis(); payload['local_inputs']['filing_ratios']['HQ'] = ratio
    with pytest.raises(ValidationError):
        run(payload=payload)


def test_api_persists_separate_balances_and_rejects_unverified_scope(tmp_path):
    url = 'sqlite:///' + str(tmp_path / 'kr.sqlite')
    service = SimpleNamespace(store=ChatStore(url))
    app = FastAPI(); app.include_router(auth.router); app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user] = fixture_user
    app.dependency_overrides[chat.get_service] = lambda: service
    headers = {'x-asiatax-request': '1'}
    with TestClient(app) as client:
        client.get('/api/auth/session')
        case_id = client.post('/api/cases', headers=headers).json()['id']
        path = f'/api/cases/{case_id}/income-tax'
        assert client.put(path, headers=headers, json=dict(revision=0,
            request_id=str(uuid4()), inputs=inputs())).status_code == 200
        payload = basis(); payload['ordinary_domestic_scope_confirmed'] = False
        request = dict(revision=1, request_id=str(uuid4()), basis=payload)
        assert client.post(path+'/runs', headers=headers, json=request).status_code == 422
        request.update(request_id=str(uuid4()), basis=basis())
        response = client.post(path+'/runs', headers=headers, json=request)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result['status'] == 'calculated_basis'
        assert Decimal(result['result']['total_payable']) == 2000000
        assert Decimal(result['result']['total_refundable']) == 1000000
        service.store.engine.dispose(); service.store = ChatStore(url)
        assert client.get(path+'/runs/'+result['id']).json() == result
        assert client.post(path+'/runs', headers=headers, json=request).json() == result
    service.store.engine.dispose()
