"""Research API with account-scoped cloud cases."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import StreamingResponse
import asyncio
import json
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.exc import SQLAlchemyError

from apps.api.auth import required_user
from packages.chat.facts import catalog
from packages.chat.service import ChatService, WorkflowError, public, current_model_config
from packages.chat.store import CaseNotFound, ChatStore, RevisionConflict
from packages.persistence.config import get_settings

ROOT = Path(__file__).resolve().parents[2]
router = APIRouter(prefix="/api")


class WebSettings(BaseSettings):
    database_url: str = ""
    secure_cookie: bool = False
    model_config = SettingsConfigDict(env_file=ROOT / ".env", env_prefix="FSIE_WEB_", extra="ignore")


@lru_cache
def get_provider():
    from packages.agent.providers import configured_provider
    return configured_provider()


@lru_cache
def get_service() -> ChatService:
    return ChatService(ChatStore(WebSettings().database_url or get_settings().database_url), provider=get_provider())


def owner(user=Depends(required_user)) -> str:
    return "user:" + user["id"]


class Mutation(BaseModel):
    revision: int = Field(ge=0)
    request_id: UUID


class Message(Mutation):
    text: str = Field(min_length=1, max_length=50000)
    data_approved: bool = False
    entry_hint: Literal['auto', 'dividend_consultation', 'fact_intake', 'reference_lookup'] = 'auto'
    reply_to_question_id: str | None = Field(default=None, min_length=1, max_length=200)
    locale: Literal['zh', 'en'] = 'zh'


class FactEdit(Mutation):
    facts: dict[str, Any] = Field(max_length=len(catalog()))


class Organization(Mutation):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    archived: bool | None = None


def call(action, *args):
    try:
        return action(*args)
    except CaseNotFound:
        raise HTTPException(404, "case_not_found") from None
    except RevisionConflict:
        raise HTTPException(409, "revision_conflict") from None
    except WorkflowError as exc:
        if exc.code == "review_forbidden":
            raise HTTPException(403, exc.code) from None
        if exc.code in ('request_payload_conflict', 'question_changed'):
            raise HTTPException(409, exc.code) from None
        raise HTTPException(503 if exc.code.startswith("model_") or exc.code in (
            'knowledge_unavailable', 'execution_budget_exhausted', 'tool_failed',
            'domain_unavailable', 'domain_timeout', 'domain_execution_failed') else 422, exc.code) from None
    except (ValueError, TypeError):
        raise HTTPException(422, "invalid_facts") from None
    except SQLAlchemyError:
        raise HTTPException(503, "storage_unavailable") from None


_pdf_slots = asyncio.Semaphore(2)


@router.post('/attachments')
@router.post('/attachments/pdf')
async def upload_pdf(request: Request, filename: str = Query(min_length=1, max_length=200),
                     workspace: str = Depends(owner)):
    from packages.chat.attachments import MAX_BYTES, EXTENSIONS, read_document
    extension = Path(filename).suffix.lower()
    if extension not in EXTENSIONS or (request.url.path.endswith('/pdf') and extension != '.pdf'):
        raise HTTPException(422, 'attachment_type')
    if _pdf_slots.locked():
        raise HTTPException(429, 'pdf_busy')
    async with _pdf_slots:
        data = bytearray()
        try:
            async with asyncio.timeout(30):
                async for chunk in request.stream():
                    data.extend(chunk)
                    if len(data) > MAX_BYTES:
                        raise HTTPException(413, 'pdf_too_large')
        except TimeoutError:
            raise HTTPException(408, 'pdf_timeout') from None
        try:
            result = await read_document(bytes(data), extension)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
    return {**result, 'name': filename.replace('\\', '/').split('/')[-1]}


@router.get("/session")
def session(user=Depends(required_user)):
    from packages.agent.providers import ProviderSettings
    from packages.consultation.settings import brief_enabled
    return {"model_configured": current_model_config().is_configured, "workflow": "brief" if brief_enabled() else "legacy", "fields": catalog(),
            "can_review": user['id'] in ProviderSettings().reviewer_ids}


@router.get('/knowledge/search')
def knowledge_search(q: str = Query(min_length=2, max_length=500),
                     kind: Literal['all', 'law', 'ruling', 'guidance'] = 'all',
                     workspace: str = Depends(owner), provider=Depends(get_provider)):
    from packages.chat import expenses
    if expenses.should_handle({}, q):
        result = expenses.search(q.strip(), kind=kind)
        if result['status'] == 'unavailable':
            raise HTTPException(503, 'knowledge_unavailable')
        return result
    from packages.agent.contracts import SearchRequest, TrustedContext
    from packages.agent.knowledge import retrieve, display_result
    from uuid import uuid4
    result = display_result(call(retrieve, provider, SearchRequest(request_id=str(uuid4()), trace_id=str(uuid4()),
                           query=q.strip(), kind=kind), TrustedContext(owner=workspace)))
    if result['status'] == 'unavailable':
        raise HTTPException(503, 'knowledge_unavailable')
    return result


@router.get("/cases")
def cases(workspace: str = Depends(owner), service: ChatService = Depends(get_service)):
    return [public(doc) for doc in call(service.store.list, workspace)]


@router.post("/cases", status_code=201)
def create(workspace: str = Depends(owner), service: ChatService = Depends(get_service)):
    return public(call(service.store.create, workspace))


@router.get("/cases/{case_id}")
def get(case_id: UUID, workspace: str = Depends(owner), service: ChatService = Depends(get_service)):
    return public(call(service.store.get, workspace, str(case_id)))


@router.post("/cases/{case_id}/messages")
async def message(case_id: UUID, body: Message, request: Request, response: Response, workspace: str = Depends(owner), service: ChatService = Depends(get_service)):
    text = body.text.strip()
    if not text:
        raise HTTPException(422, "empty_message")
    if 'text/event-stream' not in request.headers.get('accept', ''):
        return await asyncio.to_thread(call, service.message, workspace, str(case_id), body.revision, str(body.request_id), text, body.data_approved,
                                       body.entry_hint, body.reply_to_question_id, body.locale)
    if (body.reply_to_question_id or '').startswith(('domain:', 'li:')) or text.startswith('结构答复：'):
        async def domain_events():
            yield ': connected\n\n'
            try:
                doc = await asyncio.to_thread(call, service.message, workspace, str(case_id), body.revision,
                    str(body.request_id), text, body.data_approved, body.entry_hint, body.reply_to_question_id, body.locale)
                yield 'data: ' + json.dumps({'type': 'done', 'case': doc}, ensure_ascii=False) + '\n\n'
            except HTTPException as exc:
                yield 'data: ' + json.dumps({'type': 'error', 'code': exc.detail}) + '\n\n'
        return StreamingResponse(domain_events(), media_type='text/event-stream',
                                 headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
    doc, duplicate = await asyncio.to_thread(call, service.load_message, workspace, str(case_id), body.revision, str(body.request_id),
                                            text, body.data_approved, body.entry_hint, body.reply_to_question_id, body.locale)
    if not duplicate:
        if not (doc['data_approved'] or body.data_approved):
            raise HTTPException(422, 'data_confirmation_required')
        if len(doc['messages']) >= 200:
            raise HTTPException(422, 'case_limit')
    async def generate():
        from contextlib import aclosing
        from packages.chat.streaming import events
        def encode(event):
            return 'data: ' + json.dumps(event, ensure_ascii=False) + '\n\n'
        yield ': connected\n\n'
        try:
            if duplicate:
                yield encode({'type': 'done', 'case': public(doc)})
                return
            async with asyncio.timeout(90), aclosing(events(service, doc, workspace, body.revision, str(body.request_id), text, request.is_disconnected,
                    entry_hint=body.entry_hint, reply_to_question_id=body.reply_to_question_id,
                    data_approved=body.data_approved, locale=body.locale)) as stream:
                async for event in stream:
                    yield encode(event)
        except RevisionConflict:
            yield encode({'type': 'error', 'code': 'revision_conflict'})
        except WorkflowError as exc:
            yield encode({'type': 'error', 'code': exc.code})
        except SQLAlchemyError:
            yield encode({'type': 'error', 'code': 'storage_unavailable'})
        except (ValueError, TypeError):
            yield encode({'type': 'error', 'code': 'model_failed'})
        except TimeoutError:
            yield encode({'type': 'error', 'code': 'model_failed'})
    result = StreamingResponse(generate(), media_type='text/event-stream',
                             headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
    result.raw_headers.extend((key, value) for key, value in response.raw_headers if key.lower() == b'set-cookie')
    return result


@router.patch("/cases/{case_id}/facts")
def facts(case_id: UUID, body: FactEdit, workspace: str = Depends(owner), service: ChatService = Depends(get_service)):
    return call(service.edit, workspace, str(case_id), body.revision, str(body.request_id), body.facts)


@router.patch('/cases/{case_id}/organization')
def organize(case_id: UUID, body: Organization, workspace: str = Depends(owner), service: ChatService = Depends(get_service)):
    changes = body.model_dump(exclude_none=True, exclude={'revision', 'request_id'})
    return call(service.organize, workspace, str(case_id), body.revision, str(body.request_id), changes)


@router.post("/cases/{case_id}/confirm")
def confirm(case_id: UUID, body: Mutation, workspace: str = Depends(owner), service: ChatService = Depends(get_service)):
    return call(service.confirm, workspace, str(case_id), body.revision, str(body.request_id))


@router.post("/cases/{case_id}/analyze")
def run(case_id: UUID, body: Mutation, workspace: str = Depends(owner), service: ChatService = Depends(get_service)):
    return call(service.run, workspace, str(case_id), body.revision, str(body.request_id))


class DomainSetup(Mutation):
    case_input: dict[str, Any]
    data_approved: bool = False
    mode: Literal['plan_structure', 'assess_current', 'review_paid'] = 'plan_structure'
    bindings: dict[str, str] = Field(default_factory=dict, max_length=50)


class DomainAnswer(Mutation):
    key: str = Field(min_length=1, max_length=200)
    kind: Literal['data', 'blocking', 'joint', 'action']
    value: str | float | bool
    question_id: str | None = None
    disposition: Literal['answer', 'defer'] = 'answer'


class BatchAnswer(BaseModel):
    key: str = Field(min_length=1, max_length=200)
    kind: Literal['data', 'blocking', 'joint', 'action']
    value: str | float | bool
    question_id: str


class DomainAnswers(Mutation):
    locale: Literal['zh', 'en'] = 'zh'
    answers: list[BatchAnswer] = Field(min_length=1, max_length=100)


@router.post('/cases/{case_id}/domain-answers')
def domain_answers(case_id: UUID, body: DomainAnswers, workspace: str = Depends(owner),
                   service: ChatService = Depends(get_service)):
    return call(service.domain_answers_batch, workspace, str(case_id), body.revision, str(body.request_id),
                [answer.model_dump() for answer in body.answers], body.locale)


@router.get('/domain/capabilities')
def domain_capabilities(workspace: str = Depends(owner)):
    from packages.domain_bridge.bridge import PINNED_COMMIT, DomainError, release_path, verify_release
    try:
        verify_release(release_path())
        ready = True
    except DomainError:
        ready = False
    return {'ready': ready, 'release': PINNED_COMMIT, 'supported_currencies': ['CNY'],
            'modes': ['plan_structure', 'assess_current', 'review_paid'], 'supported_templates':
            ['holding', 'ip', 'services', 'repatriation', 'financing', 'inbound_services']}


@router.put('/cases/{case_id}/domain-case')
def domain_setup(case_id: UUID, body: DomainSetup, workspace: str = Depends(owner),
                 service: ChatService = Depends(get_service)):
    return call(service.domain_setup, workspace, str(case_id), body.revision, str(body.request_id),
                body.case_input, body.data_approved, body.mode, body.bindings)


@router.post('/cases/{case_id}/domain-plan')
def domain_plan(case_id: UUID, body: Mutation, workspace: str = Depends(owner),
                service: ChatService = Depends(get_service)):
    return call(service.domain_plan, workspace, str(case_id), body.revision, str(body.request_id))


@router.post('/cases/{case_id}/domain-answer')
def domain_answer(case_id: UUID, body: DomainAnswer, workspace: str = Depends(owner),
                  service: ChatService = Depends(get_service)):
    return call(service.domain_answer, workspace, str(case_id), body.revision, str(body.request_id),
                body.key, body.kind, body.value, body.question_id, body.disposition)


@router.get('/cases/{case_id}/domain-draft')
def domain_draft(case_id: UUID, workspace: str = Depends(owner), service: ChatService = Depends(get_service)):
    from packages.domain_bridge.state import draft_from_legacy
    return draft_from_legacy(call(service.store.get, workspace, str(case_id)))


class DomainControl(Mutation):
    action: Literal['pause', 'resume']


@router.post('/cases/{case_id}/domain-control')
def domain_control(case_id: UUID, body: DomainControl, workspace: str = Depends(owner), service: ChatService = Depends(get_service)):
    return call(service.domain_control, workspace, str(case_id), body.revision, str(body.request_id), body.action)


@router.post('/cases/{case_id}/domain-confirm')
def domain_confirm(case_id: UUID, body: Mutation, workspace: str = Depends(owner), service: ChatService = Depends(get_service)):
    return call(service.domain_confirm, workspace, str(case_id), body.revision, str(body.request_id))


class DomainReport(Mutation):
    allow_partial: bool = False


@router.post('/cases/{case_id}/domain-report')
def domain_report(case_id: UUID, body: DomainReport, workspace: str = Depends(owner), service: ChatService = Depends(get_service)):
    return call(service.domain_report, workspace, str(case_id), body.revision, str(body.request_id), body.allow_partial)


class ProfessionalAnswer(Mutation):
    question_id: str
    value: str | list[str]
    reference: dict[str, str]


@router.post('/cases/{case_id}/domain-professional')
def domain_professional(case_id: UUID, body: ProfessionalAnswer, workspace: str = Depends(owner),
                        user=Depends(required_user), service: ChatService = Depends(get_service)):
    return call(service.domain_professional, workspace, str(case_id), body.revision, str(body.request_id),
                body.question_id, body.value, body.reference, user['id'])


@router.get('/cases/{case_id}/analyses/{report_id}/markdown')
def report_markdown(case_id: UUID, report_id: UUID, workspace: str = Depends(owner), service: ChatService = Depends(get_service)):
    doc = call(service.store.get, workspace, str(case_id))
    report = next((r for r in doc['analyses'] if r['id'] == str(report_id) and r.get('markdown')), None)
    if not report:
        raise HTTPException(404, 'report_not_found')
    return Response(report['markdown'], media_type='text/markdown; charset=utf-8',
                    headers={'Content-Disposition': 'attachment; filename=research-' + str(report_id) + '.md'})


class FinalReview(Mutation):
    report_hash: str = Field(pattern=r'^[a-f0-9]{64}$')
    decision: Literal['approved', 'changes_requested', 'unable_to_conclude']
    note: str = Field(min_length=1, max_length=4000)


@router.post('/cases/{case_id}/analyses/{report_id}/review')
def final_review(case_id: UUID, report_id: UUID, body: FinalReview,
                 user=Depends(required_user), service: ChatService = Depends(get_service)):
    return call(service.review, 'user:' + user['id'], str(case_id), body.revision,
                str(body.request_id), str(report_id), body.report_hash, user['id'], body.decision, body.note)
