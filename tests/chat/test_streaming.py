import asyncio
import json
from uuid import uuid4

import httpx
import pytest

from packages.chat import streaming
from packages.chat.service import ChatService, WorkflowError
from packages.chat.store import ChatStore
from packages.model_adapter.client import ModelConfig


def test_reply_prefix_handles_escaped_strings_and_key_order():
    text = 'Hello "world"\n你好 😀'
    raw = json.dumps({'facts': {}, 'intent': 'chat', 'reply': text, 'query': ''})
    seen = ''
    for length in range(len(raw) + 1):
        value = streaming.reply_prefix(raw[:length])
        if value:
            assert text.startswith(value)
            assert value.startswith(seen)
            seen = value
    assert seen == text
    assert streaming.reply_prefix('{"query":"fake \\"reply\\": hi"') == ''


def test_real_provider_stream_emits_before_completion_and_closes_on_cancel(monkeypatch):
    async def run():
        closed = asyncio.Event()
        class Body(httpx.AsyncByteStream):
            async def __aiter__(self):
                chunk = {'choices': [{'delta': {'content': '{"intent":"chat","reply":"Hello'}, 'finish_reason': None}]}
                yield ('data: ' + json.dumps(chunk) + '\n\n').encode()
                await asyncio.Event().wait()
            async def aclose(self):
                closed.set()
        transport = httpx.MockTransport(lambda request: httpx.Response(200, stream=Body()))
        original = httpx.AsyncClient
        monkeypatch.setattr(streaming.httpx, 'AsyncClient', lambda **kw: original(transport=transport, **kw))
        monkeypatch.setattr(streaming, 'current_model_config', lambda: ModelConfig('https://model.test', 'fixture', 'fixture'))
        monkeypatch.setattr(streaming, 'turn_prompt', lambda *_: ('system', 'user'))
        stream = streaming.model_turn({}, 'hello')
        assert await anext(stream) == {'type': 'delta', 'text': 'Hello'}
        pending = asyncio.create_task(anext(stream))
        await asyncio.sleep(0)
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        await stream.aclose()
        assert closed.is_set()
    asyncio.run(run())


@pytest.mark.parametrize('finish,expected', [('stop', True), ('length', False)])
def test_model_stream_requires_complete_validated_json(monkeypatch, finish, expected):
    raw = json.dumps({'intent': 'chat', 'reply': 'Hello', 'facts': {}, 'query': ''})
    chunk = {'choices': [{'delta': {'content': raw}, 'finish_reason': finish}]}
    content = ('data: ' + json.dumps(chunk) + '\n\ndata: [DONE]\n\n').encode()
    original = httpx.AsyncClient
    monkeypatch.setattr(streaming.httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(lambda _: httpx.Response(200, content=content)), **kw))
    monkeypatch.setattr(streaming, 'current_model_config', lambda: ModelConfig('https://model.test', 'fixture', 'fixture'))
    monkeypatch.setattr(streaming, 'turn_prompt', lambda *_: ('system', 'user'))
    async def run():
        return [event async for event in streaming.model_turn({}, 'hello')]
    if expected:
        assert asyncio.run(run())[-1]['turn']['reply'] == 'Hello'
    else:
        with pytest.raises(WorkflowError):
            asyncio.run(run())


def test_disconnection_during_retrieval_never_commits(tmp_path):
    store = ChatStore(f"sqlite:///{(tmp_path / 'stream.sqlite').as_posix()}")
    disconnected = False
    def research(_):
        nonlocal disconnected
        disconnected = True
        return {'status': 'available', 'passages': []}
    service = ChatService(store, researcher=research, turner=lambda *_: {'intent': 'research', 'reply': 'Checking', 'facts': {}, 'query': 'FSIE'})
    doc = store.create('a')
    async def gone(): return disconnected
    async def run():
        return [event async for event in streaming.events(service, doc, 'a', 0, str(uuid4()), 'FSIE', gone)]
    try:
        assert asyncio.run(run()) == []
        assert store.get('a', doc['id'])['revision'] == 0
        assert store.get('a', doc['id'])['messages'] == []
    finally:
        store.engine.dispose()


def test_retry_resets_partial_answer_before_second_attempt(monkeypatch):
    attempts = []
    async def one(*_):
        attempts.append(1)
        if len(attempts) == 1:
            yield {'type': 'delta', 'text': 'incomplete'}
            raise WorkflowError('model_failed')
        yield {'type': 'turn', 'turn': {'intent': 'chat', 'reply': 'Complete', 'facts': {}, 'query': ''}}
    monkeypatch.setattr(streaming, '_model_turn_once', one)
    async def run():
        return [e async for e in streaming.model_turn({}, 'hello')]
    events = asyncio.run(run())
    assert [e['type'] for e in events] == ['delta', 'reset', 'turn']
    assert len(attempts) == 2


def test_cancel_during_summary_does_not_commit(tmp_path, monkeypatch):
    from packages.chat import answers
    async def run():
        started, closed = asyncio.Event(), asyncio.Event()
        async def turn(*_):
            yield {'type': 'turn', 'turn': {'intent': 'research', 'reply': 'Check', 'facts': {}, 'query': 'FSIE'}}
        async def summary(*_):
            started.set()
            try:
                await asyncio.Event().wait()
            finally:
                closed.set()
        monkeypatch.setattr(streaming, 'model_turn', turn)
        monkeypatch.setattr(answers, 'compose_async', summary)
        store = ChatStore(f"sqlite:///{(tmp_path / 'summary.sqlite').as_posix()}")
        service = ChatService(store, researcher=lambda _: {'status': 'available', 'passages': []})
        doc = store.create('a')
        async def connected(): return False
        stream = streaming.events(service, doc, 'a', 0, str(uuid4()), 'FSIE', connected)
        try:
            task = asyncio.create_task(anext(stream))
            await asyncio.wait_for(started.wait(), 3)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert closed.is_set()
            assert store.get('a', doc['id'])['messages'] == []
            assert store.get('a', doc['id'])['revision'] == 0
        finally:
            await stream.aclose()
            store.engine.dispose()
    asyncio.run(run())
