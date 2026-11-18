from copy import deepcopy
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api import auth, chat
from packages.chat.store import ChatStore
from packages.contracts.income_tax import IncomeTaxCase
from tests.chat.auth_support import fixture_user
from tests.income_tax.test_vietnam_credit_case import inputs

HEADERS = {'x-asiatax-request': '1'}


def test_credit_snapshot_restart_replay_edit_and_authorization(tmp_path):
    url = 'sqlite:///' + str(tmp_path / 'cases.sqlite')
    service = SimpleNamespace(store=ChatStore(url))
    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user] = fixture_user
    app.dependency_overrides[chat.get_service] = lambda: service
    facts, lines = inputs()
    with TestClient(app) as alice, TestClient(app) as bob, TestClient(app) as anon:
        alice.get('/api/auth/session'); bob.get('/api/auth/session')
        case_id = alice.post('/api/cases', headers=HEADERS).json()['id']
        path = f'/api/cases/{case_id}/income-tax'
        assert alice.put(path, headers=HEADERS, json=dict(revision=0,
            request_id=str(uuid4()), inputs=facts)).status_code == 200
        request = dict(revision=1, request_id=str(uuid4()), basis=dict(lines=lines,
            dossier=dict(credit_types=['tax_sparing', 'indirect'], represented=False, documents=[])))
        endpoint = path + '/credit-workpapers'
        assert alice.get(endpoint).json()['workpapers'] == []
        assert anon.get(endpoint).status_code == 401
        assert bob.get(endpoint).status_code == 404
        assert anon.post(endpoint, headers=HEADERS, json=request).status_code == 401
        assert bob.post(endpoint, headers=HEADERS, json=request).status_code == 404
        assert alice.post(endpoint, json=request).status_code == 403
        response = alice.post(endpoint, headers=HEADERS, json=request)
        assert response.status_code == 200, response.text
        run = response.json()
        assert run['status'] == 'credit_workpaper'
        assert run['dossier_review']['document_inventory_complete'] is False
        assert run['inputs'] == IncomeTaxCase.model_validate(facts).model_dump(mode='json')
        assert 'final_tax' not in run['result']
        service.store.engine.dispose()
        service.store = ChatStore(url)
        saved = endpoint + '/' + run['id']
        assert alice.get(saved).json() == run
        listing = alice.get(endpoint).json()
        assert listing['revision'] == 2
        assert len(listing['workpapers']) == 1
        assert listing['workpapers'][0]['id'] == run['id']
        assert listing['workpapers'][0]['matches_current_income_facts'] is True
        assert listing['workpapers'][0]['document_inventory_complete'] is False
        assert listing['workpapers'][0]['all_foreign_items_assessed'] is True
        assert bob.get(saved).status_code == 404
        assert anon.get(saved).status_code == 401
        assert alice.post(endpoint, headers=HEADERS, json=request).json() == run
        conflict = deepcopy(request)
        conflict['basis']['lines'][0]['vietnam_tax_limit'] = '100'
        assert alice.post(endpoint, headers=HEADERS, json=conflict).status_code == 409
        view = alice.get(path).json()
        assert view['revision'] == 2
        assert view['income_tax_status'] == 'awaiting_rule_validation'
        assert view['income_tax_result'] is None
        facts['incomes'][1]['gross_amount'] = '2000'
        assert alice.put(path, headers=HEADERS, json=dict(revision=2,
            request_id=str(uuid4()), inputs=facts)).status_code == 200
        assert alice.get(saved).json() == run
        assert alice.post(endpoint, headers=HEADERS, json=request).json() == run
        stale = {**request, 'request_id': str(uuid4())}
        assert alice.post(endpoint, headers=HEADERS, json=stale).status_code == 409
        invalid = deepcopy(stale)
        invalid['revision'] = 3
        invalid['basis']['lines'][0]['income_index'] = 199
        assert alice.post(endpoint, headers=HEADERS, json=invalid).status_code == 422
        assert alice.get(path).json()['revision'] == 3
        assert alice.get(endpoint).json()['workpapers'][0]['matches_current_income_facts'] is False
    service.store.engine.dispose()
