"""A trickled response must not bypass the hybrid transport deadline."""
import json

import httpx
import pytest

from packages.model_adapter import client as model_client
from packages.agent import providers


class ModelResponse:
    def __init__(self, chunks):
        self.chunks = iter(chunks)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read1(self, _):
        return next(self.chunks, b'')


def test_model_deadline_rejects_trickled_body(monkeypatch):
    ticks = iter([0, .1, .4, .8])
    monkeypatch.setattr(model_client.time, 'monotonic', lambda: next(ticks))
    monkeypatch.setattr(model_client.urllib.request, 'urlopen',
                        lambda *_args, **_kwargs: ModelResponse([b'{', b'"slow":']))
    config = model_client.ModelConfig('https://fixture.invalid/v1', 'fixture', 'fixture',
                                     max_retries=0, total_timeout_seconds=.5)
    with pytest.raises(model_client.ModelError, match='total deadline'):
        model_client.OpenAICompatibleClient(config)._post('/chat/completions', {})


def test_model_deadline_accepts_complete_chunked_json(monkeypatch):
    monkeypatch.setattr(model_client.time, 'monotonic', lambda: 0)
    monkeypatch.setattr(model_client.urllib.request, 'urlopen',
                        lambda *_args, **_kwargs: ModelResponse([b'{"ok":', b'true}']))
    config = model_client.ModelConfig('https://fixture.invalid/v1', 'fixture', 'fixture',
                                     max_retries=0, total_timeout_seconds=.5)
    assert model_client.OpenAICompatibleClient(config)._post('/chat/completions', {}) == {'ok': True}


def test_c_deadline_rejects_trickled_body(monkeypatch):
    class SlowBody(httpx.SyncByteStream):
        def __iter__(self):
            yield b'{'
            yield b'"slow":true}'
    ticks = iter([0, .1, .8])
    monkeypatch.setattr(providers, 'monotonic', lambda: next(ticks))
    transport = httpx.MockTransport(lambda _: httpx.Response(200, stream=SlowBody()))
    provider = providers.CKnowledgeProvider('http://127.0.0.1', transport=transport)
    with pytest.raises(httpx.TimeoutException, match='total deadline'):
        provider._post('/search', json.loads('{}'), .5)
