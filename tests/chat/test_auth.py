from uuid import uuid4
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from apps.api import auth
from apps.api.chat import get_service
from apps.api.main import app
from packages.chat.service import ChatService
from packages.chat.store import ChatStore

HEADERS = {'x-asiatax-request': '1'}


@pytest.fixture
def clients(tmp_path, monkeypatch):
    users = {k: {'id': str(uuid4()), 'email': k+'@example.test', 'email_confirmed_at': '2026-09-28'} for k in ('alice', 'bob')}
    calls = []
    def remote(path, method='GET', body=None, token=None):
        calls.append((path, method))
        if path.startswith('token?grant_type=password'):
            k = body['email'].split('@')[0]
            if body['password'] != 'validpassword' or k not in users:
                raise HTTPException(401, 'auth_invalid')
            return {'access_token': k, 'refresh_token': k}
        if path.startswith('token?grant_type=refresh_token'):
            k = body['refresh_token']
            if k not in users: raise HTTPException(401, 'auth_invalid')
            return {'access_token': k, 'refresh_token': k}
        if path == 'user':
            if token not in users: raise HTTPException(401, 'auth_invalid')
            return users[token]
        return {}
    monkeypatch.setattr(auth, 'provider', remote)
    monkeypatch.setattr(auth, 'settings', lambda: auth.AuthSettings(supabase_url='https://example.supabase.co', publishable_key='public-test-key'))
    store = ChatStore(f"sqlite:///{(tmp_path/'auth.sqlite').as_posix()}")
    app.dependency_overrides[get_service] = lambda: ChatService(store)
    with TestClient(app) as a, TestClient(app) as b:
        yield a, b, users, calls
    app.dependency_overrides.clear()
    store.engine.dispose()


def login(client, name='alice'):
    return client.post('/api/auth/login', headers=HEADERS, json={'email':name+'@example.test','password':'validpassword'})


def test_unauthed_cookie_cannot_read_cloud_data(clients):
    a, _, _, _ = clients
    a.cookies.set('asiatax_workspace', 'a'*64)
    assert a.get('/api/cases').status_code == 401
    assert a.get('/api/session').status_code == 401


def test_identity_isolation_persistence_and_logout(clients):
    a,b,_,_=clients
    assert login(a).status_code == 200
    assert 'httponly' in login(a).headers['set-cookie'].lower()
    doc = a.post('/api/cases',headers=HEADERS).json()
    assert login(b,'bob').status_code == 200
    assert b.get('/api/cases').json() == []
    assert b.get('/api/cases/'+doc['id']).status_code == 404
    assert b.post('/api/cases/'+doc['id']+'/confirm',headers=HEADERS,json={'revision':0,'request_id':str(uuid4())}).status_code == 404
    assert login(b,'alice').status_code == 200
    assert b.get('/api/cases').json()[0]['id'] == doc['id']
    assert a.post('/api/auth/logout',headers=HEADERS).status_code == 200
    assert a.get('/api/cases').status_code == 401


def test_bad_login_and_csrf(clients):
    a,_,_,_=clients
    assert a.post('/api/auth/login',json={'email':'alice@example.test','password':'validpassword'}).status_code == 403
    assert a.post('/api/auth/login',headers={**HEADERS,'origin':'https://evil.test'},json={'email':'alice@example.test','password':'validpassword'}).status_code == 403
    assert a.post('/api/auth/login',headers=HEADERS,json={'email':'alice@example.test','password':'wrong'}).status_code == 401
    assert auth.ACCESS not in a.cookies


def test_expired_access_refreshes_only_with_valid_refresh(clients):
    a,_,_,_=clients
    a.cookies.set(auth.ACCESS, 'expired')
    a.cookies.set(auth.REFRESH, 'alice')
    response=a.get('/api/auth/session')
    assert response.status_code == 200
    assert response.json()['user']['email']=='alice@example.test'
    assert auth.ACCESS in response.headers['set-cookie']


def test_unconfirmed_user_never_gets_session(clients):
    a,_,users,_=clients
    users['alice']['email_confirmed_at']=None
    assert login(a).status_code==401
    assert auth.ACCESS not in a.cookies


def test_signup_recovery_and_password_validation(clients):
    a,_,_,calls=clients
    assert a.post('/api/auth/signup',headers=HEADERS,json={'email':'new@example.test','password':'short'}).status_code==422
    assert a.post('/api/auth/signup',headers=HEADERS,json={'email':'new@example.test','password':'longpassword'}).json()=={'status':'check_email'}
    assert a.post('/api/auth/recover',headers=HEADERS,json={'email':'new@example.test'}).status_code==200
    assert a.post('/api/auth/password',headers=HEADERS,json={'password':'newpassword'}).status_code==401
    login(a)
    assert a.post('/api/auth/password',headers=HEADERS,json={'password':'newpassword'}).status_code==200
    assert ('user','PUT') in calls


def test_provider_outage_never_falls_back_to_cookie_identity(clients, monkeypatch):
    a,_,_,_=clients
    login(a)
    def unavailable(*args, **kwargs):
        raise HTTPException(503, 'auth_unavailable')
    monkeypatch.setattr(auth, 'provider', unavailable)
    assert a.get('/api/cases').status_code == 503


def test_privileged_key_is_not_valid_public_configuration():
    assert not auth.AuthSettings(supabase_url='https://example.supabase.co',publishable_key='sb_secret_example').configured
    assert not auth.AuthSettings(supabase_url='http://example.supabase.co',publishable_key='sb_publishable_example').configured


def test_resend_validates_input_and_uses_fixed_signup_redirect(clients, monkeypatch):
    from urllib.parse import parse_qs, urlsplit
    a, _, _, _ = clients
    received = []
    def remote(path, method='GET', body=None, token=None):
        received.append((path, method, body))
        return {}
    monkeypatch.setattr(auth, 'provider', remote)
    assert a.post('/api/auth/resend', json={'email': 'a@example.test'}).status_code == 403
    assert a.post('/api/auth/resend', headers=HEADERS, json={'email': 'invalid'}).status_code == 422
    assert not received
    result = a.post('/api/auth/resend', headers=HEADERS,
                    json={'email': 'a@example.test', 'redirect_to': 'https://evil.test'})
    assert result.json() == {'status': 'check_email'}
    path, method, body = received[0]
    assert path.startswith('resend?') and method == 'POST'
    assert body == {'type': 'signup', 'email': 'a@example.test'}
    assert parse_qs(urlsplit(path).query)['redirect_to'] == [auth.settings().site_url.rstrip('/') + '/']
    assert auth.ACCESS not in a.cookies


def test_organization_is_account_scoped_idempotent_and_reversible(clients):
    a, b, _, _ = clients
    login(a); login(b, 'bob')
    doc = a.post('/api/cases', headers=HEADERS).json()
    url = '/api/cases/' + doc['id'] + '/organization'
    body = {'revision': 0, 'request_id': str(uuid4()), 'title': 'Research', 'archived': True}
    assert b.patch(url, headers=HEADERS, json=body).status_code == 404
    result = a.patch(url, headers=HEADERS, json=body).json()
    assert result['title'] == 'Research' and result['archived'] is True
    assert a.patch(url, headers=HEADERS, json=body).json()['revision'] == 1
    assert a.patch(url, headers=HEADERS, json={**body, 'request_id': str(uuid4())}).status_code == 409
    restored = a.patch(url, headers=HEADERS, json={'revision': 1, 'request_id': str(uuid4()), 'archived': False}).json()
    assert restored['archived'] is False
    assert a.get('/api/cases/' + doc['id']).json()['title'] == 'Research'


@pytest.mark.parametrize('status,detail,expected', [
    (401, 'auth_invalid', 200), (429, 'auth_rate_limited', 429),
    (503, 'auth_unavailable', 503),
])
def test_resend_hides_account_state_but_preserves_operational_errors(clients, monkeypatch, status, detail, expected):
    a, _, _, _ = clients
    def remote(*args, **kwargs):
        raise HTTPException(status, detail)
    monkeypatch.setattr(auth, 'provider', remote)
    result = a.post('/api/auth/resend', headers=HEADERS, json={'email': 'a@example.test'})
    assert result.status_code == expected
    assert result.json() == ({'status': 'check_email'} if expected == 200 else {'detail': detail})
