"""One durable planning attempt, outside the web request lifecycle.

The injected executor must be asynchronous and stop/reap any subprocess in its
cancellation cleanup. Snapshot verification is required both before and after
execution: the verifier returns a freshly read snapshot, which this worker
compares with the queued version. Neither callback may publish a result.
"""
import asyncio
from copy import deepcopy
import math

from packages.domain_bridge.planning_store import LeaseLost


class PlanningExecutionError(Exception):
    """A known, non-sensitive failure suitable for a persisted run status."""
    CODES = frozenset({'library_version_changed', 'planning_execution_failed',
                       'planning_output_invalid', 'planning_resource_limit',
                       'planning_sources_unavailable', 'planning_runtime_changed'})

    def __init__(self, code):
        if code not in self.CODES:
            raise ValueError('unsupported_planning_error')
        self.code = code
        super().__init__(code)


async def verify_cloud_snapshot(job):
    """Use the same live base/review/overlay boundary as authenticated research."""
    from packages.chat.library_cloud import current_library_snapshot, LibraryVersionChanged
    try:
        return await asyncio.to_thread(current_library_snapshot, expected_version=job['library_snapshot'])
    except LibraryVersionChanged:
        raise PlanningExecutionError('library_version_changed') from None


async def run_once(store, execute, verify_snapshot=verify_cloud_snapshot, *, lease_seconds=60,
                   wall_seconds=1800, max_attempts=3):
    """Claim at most one job; return its ID, or None when no job was claimed.

    Cancellation and renewal failures leave a recoverable running record.
    A bounded computation failure is persisted as a terminal failure. Database
    errors propagate to the supervisor, rather than pretending work succeeded.
    """
    if not isinstance(wall_seconds, (int, float)) or isinstance(wall_seconds, bool) or \
            not math.isfinite(wall_seconds) or not 0 < wall_seconds <= 86400:
        raise ValueError('invalid_planning_deadline')
    job = await asyncio.to_thread(store.claim, lease_seconds, max_attempts)
    if job is None:
        return None
    run_id, token = job['id'], job['lease_token']
    expected_snapshot = deepcopy(job['library_snapshot'])

    async def verify():
        if await verify_snapshot(job) != expected_snapshot:
            raise PlanningExecutionError('library_version_changed')

    async def pipeline():
        await verify()
        result = await execute(job)
        await verify()
        if not isinstance(result, dict):
            raise PlanningExecutionError('planning_output_invalid')
        return result

    async def renew():
        while True:
            await asyncio.sleep(lease_seconds / 3)
            await asyncio.to_thread(store.heartbeat, run_id, token, lease_seconds)

    work = asyncio.create_task(asyncio.wait_for(pipeline(), wall_seconds))
    heartbeat = asyncio.create_task(renew())
    result, error = None, None
    try:
        done, _ = await asyncio.wait((work, heartbeat), return_when=asyncio.FIRST_COMPLETED)
        if heartbeat in done:
            # Do not publish even if computation finished in the same loop turn.
            # A failed renewal means this worker cannot establish current ownership.
            await heartbeat
            raise LeaseLost()
        try:
            result = await work
        except asyncio.TimeoutError:
            error = 'planning_timeout'
        except PlanningExecutionError as exc:
            error = exc.code
        except LeaseLost:
            raise
        except Exception:
            error = 'planning_execution_failed'
    finally:
        # Await executor cleanup before releasing this attempt to the supervisor.
        # CancelledError propagates, so shutdown does not falsely complete a job.
        for task in (work, heartbeat):
            if not task.done():
                task.cancel()
        await asyncio.gather(work, heartbeat, return_exceptions=True)
    await asyncio.to_thread(store.finish, run_id, token, result=result, error=error)
    return run_id
