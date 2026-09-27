import json
from uuid import uuid4

import pytest

from packages.chat import service
from packages.chat.store import ChatStore
from packages.model_adapter.client import ModelConfig


def test_chat_does_not_search_or_invalidate_and_keeps_history(tmp_path):
    store = ChatStore(f'sqlite:///{tmp_path.as_posix()}/chat.sqlite')
    seen = []
    def turn(doc, text):
        seen.append(doc['messages'][:])
        return {'intent': 'chat', 'facts': {}, 'reply': 'A natural model reply.', 'query': ''}
    def search(_):
        pytest.fail('Normal conversation must not access the knowledge database')
    chat = service.ChatService(store, turner=turn, researcher=search)
    doc = store.create('owner')
    doc = chat.edit('owner', doc['id'], doc['revision'], str(uuid4()), {'income_type': 'dividend'})
    doc = chat.confirm('owner', doc['id'], doc['revision'], str(uuid4()))
    confirmed = doc['confirmed_revision']
    request_id, revision = str(uuid4()), doc['revision']
    doc = chat.message('owner', doc['id'], revision, request_id, 'Hello', True)
    assert doc['messages'][-1]['kind'] == 'chat'
    assert doc['confirmed_revision'] == confirmed and doc['state'] == 'confirmed'
    assert chat.message('owner', doc['id'], revision, request_id, 'Hello', True) == doc
    doc = chat.message('owner', doc['id'], doc['revision'], str(uuid4()), 'Continue', True)
    assert seen[-1][-1]['text'] == 'A natural model reply.'
    assert doc['facts']['income_type']['value'] == 'dividend'
    assert store.get('owner', doc['id'])['messages'] == doc['messages']
    assert store.list('other-owner') == []
    store.engine.dispose()


def test_model_turn_receives_both_roles_but_never_raw_documents(monkeypatch):
    monkeypatch.setattr(service, 'current_model_config', lambda: ModelConfig('https://example.invalid', 'secret', 'test'))
    class Client:
        def __init__(self, *_): pass
        def chat_json(self, system, user, **kwargs):
            assert 'SECRET_ORIGINAL' not in user
            context = json.loads(user)
            assert context['recent_conversation'][1]['text'] == 'Previous assistant reply'
            assert context['latest_user_message'] == 'Say that in English'
            return {'intent': 'chat', 'reply': 'Here it is in English.', 'facts': {}, 'query': ''}
    monkeypatch.setattr(service, 'OpenAICompatibleClient', Client)
    doc = {'facts': {}, 'messages': [
        {'role': 'user', 'text': 'Earlier question'},
        {'role': 'assistant', 'kind': 'chat', 'text': 'Previous assistant reply'},
        {'role': 'assistant', 'kind': 'research', 'research': {'status': 'available', 'query': 'Case 68',
                                                             'passages': [{'text': 'SECRET_ORIGINAL'}]}},
    ]}
    assert service.plan_turn(doc, 'Say that in English')['intent'] == 'chat'


@pytest.mark.parametrize('turn', [
    {'intent': 'approved', 'reply': 'Approved', 'facts': {}, 'query': ''},
    {'intent': 'chat', 'reply': 'Hi', 'facts': {'income_type': 'dividend'}, 'query': ''},
    {'intent': 'chat', 'reply': '', 'facts': {}, 'query': ''},
    {'intent': 'research', 'reply': 'Search', 'facts': {}, 'query': ''},
    {'intent': 'intake', 'reply': 'Done', 'facts': {'expert_decision_status': 'approved'}, 'query': ''},
])
def test_invalid_turns_cannot_change_workflow(monkeypatch, turn):
    monkeypatch.setattr(service, 'current_model_config', lambda: ModelConfig('https://example.invalid', 'secret', 'test'))
    class Client:
        def __init__(self, *_): pass
        def chat_json(self, *_, **kwargs): return turn
    monkeypatch.setattr(service, 'OpenAICompatibleClient', Client)
    with pytest.raises(service.WorkflowError, match='model_failed'):
        service.plan_turn({'facts': {}, 'messages': []}, 'Hello')


def test_model_failure_is_atomic(tmp_path):
    store = ChatStore(f'sqlite:///{tmp_path.as_posix()}/chat.sqlite')
    def fail(*_): raise service.WorkflowError('model_failed')
    chat = service.ChatService(store, turner=fail)
    doc = store.create('owner')
    with pytest.raises(service.WorkflowError):
        chat.message('owner', doc['id'], 0, str(uuid4()), 'Hello', True)
    assert store.get('owner', doc['id']) == doc
    store.engine.dispose()
