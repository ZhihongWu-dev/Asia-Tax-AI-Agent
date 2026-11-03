"""Isolated browser server: real upload/PDF/storage, synthetic model/calculation boundary."""
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
os.environ['FSIE_ACTIVE_WORKFLOW'] = 'brief'
os.environ['FSIE_AGENT_PROVIDER'] = 'legacy'
os.environ['FSIE_AGENT_LOG_DIR'] = 'off'

import uvicorn
from apps.api.main import app
from apps.api import auth, consultation
from apps.api.chat import get_service, get_provider
from packages.chat.service import ChatService
from packages.chat.store import ChatStore
from packages.consultation import workflow
from packages.consultation.reports import ReportJobs
from tests.chat.auth_support import fixture_user
from tests.consultation.fixtures import fake_model, fake_calculate, fake_research

if __name__ == '__main__':
    with TemporaryDirectory(prefix='taxrora-brief-browser-') as directory:
        store = ChatStore(f'sqlite:///{directory}/cases.sqlite')
        jobs = ReportJobs(Path(directory) / 'reports')
        consultation.jobs = jobs
        workflow.model, workflow.calculate, workflow.research = fake_model, fake_calculate, fake_research
        app.dependency_overrides[auth.optional_user] = fixture_user
        auth.settings = lambda: auth.AuthSettings(supabase_url='https://fixture.supabase.co', publishable_key='fixture')
        app.dependency_overrides[get_service] = lambda: ChatService(store)
        app.dependency_overrides[get_provider] = lambda: None
        try:
            uvicorn.run(app, host='127.0.0.1', port=int(os.environ.get('FSIE_TEST_API_PORT', '8012')), log_level='warning')
        finally:
            jobs.pool.shutdown(); store.engine.dispose()
