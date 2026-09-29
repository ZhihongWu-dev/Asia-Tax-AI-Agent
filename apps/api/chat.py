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
from packages.chat.knowledge import search

ROOT = Path(__file__).resolve().parents[2]
router = APIRouter(prefix="/api")


class WebSettings(BaseSettings):
    database_url: str = ""
    secure_cookie: bool = False
    model_config = SettingsConfigDict(env_file=ROOT / ".env", env_prefix="FSIE_WEB_", extra="ignore")


@lru_cache
def get_service() -> ChatService:
    return ChatService(ChatStore(WebSettings().database_url or get_settings().database_url))


def owner(user=Depends(required_user)) -> str:
    return "user:" + user["id"]


class Mutation(BaseModel):
    revision: int = Field(ge=0)
    request_id: UUID


class Message(Mutation):
    text: str = Field(min_length=1, max_length=4000)
    data_approved: bool = False


class FactEdit(Mutation):
    facts: dict[str, Any] = Field(max_length=42)


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
        raise HTTPException(503 if exc.code.startswith("model_") or exc.code == 'knowledge_unavailable' else 422, exc.code) from None
    except (ValueError, TypeError):
        raise HTTPException(422, "invalid_facts") from None
    except SQLAlchemyError:
        raise HTTPException(503, "storage_unavailable") from None


@router.get("/session")
def session(user=Depends(required_user)):
    return {"model_configured": current_model_config().is_configured, "fields": catalog()}


@router.get('/knowledge/search')
def knowledge_search(q: str = Query(min_length=2, max_length=500),
                     kind: Literal['all', 'law', 'ruling', 'guidance'] = 'all',
                     workspace: str = Depends(owner)):
    result = search(q.strip(), kind, 7)
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
        return await asyncio.to_thread(call, service.message, workspace, str(case_id), body.revision, str(body.request_id), text, body.data_approved)
    doc, duplicate = await asyncio.to_thread(call, service.load, workspace, str(case_id), body.revision, str(body.request_id))
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
            async with asyncio.timeout(90), aclosing(events(service, doc, workspace, body.revision, str(body.request_id), text, request.is_disconnected)) as stream:
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
