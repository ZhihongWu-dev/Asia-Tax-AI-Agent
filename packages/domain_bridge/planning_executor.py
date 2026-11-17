"""Cloud source admission followed by isolated Li execution for planning_worker."""
import asyncio
from copy import deepcopy

from packages.chat.library_cloud import LibraryVersionChanged
from packages.domain_bridge.planning_sources import read_planning_bundle, PlanningSourcesUnavailable
from packages.domain_bridge.planning_runtime import capture_runtime
from packages.domain_bridge.planning_process import execute_bundle
from packages.domain_bridge.planning_worker import PlanningExecutionError


async def execute_job(job):
    """No publication: the worker rechecks the live snapshot and lease afterward."""
    pin = deepcopy(job['library_snapshot'])
    inputs = deepcopy(job['input'])
    runtime = capture_runtime()
    try:
        bundle = await asyncio.to_thread(read_planning_bundle, runtime['citations'], expected_version=pin)
    except LibraryVersionChanged:
        raise PlanningExecutionError('library_version_changed') from None
    except PlanningSourcesUnavailable:
        raise PlanningExecutionError('planning_sources_unavailable') from None
    if capture_runtime() != runtime:
        raise PlanningExecutionError('planning_runtime_changed')
    return await execute_bundle(inputs, bundle, expected_version=pin, expected_runtime=runtime)
