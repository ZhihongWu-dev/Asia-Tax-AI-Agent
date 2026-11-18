import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api import atlas, auth
from packages.domain_bridge import atlas_service
from packages.chat.library_cloud import LibraryVersionChanged
from tests.chat.auth_support import fixture_user


def test_routes_require_login_validate_selectors_and_hide_internal_errors(monkeypatch):
    calls = []

    async def query(payload, *, expected_snapshot=None):
        calls.append(payload)
        if payload['operation'] == 'glossary':
            raise RuntimeError('private connection details')
        return {'operation': payload['operation'], 'snapshot': 'reviewed'}

    monkeypatch.setattr(atlas_service, 'query', query)
    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(atlas.router)
    app.dependency_overrides[auth.optional_user] = fixture_user
    with TestClient(app) as client:
        for path in ('map', 'country/cn', 'glossary', 'clause?cite_id=cn.law%231'):
            assert client.get('/api/atlas/' + path).status_code == 401
        assert not calls
        client.get('/api/auth/session')
        assert client.get('/api/atlas/map?date=2026-02-30').status_code == 422
        assert client.get('/api/atlas/country/xx').status_code == 404
        assert client.get('/api/atlas/clause?cite_id=bad').status_code == 422
        assert not calls
        for path in ('map?date=2026-11-18', 'country/cn', 'clause?cite_id=cn.law%231'):
            response = client.get('/api/atlas/' + path)
            assert response.status_code == 200, response.text
            assert response.json()['snapshot'] == 'reviewed'
        response = client.get('/api/atlas/glossary')
        assert response.status_code == 503
        assert response.json() == {'detail': 'atlas_unavailable'}


def test_service_rechecks_snapshot_after_execution(monkeypatch):
    calls = []
    version = {'uploaded_at': 'v1'}
    runtime = {'engine': {'citations': ['cn.law#1']}}

    def snapshot(*, expected_version=None):
        calls.append(('snapshot', expected_version))
        if expected_version:
            raise LibraryVersionChanged('changed')
        return version

    def read(citations, *, expected_version):
        assert citations == ['cn.law#1']
        assert expected_version == version
        calls.append(('read', None))
        return {'fixture': True}

    async def execute(request, bundle, *, expected_version):
        calls.append(('execute', None))
        return {'runtime': runtime, 'result': {'stale': True}}

    monkeypatch.setattr(atlas_service, 'current_library_snapshot', snapshot)
    monkeypatch.setattr(atlas_service, 'capture_atlas_runtime', lambda: runtime)
    monkeypatch.setattr(atlas_service, 'read_planning_bundle', read)
    monkeypatch.setattr(atlas_service, 'execute', execute)
    with pytest.raises(LibraryVersionChanged):
        asyncio.run(atlas_service.query({'operation': 'map'}))
    assert [item[0] for item in calls] == ['snapshot', 'read', 'execute', 'snapshot']


def test_cross_view_snapshot_mismatch_stops_before_reading_sources(monkeypatch):
    monkeypatch.setattr(atlas_service, 'current_library_snapshot', lambda: {'version': 'new'})
    monkeypatch.setattr(atlas_service, 'capture_atlas_runtime', lambda: {'engine': {}})
    def forbidden(*args, **kwargs):
        pytest.fail('must not read sources for a stale page')
    monkeypatch.setattr(atlas_service, 'read_planning_bundle', forbidden)
    with pytest.raises(LibraryVersionChanged):
        asyncio.run(atlas_service.query({'operation': 'country', 'code': 'cn'},
                                        expected_snapshot='a' * 64))
