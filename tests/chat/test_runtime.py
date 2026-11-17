"""Shared startup uses the same validated configuration and owns its child."""
from contextlib import contextmanager
import json
import os
from types import SimpleNamespace
import pytest
from packages import runtime
from scripts import combined_runtime


@pytest.fixture
def defaults(tmp_path, monkeypatch):
    (tmp_path / 'config').mkdir()
    config = {'FSIE_AGENT_ORCHESTRATION': 'hybrid', 'FSIE_AGENT_DYNAMIC_PLANNER': 'true',
              'FSIE_AGENT_HARNESS_MODE': 'tools', 'FSIE_AGENT_PROVIDER': 'combined'}
    (tmp_path / 'config/runtime.json').write_text(json.dumps(config))
    for key in [*config, 'FSIE_AGENT_C_URL', 'FSIE_AGENT_C_TOKEN']:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(runtime, 'ROOT', tmp_path)
    return tmp_path


def test_combined_runtime_owns_service_and_restores_environment(defaults, monkeypatch):
    stopped = []
    @contextmanager
    def server(*, on_start):
        on_start(SimpleNamespace(poll=lambda: None))
        try:
            yield 'http://127.0.0.1:9999', 'temporary-test-token'
        finally:
            stopped.append(True)
    monkeypatch.setattr(combined_runtime, 'knowledge_server', server)
    with runtime.application_runtime() as state:
        assert state.public() == dict(orchestration='hybrid', provider='combined',
            dynamic_planner=True, harness_mode='tools', knowledge_ready=True)
        assert os.environ['FSIE_AGENT_C_TOKEN'] == 'temporary-test-token'
        assert 'temporary-test-token' not in str(state.public())
    assert stopped == [True]
    assert 'FSIE_AGENT_C_TOKEN' not in os.environ
    assert 'FSIE_AGENT_PROVIDER' not in os.environ


def test_explicit_environment_wins_over_local_and_shared_defaults(defaults, monkeypatch):
    (defaults / '.env').write_text('FSIE_AGENT_PROVIDER=combined\nFSIE_AGENT_DYNAMIC_PLANNER=false\n')
    monkeypatch.setenv('FSIE_AGENT_PROVIDER', 'legacy')
    monkeypatch.setattr(combined_runtime, 'knowledge_server', lambda **_: pytest.fail('No library for legacy'))
    with runtime.application_runtime() as state:
        assert state.provider == 'legacy'
        assert not state.dynamic_planner
    assert os.environ['FSIE_AGENT_PROVIDER'] == 'legacy'


def test_missing_combined_dependency_fails_startup_instead_of_falling_back(defaults, monkeypatch):
    @contextmanager
    def unavailable(**_):
        raise RuntimeError('release_unavailable')
        yield
    monkeypatch.setattr(combined_runtime, 'knowledge_server', unavailable)
    with pytest.raises(RuntimeError, match='release_unavailable'):
        with runtime.application_runtime():
            pytest.fail('Startup must fail')
    assert 'FSIE_AGENT_PROVIDER' not in os.environ


def test_health_fails_when_managed_library_exits(monkeypatch):
    from apps.api import main
    state = runtime.Runtime('hybrid', 'combined', True, 'tools',
                            SimpleNamespace(poll=lambda: 1))
    monkeypatch.setattr(main.app.state, 'runtime', state, raising=False)
    response = main.health(SimpleNamespace(app=main.app))
    assert response.status_code == 503
    data = json.loads(response.body)
    assert data['status'] == 'unavailable'
    assert data['runtime']['knowledge_ready'] is False
