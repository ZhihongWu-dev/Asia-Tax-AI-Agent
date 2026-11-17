"""Worker lifecycle; schema deployment is deliberately separate from startup."""
import asyncio
import signal
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine, select

from packages.domain_bridge.planning_executor import execute_job
from packages.domain_bridge.planning_store import PlanningStore, LeaseLost, runs
from packages.domain_bridge.planning_worker import run_once


class WorkerSettings(BaseSettings):
    database_url: str = Field(default='', validation_alias='FSIE_DATABASE_URL')
    web_database_url: str = Field(default='', validation_alias='FSIE_WEB_DATABASE_URL')
    poll_seconds: float = Field(default=2, ge=.1, le=60)
    lease_seconds: int = Field(default=60, ge=5, le=3600)
    wall_seconds: int = Field(default=1800, ge=1, le=86400)
    max_attempts: int = Field(default=3, ge=1, le=10)
    model_config = SettingsConfigDict(env_file=Path(__file__).resolve().parents[2]/'.env',
                                     env_prefix='FSIE_PLANNING_', extra='ignore')


async def serve(store, settings, *, once=False):
    while True:
        try:
            completed = await run_once(store, execute_job, lease_seconds=settings.lease_seconds,
                                       wall_seconds=settings.wall_seconds, max_attempts=settings.max_attempts)
        except LeaseLost:
            # Another owner may now hold the lease. Never finish its attempt.
            completed = None
        if once:
            return
        if completed is None:
            await asyncio.sleep(settings.poll_seconds)


async def with_shutdown(store, settings, *, once=False):
    loop = asyncio.get_running_loop()
    task = asyncio.current_task()
    previous = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGTERM, lambda *_: loop.call_soon_threadsafe(task.cancel))
    try:
        await serve(store, settings, once=once)
    finally:
        signal.signal(signal.SIGTERM, previous)


def start(*, once=False):
    settings = WorkerSettings()
    url = settings.web_database_url or settings.database_url
    if not url:
        raise ValueError('planning_database_required')
    if url.startswith('postgresql://'):
        url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
    options = {'connect_timeout': 5, 'options': '-c statement_timeout=10000'} if url.startswith('postgresql') else {}
    engine = create_engine(url, pool_pre_ping=True, connect_args=options)
    try:
        # SELECT every column so a stale/missing deployment fails before polling.
        with engine.connect() as connection:
            connection.execute(select(runs).limit(0))
        asyncio.run(with_shutdown(PlanningStore(engine), settings, once=once))
    finally:
        engine.dispose()
