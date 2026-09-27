"""Browser-test-only server: real API/storage/rules, deterministic model boundary.

Never imported by the application or normal startup scripts.
"""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import uvicorn
from apps.api.main import app
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
    with TemporaryDirectory(prefix='asiatax-browser-') as directory:
        store = ChatStore(f"sqlite:///{Path(directory).as_posix()}/cases.sqlite")
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
        app.dependency_overrides[get_service] = lambda: ChatService(store, extractor=extract)
        try:
            uvicorn.run(app, host='127.0.0.1', port=8001, log_level='warning')
        finally:
            store.engine.dispose()
