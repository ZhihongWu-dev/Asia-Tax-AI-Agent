"""Engine/session helpers. Importing this module registers every ORM mapper."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from packages.persistence import models  # noqa: F401  (registers mappers on Base)
from packages.persistence.base import Base
from packages.persistence.config import get_settings


def make_engine(database_url: str | None = None) -> Engine:
    return create_engine(database_url or get_settings().database_url, future=True)


@contextmanager
def session_scope(engine: Engine | None = None) -> Iterator[Session]:
    own_engine = engine or make_engine()
    factory = sessionmaker(bind=own_engine, future=True, expire_on_commit=False)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        if engine is None:
            own_engine.dispose()


__all__ = ["Base", "make_engine", "session_scope"]
