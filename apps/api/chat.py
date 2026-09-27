"""Local research API. Browser workspaces are isolated by opaque cookies."""
from __future__ import annotations

from functools import lru_cache
from hashlib import sha256
from pathlib import Path
import secrets
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.exc import SQLAlchemyError

from packages.chat.facts import catalog
from packages.chat.service import ChatService, WorkflowError, public, current_model_config
from packages.chat.store import CaseNotFound, ChatStore, RevisionConflict

ROOT = Path(__file__).resolve().parents[2]
COOKIE = "asiatax_workspace"
router = APIRouter(prefix="/api")


class WebSettings(BaseSettings):
    database_url: str = f"sqlite:///{(ROOT / 'data/chat.sqlite3').as_posix()}"
    secure_cookie: bool = False
    model_config = SettingsConfigDict(env_file=ROOT / ".env", env_prefix="FSIE_WEB_", extra="ignore")


@lru_cache
def get_service() -> ChatService:
    return ChatService(ChatStore(WebSettings().database_url))


def same_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "origin_rejected")
    if origin and urlsplit(origin).netloc != request.headers.get("host"):
        raise HTTPException(403, "origin_rejected")
    if request.method not in ("GET", "HEAD") and request.headers.get("x-asiatax-request") != "1":
        raise HTTPException(403, "request_header_required")


def owner(request: Request) -> str:
    same_origin(request)
    token = request.cookies.get(COOKIE, "")
    if len(token) != 64 or any(c not in "0123456789abcdef" for c in token):
        raise HTTPException(401, "workspace_required")
    return sha256(token.encode()).hexdigest()


class Mutation(BaseModel):
    revision: int = Field(ge=0)
    request_id: UUID


class Message(Mutation):
    text: str = Field(min_length=1, max_length=4000)
    data_approved: bool = False


class FactEdit(Mutation):
    facts: dict[str, Any] = Field(max_length=42)


def call(action, *args):
    try:
        return action(*args)
    except CaseNotFound:
        raise HTTPException(404, "case_not_found") from None
    except RevisionConflict:
        raise HTTPException(409, "revision_conflict") from None
    except WorkflowError as exc:
        raise HTTPException(503 if exc.code.startswith("model_") else 422, exc.code) from None
    except (ValueError, TypeError):
        raise HTTPException(422, "invalid_facts") from None
    except SQLAlchemyError:
        raise HTTPException(503, "storage_unavailable") from None


@router.get("/session")
def session(request: Request, response: Response):
    same_origin(request)
    token = request.cookies.get(COOKIE, "")
    if len(token) != 64 or any(c not in "0123456789abcdef" for c in token):
        response.set_cookie(COOKIE, secrets.token_hex(32), httponly=True, samesite="strict",
                            secure=WebSettings().secure_cookie, max_age=60 * 60 * 24 * 180)
    return {"model_configured": current_model_config().is_configured, "fields": catalog()}


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
def message(case_id: UUID, body: Message, workspace: str = Depends(owner), service: ChatService = Depends(get_service)):
    text = body.text.strip()
    if not text:
        raise HTTPException(422, "empty_message")
    return call(service.message, workspace, str(case_id), body.revision, str(body.request_id), text, body.data_approved)


@router.patch("/cases/{case_id}/facts")
def facts(case_id: UUID, body: FactEdit, workspace: str = Depends(owner), service: ChatService = Depends(get_service)):
    return call(service.edit, workspace, str(case_id), body.revision, str(body.request_id), body.facts)


@router.post("/cases/{case_id}/confirm")
def confirm(case_id: UUID, body: Mutation, workspace: str = Depends(owner), service: ChatService = Depends(get_service)):
    return call(service.confirm, workspace, str(case_id), body.revision, str(body.request_id))


@router.post("/cases/{case_id}/analyze")
def run(case_id: UUID, body: Mutation, workspace: str = Depends(owner), service: ChatService = Depends(get_service)):
    return call(service.run, workspace, str(case_id), body.revision, str(body.request_id))
