"""Bounded, owner-scoped PDF jobs with snapshot checks and race-safe cancellation."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from threading import RLock
from time import time
from uuid import uuid4

from packages.chat.service import WorkflowError, public
from packages.chat.store import RevisionConflict
from packages.consultation.workflow import CORE, ROOT, fingerprint
from packages.consultation.pdf import render_pdf


class ReportJobs:
    def __init__(self, directory=None, renderer=render_pdf):
        self.directory = Path(directory or ROOT / 'data/consultation_reports')
        self.renderer = renderer
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='consultation-pdf')
        self.lock = RLock()
        self.jobs = {}

    def _persist(self, job):
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / (job['id'] + '.json')
        temporary = path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(job, ensure_ascii=False))
        temporary.replace(path)

    def _get(self, owner, case_id, job_id):
        job = self.jobs.get(job_id)
        if job is None:
            path = self.directory / (job_id + '.json')
            if not path.exists(): raise WorkflowError('report_not_found')
            job = json.loads(path.read_text())
            if job['status'] in ('queued', 'running'):
                job.update(status='failed', progress=0, message='服务重启，生成任务已中断，请重新生成。', error='report_interrupted')
                self._persist(job)
            self.jobs[job_id] = job
        if job['owner_hash'] != sha256(owner.encode()).hexdigest() or job['case_id'] != case_id:
            raise WorkflowError('report_not_found')
        if time() > job['expires_at'] and job['status'] not in ('cancelled', 'expired'):
            job.update(status='expired', message='报告已过期，请重新生成。')
            (self.directory / (job_id + '.pdf')).unlink(missing_ok=True)
            self._persist(job)
        return job

    @staticmethod
    def wire(job):
        return {k: v for k, v in job.items() if k not in ('owner_hash', 'case_id')}

    def start(self, store, owner, case_id, revision, expected_hash, consent):
        if not consent: raise WorkflowError('report_confirmation_required')
        with self.lock:
            doc = deepcopy(store.get(owner, case_id))
            brief = doc.get('consultation', {})
            if not expected_hash or brief.get('stage') != 'ready' or brief.get('conflicts') or any(k not in brief.get('facts', {}) for k in CORE):
                raise WorkflowError('consultation_not_ready')
            if expected_hash != fingerprint(brief) or expected_hash != brief.get('analyzed_hash'):
                raise WorkflowError('report_snapshot_changed')
            old = brief.get('report_job')
            if old:
                job = self._get(owner, case_id, old)
                if job['input_hash'] == expected_hash and job['status'] in ('queued', 'running', 'ready'):
                    return public(doc), self.wire(job)
            if doc['revision'] != revision: raise RevisionConflict()
            if sum(j['status'] in ('queued', 'running') for j in self.jobs.values()) >= 8:
                raise WorkflowError('report_busy')
            job_id = str(uuid4())
            job = {'id': job_id, 'owner_hash': sha256(owner.encode()).hexdigest(), 'case_id': case_id,
                   'input_hash': expected_hash, 'status': 'queued', 'progress': 5, 'message': '已确认，等待生成',
                   'created_at': datetime.now(timezone.utc).isoformat(), 'expires_at': time() + 86400}
            brief.update(report_job=job_id, generation_consent=expected_hash)
            store.save(owner, doc, revision)
            self.jobs[job_id] = job
            self._persist(job)
            self.pool.submit(self._run, job_id, deepcopy(brief))
            return public(doc), self.wire(job)

    def _run(self, job_id, snapshot):
        temporary = self.directory / (job_id + '.part.pdf')
        def update(progress, message):
            with self.lock:
                job = self.jobs[job_id]
                if job['status'] == 'cancelled': raise InterruptedError()
                job.update(status='running', progress=progress, message=message)
                self._persist(job)
        try:
            update(15, '冻结用户资料、工具结果和规则版本')
            self.renderer(snapshot, temporary, update)
            update(94, '检查 PDF 页数与文档完整性')
            from pypdf import PdfReader
            if len(PdfReader(temporary).pages) != 5: raise ValueError('unexpected_page_count')
            with self.lock:
                job = self.jobs[job_id]
                if job['status'] == 'cancelled': raise InterruptedError()
                temporary.replace(self.directory / (job_id + '.pdf'))
                job.update(status='ready', progress=100, message='咨询简报生成完成', pages=5)
                self._persist(job)
        except InterruptedError:
            pass
        except Exception:
            with self.lock:
                job = self.jobs[job_id]
                if job['status'] != 'cancelled':
                    job.update(status='failed', message='PDF 生成失败，请重试。', error='report_generation_failed')
                    self._persist(job)
        finally:
            temporary.unlink(missing_ok=True)

    def get(self, store, owner, case_id, job_id):
        doc = store.get(owner, case_id)
        with self.lock:
            job = self._get(owner, case_id, job_id)
            return {**self.wire(job), 'stale': fingerprint(doc.get('consultation', {})) != job['input_hash']}

    def download(self, store, owner, case_id, job_id):
        with self.lock:
            job = self.get(store, owner, case_id, job_id)
            if job.get('stale'): raise WorkflowError('report_snapshot_changed')
            if job['status'] != 'ready': raise WorkflowError('report_not_ready')
            return (self.directory / (job_id + '.pdf')).read_bytes()

    def cancel(self, store, owner, case_id, job_id):
        store.get(owner, case_id)
        with self.lock:
            job = self._get(owner, case_id, job_id)
            job.update(status='cancelled', progress=0, message='已取消下载并删除服务器上的 PDF。')
            (self.directory / (job_id + '.pdf')).unlink(missing_ok=True)
            self._persist(job)
            return self.wire(job)


jobs = ReportJobs()
