"""Default dividend consultation API. All resources remain account/case scoped."""
from __future__ import annotations

import asyncio
import json
from functools import partial
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from apps.api.chat import Message, Mutation, call, owner, get_service, get_provider
from packages.chat.service import WorkflowError
from packages.chat.store import RevisionConflict
from packages.consultation import workflow
from packages.consultation.reports import jobs

router = APIRouter(prefix='/api/cases/{case_id}/brief')


def handle(action, *args, **kwargs):
    try: return call(partial(action, **kwargs), *args)
    except HTTPException as exc:
        if exc.detail == 'report_not_found': raise HTTPException(404, exc.detail) from None
        if exc.detail in ('report_snapshot_changed', 'report_not_ready', 'consultation_not_ready'):
            raise HTTPException(409, exc.detail) from None
        raise


@router.post('/messages')
async def message(case_id: UUID, body: Message, request: Request, workspace=Depends(owner),
                  service=Depends(get_service), provider=Depends(get_provider)):
    # Parse and authorize the case before opening an SSE stream.
    call(service.store.get, workspace, str(case_id))
    action = partial(workflow.message, service.store, provider, workspace, str(case_id), body.revision,
                     str(body.request_id), body.text, body.data_approved, body.locale)
    if 'text/event-stream' not in request.headers.get('accept', ''):
        return await asyncio.to_thread(handle, action)
    async def stream():
        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        def progress(text): loop.call_soon_threadsafe(queue.put_nowait, {'type': 'status', 'text': text})
        task = asyncio.create_task(asyncio.to_thread(handle, action, emit=progress))
        # The worker commits once; disconnect does not cause duplicate model calls or partial commits.
        yield ': connected\n\n'
        try:
            while not task.done():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=2)
                    yield 'data: ' + json.dumps(event, ensure_ascii=False) + '\n\n'
                except asyncio.TimeoutError:
                    yield ': working\n\n'
            result = await task
            yield 'data: ' + json.dumps({'type': 'done', 'case': result}, ensure_ascii=False) + '\n\n'
        except HTTPException as exc:
            yield 'data: ' + json.dumps({'type': 'error', 'code': exc.detail}) + '\n\n'
        finally:
            if not task.done():
                task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)
    return StreamingResponse(stream(), media_type='text/event-stream', headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


class Generate(Mutation):
    input_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    confirmed: bool = False


@router.post('/reports', status_code=202)
def generate(case_id: UUID, body: Generate, workspace=Depends(owner), service=Depends(get_service)):
    doc, job = handle(jobs.start, service.store, workspace, str(case_id), body.revision, body.input_hash, body.confirmed)
    return {'case': doc, 'job': job}


@router.get('/reports/{job_id}')
def status(case_id: UUID, job_id: UUID, workspace=Depends(owner), service=Depends(get_service)):
    return handle(jobs.get, service.store, workspace, str(case_id), str(job_id))


@router.get('/reports/{job_id}/download')
def download(case_id: UUID, job_id: UUID, workspace=Depends(owner), service=Depends(get_service)):
    data = handle(jobs.download, service.store, workspace, str(case_id), str(job_id))
    return Response(data, media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename="taxrora-brief-{job_id}.pdf"'})


@router.delete('/reports/{job_id}')
def cancel(case_id: UUID, job_id: UUID, workspace=Depends(owner), service=Depends(get_service)):
    return handle(jobs.cancel, service.store, workspace, str(case_id), str(job_id))
