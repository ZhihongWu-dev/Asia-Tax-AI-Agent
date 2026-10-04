"""Browser-test-only server: real API/storage/rules, deterministic model boundary.

Never imported by the application or normal startup scripts.
"""
import sys
import os
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import uvicorn
from apps.api.main import app
from apps.api import auth
from tests.chat.auth_support import fixture_user
from apps.api.chat import get_service
from packages.chat import analysis
from packages.chat import knowledge
from packages.chat.service import ChatService, WorkflowError
from packages.chat.store import ChatStore

attempts = {}


def extract(doc, text):
    key = (doc['id'], text)
    attempts[key] = attempts.get(key, 0) + 1
    if text == 'RETRY_TEST' and attempts[key] == 1:
        raise WorkflowError('model_failed')
    if text == 'CONFLICT_TEST':
        return {'income_type': 'dividend', 'entity_hk_business_status': 'conflict'}
    if text == 'FOLLOW_UP':
        return {'mne_group_status': 'yes', 'source_analysis': 'foreign_sourced'}
    if text == 'Case 68':
        return {}
    return {'income_type': 'dividend', 'entity_hk_business_status': 'yes', 'dividend_amount': 100000}


if __name__ == '__main__':
    app.dependency_overrides[auth.optional_user] = fixture_user
    auth.settings = lambda: auth.AuthSettings(supabase_url='https://fixture.supabase.co', publishable_key='fixture')
    with TemporaryDirectory(prefix='asiatax-browser-') as directory:
        # Optional persistent storage for manual local walkthroughs; automated tests stay isolated.
        database_path = Path(os.environ.get('FSIE_TEST_DATABASE_PATH', str(Path(directory) / 'cases.sqlite'))).resolve()
        store = ChatStore(f"sqlite:///{database_path.as_posix()}")
        analysis.retrieve_units = lambda _: ([], 'unavailable')
        analysis.related_rulings = lambda _: {'status': 'unavailable', 'passages': []}
        knowledge.read_documents = lambda **_: [{
            'unit_id': 'hk_ird_advance_68:section7', 'source_id': 'hk_ird_advance_68',
            'locator': None, 'unit_type': 'ruling_block', 'ordinal': 7,
            'heading': '7. Date of ruling issued', 'text': 'Synthetic browser fixture: date retained.',
            'title': 'Browser test ruling', 'url': 'https://www.ird.gov.hk/eng/ppr/advance68.htm',
            'drift': True, 'snapshot_sha256': 'a' * 64, 'text_sha256': 'b' * 64,
            'retrieved_at': '2026-09-27T00:00:00+00:00', 'coverage_cutoff': '2026-08-15',
        }]
        def turn(doc, text):
            if text == 'STREAM_TEST':
                import time
                time.sleep(3)
                return {'intent': 'chat', 'reply': 'First live chunk and final chunk', 'facts': {}, 'query': ''}
            if text == 'MARKDOWN_TEST':
                return {'intent': 'chat', 'reply': '## Summary\n\n- First item\n- Second item\n\n| Item | Value |\n| --- | --- |\n| Test | 100 |\n\n<script>alert(1)</script>\n\n[Unsafe](javascript:alert(1))', 'facts': {}, 'query': ''}
            if text == '你好':
                return {'intent': 'chat', 'reply': '你好！今天想聊些什么？', 'facts': {}, 'query': ''}
            if text == '用英文再说一遍':
                return {'intent': 'chat', 'reply': 'Hello! What would you like to talk about today?', 'facts': {}, 'query': ''}
            patch = extract(doc, text)
            return {'intent': 'intake' if patch else 'research', 'reply': '', 'facts': patch, 'query': text}
        async def stream_turn(doc, text):
            if text == 'STREAM_TEST':
                yield {'type': 'delta', 'text': 'First live chunk'}
                await asyncio.sleep(3)
                yield {'type': 'delta', 'text': ' and final chunk'}
                yield {'type': 'turn', 'turn': {'intent': 'chat', 'reply': 'First live chunk and final chunk', 'facts': {}, 'query': ''}}
            else:
                yield {'type': 'turn', 'turn': turn(doc, text)}
        def browser_service():
            service = ChatService(store, turner=turn,
                                  orchestration=os.environ.get('FSIE_TEST_ORCHESTRATION', 'hybrid'),
                                  dynamic_planner=False)
            service.streamer = stream_turn
            return service
        app.dependency_overrides[get_service] = browser_service
        try:
            uvicorn.run(app, host='127.0.0.1', port=int(os.environ.get('FSIE_TEST_API_PORT', '8001')), log_level='warning')
        finally:
            store.engine.dispose()
