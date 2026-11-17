"""Cancellable isolated execution of a trusted, pinned planning bundle."""
import asyncio
import base64
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from packages.chat.worker_limits import terminate_worker
from packages.domain_bridge.planning_worker import PlanningExecutionError


ROOT = Path(__file__).resolve().parents[2]


async def _child(command):
    options = ({'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt'
               else {'start_new_session': True})
    spawning = asyncio.create_task(asyncio.create_subprocess_exec(
        *command, cwd=ROOT, stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL, **options))
    proc = None
    try:
        proc = await asyncio.shield(spawning)
        return await proc.wait()
    finally:
        # Shield creation so cancellation cannot strand a newly-created child.
        async def cleanup():
            child = proc if proc is not None else await spawning
            await terminate_worker(child, process_group=True)
        task = asyncio.create_task(cleanup())
        cancelled = False
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                # Finish reaping even if shutdown issues a second cancellation.
                cancelled = True
        task.result()
        if cancelled:
            raise asyncio.CancelledError


def _collect(response, output, expected_version):
    if response.stat().st_size > 5_000_000:
        raise PlanningExecutionError('planning_resource_limit')
    result = json.loads(response.read_text(encoding='utf-8'))
    if (result.get('checks') != {'status': 'passed', 'scope': 'li_checker_run_all'} or
            result['version']['database_version']['library_version'] != expected_version):
        raise PlanningExecutionError('planning_output_invalid')
    contents = {}
    total = 0
    for name, metadata in result['artifacts'].items():
        path = output / name
        if path.is_symlink() or not path.resolve().is_relative_to(output.resolve()):
            raise PlanningExecutionError('planning_output_invalid')
        total += path.stat().st_size
        if total > 50_000_000:
            raise PlanningExecutionError('planning_resource_limit')
        raw = path.read_bytes()
        if len(raw) != metadata['bytes'] or sha256(raw).hexdigest() != metadata['sha256']:
            raise PlanningExecutionError('planning_output_invalid')
        contents[name] = raw.decode('utf-8')
    payload = json.dumps(contents, ensure_ascii=False, allow_nan=False,
                         separators=(',', ':')).encode('utf-8')
    result['artifact_payload'] = {'encoding': 'gzip+base64+json',
                                  'uncompressed_bytes': len(payload),
                                  'sha256': sha256(payload).hexdigest(),
                                  'data': base64.b64encode(gzip.compress(payload, mtime=0)).decode('ascii')}
    if len(json.dumps(result, ensure_ascii=False, allow_nan=False).encode('utf-8')) > 5_000_000:
        raise PlanningExecutionError('planning_resource_limit')
    return result


async def execute_bundle(inputs, bundle, *, expected_version):
    """Return verified artifact contents for durable storage by planning_worker.

    The caller supplies an admitted bundle from read_planning_bundle; this
    function neither approves sources nor publishes a completed run.
    """
    with TemporaryDirectory(prefix='tax-planning-') as directory:
        root = Path(directory)
        request, output, response = root/'request.json', root/'products', root/'response.json'
        request.write_text(json.dumps({'input': inputs, 'bundle': bundle,
                           'library_snapshot': expected_version}, ensure_ascii=False,
                           allow_nan=False), encoding='utf-8')
        code = await _child([sys.executable, '-X', 'utf8', '-m',
                             'packages.domain_bridge.planning_runner',
                             str(request), str(output), str(response)])
        if code != 0:
            raise PlanningExecutionError('planning_execution_failed')
        try:
            return _collect(response, output, expected_version)
        except PlanningExecutionError:
            raise
        except (OSError, ValueError, KeyError, TypeError):
            raise PlanningExecutionError('planning_output_invalid') from None
