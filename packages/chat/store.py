"""Portable local workspace storage; separate from the research knowledge DB."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import JSON, Column, Integer, MetaData, String, Table, create_engine, select, update, text

metadata = MetaData()
conversations = Table(
    "chat_cases", metadata,
    Column("id", String(36), primary_key=True),
    Column("owner", String(64), nullable=False, index=True),
    Column("revision", Integer, nullable=False),
    Column("document", JSON, nullable=False),
)


class RevisionConflict(Exception):
    pass


class CaseNotFound(Exception):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChatStore:
    def __init__(self, url: str):
        if url.startswith('postgresql://'):
            url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
        if url.startswith("sqlite:///"):
            path = url.removeprefix("sqlite:///")
            if path != ":memory:":
                Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(url, pool_pre_ping=True, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {'connect_timeout': 5})
        with self.engine.begin() as connection:
            metadata.create_all(connection)
            if connection.dialect.name == 'postgresql':
                connection.execute(text('ALTER TABLE chat_cases ENABLE ROW LEVEL SECURITY'))

    def create(self, owner: str) -> dict:
        doc = {"id": str(uuid4()), "title": "", "revision": 0, "state": "collecting",
               "messages": [], "facts": {}, "fact_history": [], "analyses": [],
               "confirmed_revision": None, "confirmed_facts": None, "receipts": {},
               "created_at": now(), "updated_at": now(), "data_approved": False}
        with self.engine.begin() as c:
            c.execute(conversations.insert().values(id=doc["id"], owner=owner, revision=0, document=doc))
        return doc

    def list(self, owner: str) -> list[dict]:
        with self.engine.connect() as c:
            docs = list(c.execute(select(conversations.c.document).where(conversations.c.owner == owner)).scalars())
        return sorted(docs, key=lambda d: d["updated_at"], reverse=True)

    def get(self, owner: str, case_id: str) -> dict:
        with self.engine.connect() as c:
            doc = c.execute(select(conversations.c.document).where(conversations.c.id == case_id, conversations.c.owner == owner)).scalar_one_or_none()
        if doc is None:
            raise CaseNotFound()
        return doc

    def save(self, owner: str, doc: dict, expected: int) -> dict:
        doc["revision"] = expected + 1
        doc["updated_at"] = now()
        with self.engine.begin() as c:
            result = c.execute(update(conversations).where(
                conversations.c.id == doc["id"], conversations.c.owner == owner,
                conversations.c.revision == expected,
            ).values(revision=doc["revision"], document=doc))
            if result.rowcount != 1:
                raise RevisionConflict()
        return doc
