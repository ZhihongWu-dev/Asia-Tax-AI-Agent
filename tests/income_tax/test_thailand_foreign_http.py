from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api import auth, chat
from packages.chat.store import ChatStore
from tests.chat.auth_support import fixture_user
from tests.income_tax.test_thailand_foreign_assessment import inputs


HEADERS = {'x-asiatax-request': '1'}


def test_foreign_assessment_http_owner_snapshot_replay_and_amendment(tmp_path):
    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(chat.router)
    store = ChatStore('sqlite:///' + str(tmp_path / 'thai-foreign.sqlite'))
    app.dependency_overrides[auth.optional_user] = fixture_user
    app.dependency_overrides[chat.get_service] = lambda: SimpleNamespace(store=store)
    with TestClient(app) as alice, TestClient(app) as bob, TestClient(app) as anonymous:
        alice.get('/api/auth/session')
        bob.get('/api/auth/session')
        created = alice.post('/api/cases', headers=HEADERS)
        assert created.status_code == 201
        case_id = created.json()['id']
        url = f'/api/cases/{case_id}/income-tax'
        case, basis = inputs()
        saved = alice.put(url, headers=HEADERS, json=dict(revision=0, request_id=str(uuid4()), inputs=case))
        assert saved.status_code == 200
        revision = saved.json()['revision']
        payload = dict(revision=revision, request_id=str(uuid4()), basis=basis)
        endpoint = url + '/runs'
        assert anonymous.post(endpoint, headers=HEADERS, json=payload).status_code == 401
        assert bob.post(endpoint, headers=HEADERS, json=payload).status_code == 404
        assert alice.post(endpoint, json=payload).status_code == 403
        invalid = deepcopy(payload)
        invalid['basis']['pools'][0]['previously_remitted_income'] = '1'
        rejected = alice.post(endpoint, headers=HEADERS, json=invalid)
        assert rejected.status_code == 422, rejected.text
        assert alice.get(url).json()['revision'] == revision
        result = alice.post(endpoint, headers=HEADERS, json=payload)
        assert result.status_code == 200, result.text
        run = result.json()
        assert run['input_revision'] == revision
        assert run['basis'] == basis
        assert Decimal(run['result']['gross_tax']) == 200000
        assert Decimal(run['result']['allowed_tax_credits']).quantize(Decimal('.01')) == Decimal('66666.67')
        assert alice.get(endpoint + '/' + run['id']).json() == run
        assert bob.get(endpoint + '/' + run['id']).status_code == 404
        assert anonymous.get(endpoint + '/' + run['id']).status_code == 401
        assert alice.post(endpoint, headers=HEADERS, json=payload).json() == run
        current = alice.get(url).json()
        assert current['revision'] == revision + 1
        conflicting = deepcopy(payload)
        conflicting['basis']['prepaid_tax'] = '0'
        assert alice.post(endpoint, headers=HEADERS, json=conflicting).status_code == 409
        stale = {**payload, 'request_id':str(uuid4())}
        assert alice.post(endpoint, headers=HEADERS, json=stale).status_code == 409
        case['claimed_deductions'] = '150000'
        amended = alice.put(url, headers=HEADERS, json=dict(revision=current['revision'],
            request_id=str(uuid4()), inputs=case))
        assert amended.status_code == 200
        assert amended.json()['income_tax_result'] is None
        assert alice.get(endpoint + '/' + run['id']).json() == run
        assert alice.post(endpoint, headers=HEADERS, json=payload).json() == run
        assert alice.get(url).json()['income_tax_result'] is None
    store.engine.dispose()
