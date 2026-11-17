import asyncio
import base64
import gzip
from hashlib import sha256
import json
import sys

import pytest

from packages.domain_bridge import planning_process as process
from packages.domain_bridge.planning_worker import PlanningExecutionError


def test_real_child_is_reaped_on_cancellation(monkeypatch):
    original = asyncio.create_subprocess_exec
    children = []
    async def spawn(*args, **kwargs):
        child = await original(*args, **kwargs)
        children.append(child)
        return child
    monkeypatch.setattr(asyncio, 'create_subprocess_exec', spawn)
    async def scenario():
        task = asyncio.create_task(process._child([sys.executable, '-c', 'import time; time.sleep(60)']))
        while not children:
            await asyncio.sleep(.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert children[0].returncode is not None
    asyncio.run(scenario())


def test_real_child_exit_code():
    assert asyncio.run(process._child([sys.executable, '-c', 'raise SystemExit(7)'])) == 7


@pytest.mark.parametrize('change', ['none', 'content', 'version', 'escape'])
def test_collection_verifies_persisted_contents(tmp_path, change):
    output = tmp_path / 'products'
    output.mkdir()
    raw = b'{"tax":20}'
    (output / 'tax.json').write_bytes(raw)
    pin = {'version': 'one'}
    manifest = {'version': {'database_version': {'library_version': pin}},
                'checks': {'status': 'passed', 'scope': 'li_checker_run_all'},
                'artifacts': {'tax.json': {'bytes': len(raw), 'sha256': sha256(raw).hexdigest()}}}
    if change == 'content':
        (output / 'tax.json').write_bytes(b'changed')
    if change == 'version':
        manifest['version']['database_version']['library_version'] = {'version': 'other'}
    if change == 'escape':
        manifest['artifacts']['../tax.json'] = manifest['artifacts'].pop('tax.json')
    response = tmp_path / 'response.json'
    response.write_text(json.dumps(manifest), encoding='utf-8')
    if change == 'none':
        payload = process._collect(response, output, pin)['artifact_payload']
        decoded = gzip.decompress(base64.b64decode(payload['data']))
        assert len(decoded) == payload['uncompressed_bytes']
        assert sha256(decoded).hexdigest() == payload['sha256']
        assert json.loads(decoded)['tax.json'] == raw.decode()
    else:
        with pytest.raises(PlanningExecutionError):
            process._collect(response, output, pin)
