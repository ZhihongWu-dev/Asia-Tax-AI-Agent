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
    return {'income_type': 'dividend', 'entity_hk_business_status': 'yes', 'dividend_amount': 100000}


if __name__ == '__main__':
    with TemporaryDirectory(prefix='asiatax-browser-') as directory:
        store = ChatStore(f"sqlite:///{Path(directory).as_posix()}/cases.sqlite")
        analysis.retrieve_units = lambda _: ([], 'unavailable')
        app.dependency_overrides[get_service] = lambda: ChatService(store, extractor=extract)
        try:
            uvicorn.run(app, host='127.0.0.1', port=8001, log_level='warning')
        finally:
            store.engine.dispose()
