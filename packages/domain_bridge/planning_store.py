"""Durable planner jobs on the application's database, independent of web processes.

Only trusted backend workers may claim/finish jobs. User reads always require an
owner. Deployment must provision this table with RLS and no browser grants;
constructing this store does not create or alter a production schema.
"""
from datetime import timezone
from hashlib import sha256
import json
import re
from uuid import uuid4

from sqlalchemy import (JSON, CheckConstraint, Column, Float, Index, Integer, MetaData, String,
                        Table, UniqueConstraint, and_, func, literal, or_, select, update)

from packages.chat.store import CaseNotFound, RevisionConflict, conversations
from packages.domain_bridge.planning_runtime import capture_runtime

metadata = MetaData()
runs = Table(
    'planning_runs', metadata,
    Column('id', String(36), primary_key=True),
    Column('owner', String(64), nullable=False),
    Column('case_id', String(36), nullable=False),
    Column('case_revision', Integer, nullable=False),
    Column('request_id', String(64), nullable=False),
    Column('request_hash', String(64), nullable=False),
    Column('input', JSON, nullable=False),
    Column('library_snapshot', JSON, nullable=False),
    Column('runtime_snapshot', JSON, nullable=False),
    Column('case_snapshot', JSON, nullable=False),
    Column('status', String(16), nullable=False),
    Column('attempts', Integer, nullable=False),
    Column('lease_token', String(36)),
    Column('lease_until', Float),
    Column('created_at', Float, nullable=False),
    Column('updated_at', Float, nullable=False),
    Column('result', JSON),
    Column('error', String(80)),
    Column('events', JSON, nullable=False),
    UniqueConstraint('owner', 'request_id', name='planning_runs_owner_request'),
    CheckConstraint("status IN ('queued', 'running', 'succeeded', 'failed')", name='planning_runs_status'),
    CheckConstraint('attempts >= 0', name='planning_runs_attempts'),
    CheckConstraint("(status = 'running' AND lease_token IS NOT NULL AND lease_until IS NOT NULL) OR "
                    "(status <> 'running' AND lease_token IS NULL AND lease_until IS NULL)",
                    name='planning_runs_lease'),
)
Index('planning_runs_claim', runs.c.status, runs.c.lease_until, runs.c.created_at)
Index('planning_runs_owner_case', runs.c.owner, runs.c.case_id, runs.c.created_at)


class PlanningConflict(Exception):
    pass


class LeaseLost(Exception):
    pass


def _json(value):
    encoded = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
    if len(encoded.encode('utf-8')) > 5_000_000:
        raise ValueError('planning_payload_too_large')
    return encoded


def _clock(connection):
    # Database time avoids disagreement between worker clocks. SQLite returns a
    # naive UTC datetime; PostgreSQL returns a timezone-aware datetime.
    value = connection.execute(select(func.current_timestamp())).scalar_one()
    return value.replace(tzinfo=timezone.utc).timestamp() if value.tzinfo is None else value.timestamp()


def _public(row):
    return {key: value for key, value in dict(row).items() if key not in ('lease_token', 'lease_until', 'owner')}


class PlanningStore:
    def __init__(self, engine):
        self.engine = engine

    def enqueue(self, owner, case_id, revision, request_id, inputs, library_snapshot):
        if not isinstance(owner, str) or not 1 <= len(owner) <= 64:
            raise ValueError('invalid_owner')
        if not isinstance(request_id, str) or not 1 <= len(request_id) <= 64:
            raise ValueError('invalid_request_id')
        if type(revision) is not int or revision < 0:
            raise ValueError('invalid_case_revision')
        if not isinstance(inputs, dict) or not isinstance(library_snapshot, dict) or not library_snapshot:
            raise ValueError('planning_snapshot_required')
        runtime_snapshot = capture_runtime()
        payload = _json([case_id, revision, inputs, library_snapshot, runtime_snapshot])
        signature = sha256(payload.encode('utf-8')).hexdigest()
        with self.engine.begin() as c:
            stamp = _clock(c)
            # INSERT ... SELECT atomically binds ownership, revision and the
            # actual persisted case document; no caller-supplied case snapshot.
            values = dict(id=str(uuid4()), owner=owner, case_id=case_id, case_revision=revision,
                          request_id=request_id, request_hash=signature, input=inputs,
                          library_snapshot=library_snapshot, runtime_snapshot=runtime_snapshot,
                          status='queued', attempts=0,
                          created_at=stamp, updated_at=stamp, events=[{'status':'queued', 'at':stamp}])
            columns = list(values) + ['case_snapshot']
            source = select(*(literal(value, type_=runs.c[key].type) for key, value in values.items()),
                            conversations.c.document).where(
                                conversations.c.id == case_id, conversations.c.owner == owner,
                                conversations.c.revision == revision).with_for_update()
            if c.dialect.name == 'postgresql':
                from sqlalchemy.dialects.postgresql import insert
            elif c.dialect.name == 'sqlite':
                from sqlalchemy.dialects.sqlite import insert
            else:
                raise ValueError('unsupported_planning_database')
            c.execute(insert(runs).from_select(columns, source).on_conflict_do_nothing(
                index_elements=['owner', 'request_id']))
            row = c.execute(select(runs).where(runs.c.owner == owner,
                                               runs.c.request_id == request_id)).mappings().one_or_none()
            if row is None:
                exists = c.execute(select(conversations.c.id).where(
                    conversations.c.id == case_id, conversations.c.owner == owner)).first()
                if exists is None:
                    raise CaseNotFound()
                raise RevisionConflict()
            if row['request_hash'] != signature:
                raise PlanningConflict('request_payload_conflict')
            return _public(row)

    def get(self, owner, run_id):
        with self.engine.connect() as c:
            row = c.execute(select(runs).where(runs.c.id == run_id, runs.c.owner == owner)).mappings().one_or_none()
        if row is None:
            raise CaseNotFound()
        return _public(row)

    def find_request(self, owner, request_id):
        """Owner-scoped receipt lookup, including terminal and historical runs."""
        with self.engine.connect() as c:
            row = c.execute(select(runs).where(runs.c.owner == owner,
                                               runs.c.request_id == request_id)).mappings().one_or_none()
        return _public(row) if row is not None else None

    def list_case(self, owner, case_id, limit=25, before=None):
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('invalid_planning_page_size')
        scope = and_(runs.c.owner == owner, runs.c.case_id == case_id)
        fields = ('id', 'case_id', 'case_revision', 'request_id', 'status',
                  'attempts', 'created_at', 'updated_at', 'error')
        query = select(*(runs.c[name] for name in fields)).where(scope)
        with self.engine.connect() as c:
            if before is not None:
                cursor = c.execute(select(runs.c.id, runs.c.created_at).where(
                    scope, runs.c.id == before)).mappings().one_or_none()
                if cursor is None:
                    raise CaseNotFound()
                query = query.where(or_(runs.c.created_at < cursor['created_at'],
                    and_(runs.c.created_at == cursor['created_at'], runs.c.id < cursor['id'])))
            rows = c.execute(query.order_by(runs.c.created_at.desc(), runs.c.id.desc())
                             .limit(limit + 1)).mappings().all()
        items = [dict(row) for row in rows[:limit]]
        return {'items': items, 'next_before': items[-1]['id'] if len(rows) > limit else None}

    def claim(self, lease_seconds=60, max_attempts=3):
        if type(lease_seconds) is not int or type(max_attempts) is not int or not 5 <= lease_seconds <= 3600 or not 1 <= max_attempts <= 10:
            raise ValueError('invalid_lease_policy')
        with self.engine.begin() as c:
            stamp = _clock(c)
            available = or_(runs.c.status == 'queued', and_(runs.c.status == 'running', runs.c.lease_until <= stamp))
            row = c.execute(select(runs).where(available).order_by(runs.c.created_at, runs.c.id)
                            .limit(1).with_for_update(skip_locked=True)).mappings().one_or_none()
            if row is None:
                return None
            exhausted = row['attempts'] >= max_attempts
            status = 'failed' if exhausted else 'running'
            token = None if exhausted else str(uuid4())
            changes = dict(status=status, lease_token=token, lease_until=None if exhausted else stamp+lease_seconds,
                           attempts=row['attempts'] if exhausted else row['attempts']+1,
                           updated_at=stamp, error='worker_attempts_exhausted' if exhausted else None,
                           events=row['events']+[{'status':status, 'at':stamp, 'recovered':row['status']=='running'}])
            # CAS is retained for SQLite and protects against stale contenders.
            claimed = c.execute(update(runs).where(runs.c.id == row['id'], available,
                                                   runs.c.attempts == row['attempts']).values(**changes)
                                .returning(*runs.c)).mappings().one_or_none()
            return dict(claimed) if claimed is not None and not exhausted else None

    def heartbeat(self, run_id, token, lease_seconds=60):
        if type(lease_seconds) is not int or not 5 <= lease_seconds <= 3600:
            raise ValueError('invalid_lease_policy')
        with self.engine.begin() as c:
            stamp = _clock(c)
            result = c.execute(update(runs).where(self._lease(run_id, token, stamp))
                               .values(lease_until=stamp+lease_seconds, updated_at=stamp))
            if result.rowcount != 1:
                raise LeaseLost()

    @staticmethod
    def _lease(run_id, token, stamp):
        if not token:
            raise LeaseLost()
        return and_(runs.c.id == run_id, runs.c.lease_token == token,
                    runs.c.status == 'running', runs.c.lease_until > stamp)

    def finish(self, run_id, token, *, result=None, error=None):
        if (result is None) == (error is None):
            raise ValueError('provide_result_or_error')
        if error is not None and (not isinstance(error, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,79}', error)):
            raise ValueError('invalid_error_code')
        _json(result)
        with self.engine.begin() as c:
            stamp = _clock(c)
            condition = self._lease(run_id, token, stamp)
            row = c.execute(select(runs).where(condition).with_for_update()).mappings().one_or_none()
            if row is None:
                raise LeaseLost()
            status = 'failed' if error else 'succeeded'
            saved = c.execute(update(runs).where(condition).values(
                status=status, result=result, error=error, updated_at=stamp, lease_token=None, lease_until=None,
                events=row['events']+[{'status':status, 'at':stamp}]))
            if saved.rowcount != 1:
                raise LeaseLost()
