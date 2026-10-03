"""Supabase email authentication. Credentials never enter the application database."""
from __future__ import annotations

from pathlib import Path
from uuid import UUID
from urllib.parse import urlsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

router = APIRouter(prefix="/api/auth")
ACCESS = "taxora_access"
REFRESH = "taxora_refresh"


class AuthSettings(BaseSettings):
    supabase_url: str = ""
    publishable_key: str = ""
    site_url: str = "http://127.0.0.1:8000"
    secure_cookie: bool = False
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[2] / '.env', env_prefix="FSIE_AUTH_", extra="ignore")

    @property
    def configured(self):
        if not self.supabase_url or not self.publishable_key:
            return False
        if self.publishable_key.startswith('sb_secret_'):
            return False
        # Reject privileged legacy JWT keys if pasted into the public-key setting.
        if self.publishable_key.count('.') == 2:
            import base64
            import json
            try:
                payload = self.publishable_key.split('.')[1]
                role = json.loads(base64.urlsafe_b64decode(payload + '=' * (-len(payload) % 4))).get('role')
                if role != 'anon':
                    return False
            except (ValueError, TypeError):
                return False
        return urlsplit(self.supabase_url).scheme == 'https'


def settings():
    return AuthSettings()


def same_origin(request: Request):
    if request.headers.get('sec-fetch-site') == 'cross-site':
        raise HTTPException(403, 'origin_rejected')
    origin = request.headers.get('origin')
    if origin and urlsplit(origin).netloc != request.headers.get('host'):
        raise HTTPException(403, 'origin_rejected')
    if request.method not in ('GET', 'HEAD') and request.headers.get('x-asiatax-request') != '1':
        raise HTTPException(403, 'request_header_required')


def provider(path: str, method='GET', body=None, token=None):
    cfg = settings()
    if not cfg.configured:
        raise HTTPException(503, 'auth_not_configured')
    # The fixed, administrator-configured project origin is never supplied by a client.
    if urlsplit(cfg.supabase_url).scheme != 'https':
        raise HTTPException(503, 'auth_not_configured')
    headers = {'apikey': cfg.publishable_key}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    try:
        with httpx.Client(timeout=15, follow_redirects=False) as client:
            result = client.request(method, cfg.supabase_url.rstrip('/') + '/auth/v1/' + path,
                                    headers=headers, json=body)
        data = result.json()
    except (httpx.HTTPError, ValueError):
        raise HTTPException(503, 'auth_unavailable') from None
    if not result.is_success:
        code = data.get('error_code') or data.get('code') if isinstance(data, dict) else ''
        if result.status_code == 429:
            raise HTTPException(429, 'auth_rate_limited')
        if code in ('email_not_confirmed',):
            raise HTTPException(401, 'email_not_confirmed')
        if code in ('weak_password', 'same_password'):
            raise HTTPException(422, 'password_rejected')
        if result.status_code >= 500:
            raise HTTPException(503, 'auth_unavailable')
        raise HTTPException(401 if result.status_code in (400, 401, 403, 422) else 503,
                            'auth_invalid' if result.status_code < 500 else 'auth_unavailable')
    if not isinstance(data, dict):
        raise HTTPException(503, 'auth_unavailable')
    return data


def identity(data):
    try:
        uid = str(UUID(data['id']))
    except (KeyError, ValueError, TypeError):
        raise HTTPException(401, 'auth_invalid') from None
    if not data.get('email_confirmed_at'):
        raise HTTPException(401, 'email_not_confirmed')
    return {'id': uid, 'email': data.get('email', '')}


def set_session(response: Response, data):
    if not data.get('access_token') or not data.get('refresh_token'):
        raise HTTPException(401, 'auth_invalid')
    cfg = settings()
    # Retain the expired access token so the next request can refresh the session.
    for name, value in ((ACCESS, data['access_token']), (REFRESH, data['refresh_token'])):
        response.set_cookie(name, value, httponly=True, secure=cfg.secure_cookie,
                            samesite='lax', max_age=60 * 60 * 24 * 30, path='/')


def optional_user(request: Request, response: Response):
    same_origin(request)
    access = request.cookies.get(ACCESS)
    refresh = request.cookies.get(REFRESH)
    if not access and not refresh:
        return None
    if access:
        try:
            return identity(provider('user', token=access))
        except HTTPException as exc:
            if exc.status_code != 401:
                raise
    if not refresh:
        return None
    try:
        data = provider('token?grant_type=refresh_token', 'POST', {'refresh_token': refresh})
        user = identity(provider('user', token=data.get('access_token')))
        set_session(response, data)
        return user
    except HTTPException as exc:
        if exc.status_code != 401:
            raise
        response.delete_cookie(ACCESS, path='/')
        response.delete_cookie(REFRESH, path='/')
        return None


def required_user(user=Depends(optional_user)):
    if not user:
        raise HTTPException(401, 'login_required')
    return user


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    password: str = Field(min_length=1, max_length=128)


class Email(BaseModel):
    email: str = Field(min_length=3, max_length=254, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


class Password(BaseModel):
    password: str = Field(min_length=8, max_length=128)


class Tokens(BaseModel):
    access_token: str = Field(min_length=10, max_length=8192)
    refresh_token: str = Field(min_length=10, max_length=8192)


@router.get('/session')
def session(user=Depends(optional_user)):
    return {'configured': settings().configured, 'user': user}


@router.post('/login', dependencies=[Depends(same_origin)])
def login(body: Credentials, response: Response):
    data = provider('token?grant_type=password', 'POST', body.model_dump())
    user = identity(provider('user', token=data.get('access_token')))
    set_session(response, data)
    return {'user': user}


@router.post('/signup', dependencies=[Depends(same_origin)])
def signup(body: Credentials):
    if len(body.password) < 8:
        raise HTTPException(422, 'password_rejected')
    from urllib.parse import quote
    redirect = quote(settings().site_url.rstrip('/') + '/', safe='')
    try:
        provider('signup?redirect_to=' + redirect, 'POST', body.model_dump())
    except HTTPException as exc:
        # Do not disclose whether this email is already registered.
        if exc.detail != 'auth_invalid':
            raise
    return {'status': 'check_email'}


@router.post('/recover', dependencies=[Depends(same_origin)])
def recover(body: Email):
    from urllib.parse import quote
    redirect = quote(settings().site_url.rstrip('/') + '/?reset=1', safe='')
    provider('recover?redirect_to=' + redirect, 'POST', body.model_dump())
    return {'status': 'check_email'}


@router.post('/resend', dependencies=[Depends(same_origin)])
def resend(body: Email):
    from urllib.parse import quote
    redirect = quote(settings().site_url.rstrip('/') + '/', safe='')
    try:
        provider('resend?redirect_to=' + redirect, 'POST',
                 {'type': 'signup', 'email': body.email})
    except HTTPException as exc:
        # Do not expose whether the address exists or is already confirmed.
        # Supabase enforces mail rate limits; outages and 429s remain actionable.
        if exc.detail != 'auth_invalid':
            raise
    return {'status': 'check_email'}


@router.post('/callback', dependencies=[Depends(same_origin)])
def callback(body: Tokens, response: Response):
    # Exchange the provided refresh token and verify identity remotely before trusting it.
    supplied = identity(provider('user', token=body.access_token))
    data = provider('token?grant_type=refresh_token', 'POST', {'refresh_token': body.refresh_token})
    user = identity(provider('user', token=data.get('access_token')))
    if user['id'] != supplied['id']:
        raise HTTPException(401, 'auth_invalid')
    set_session(response, data)
    return {'user': user}


@router.post('/password', dependencies=[Depends(same_origin)])
def password(body: Password, request: Request, user=Depends(required_user)):
    # Obtain a fresh token explicitly; the request cookie itself can be expired.
    data = provider('token?grant_type=refresh_token', 'POST', {'refresh_token': request.cookies.get(REFRESH, '')})
    provider('user', 'PUT', body.model_dump(), token=data['access_token'])
    response = Response(content='{"status":"updated"}', media_type='application/json')
    set_session(response, data)
    return response


@router.post('/logout', dependencies=[Depends(same_origin)])
def logout(request: Request, response: Response):
    if request.cookies.get(ACCESS):
        try:
            provider('logout?scope=local', 'POST', token=request.cookies[ACCESS])
        except HTTPException:
            # Local logout must still work if the provider cannot be reached.
            pass
    response.delete_cookie(ACCESS, path='/')
    response.delete_cookie(REFRESH, path='/')
    return {'status': 'signed_out'}
