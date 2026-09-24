"""Fresh-database migration round trip. Skipped unless FSIE_RUN_INTEGRATION=1.

Every other live test runs against a database that was migrated step by step,
so a baseline that only works incrementally goes unnoticed. This test creates a
throwaway database next to the configured one and checks that:

1. ``alembic upgrade head`` succeeds on an empty database;
2. the migrated schema matches the ORM (autogenerate finds no difference);
3. ``downgrade base`` then ``upgrade head`` round-trips cleanly.

Needs a role allowed to CREATE DATABASE (the local docker-compose role is).
"""

from __future__ import annotations

import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from packages.persistence import models  # noqa: F401  (register every table)
from packages.persistence.base import Base
from packages.persistence.config import get_settings

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("FSIE_RUN_INTEGRATION") != "1",
        reason="set FSIE_RUN_INTEGRATION=1 to run live-DB integration tests",
    ),
]

REPO_ROOT = Path(__file__).resolve().parents[2]


def _alembic(url: str, *args: str) -> None:
    env = dict(os.environ, FSIE_DATABASE_URL=url)
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"alembic {' '.join(args)} failed:\n{result.stderr[-3000:]}"


@pytest.fixture()
def fresh_database_url():
    base = make_url(get_settings().database_url)
    name = f"fsie_migrations_{uuid.uuid4().hex[:8]}"
    admin = create_engine(base.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    try:
        yield base.set(database=name).render_as_string(hide_password=False)
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


def _schema_diff(url: str) -> list:
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            context = MigrationContext.configure(conn, opts={"compare_type": True})
            return compare_metadata(context, Base.metadata)
    finally:
        engine.dispose()


def _user_tables(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names()) - {"alembic_version"}
    finally:
        engine.dispose()


def test_upgrade_head_on_an_empty_database_matches_the_orm(fresh_database_url):
    _alembic(fresh_database_url, "upgrade", "head")
    assert _user_tables(fresh_database_url) == set(Base.metadata.tables)
    assert _schema_diff(fresh_database_url) == []


def test_downgrade_base_then_upgrade_head_round_trips(fresh_database_url):
    _alembic(fresh_database_url, "upgrade", "head")
    _alembic(fresh_database_url, "downgrade", "base")
    assert _user_tables(fresh_database_url) == set()
    _alembic(fresh_database_url, "upgrade", "head")
    assert _schema_diff(fresh_database_url) == []
