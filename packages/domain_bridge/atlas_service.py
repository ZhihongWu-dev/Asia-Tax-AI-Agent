"""Read one reviewed catalog snapshot and reject changes during atlas execution."""
from functools import partial

from starlette.concurrency import run_in_threadpool

from packages.chat.library_cloud import current_library_snapshot
from packages.domain_bridge.planning_sources import read_planning_bundle
from packages.domain_bridge.atlas_runner import AtlasRequest, capture_atlas_runtime
from packages.domain_bridge.atlas_process import execute


async def query(request):
    request = AtlasRequest.model_validate(request).model_dump()
    version = await run_in_threadpool(current_library_snapshot)
    runtime = capture_atlas_runtime()
    citations = ([request['cite_id']] if request['operation'] == 'clause'
                 else runtime['engine']['citations'])
    bundle = await run_in_threadpool(partial(read_planning_bundle, citations,
                                            expected_version=version))
    result = await execute(request, bundle, expected_version=version)
    await run_in_threadpool(partial(current_library_snapshot, expected_version=version))
    if result['runtime'] != runtime:
        raise ValueError('atlas_runtime_changed')
    return result['result']
