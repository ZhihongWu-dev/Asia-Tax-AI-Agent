"""Bounded atlas subprocess using the existing cancellation/reaping mechanism."""
import asyncio
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from packages.domain_bridge.atlas_runner import AtlasRequest, capture_atlas_runtime
from packages.domain_bridge.planning_process import _child


async def execute(request, bundle, *, expected_version, timeout_seconds=40):
    request = AtlasRequest.model_validate(request).model_dump()
    runtime = capture_atlas_runtime()
    with TemporaryDirectory(prefix='tax-atlas-') as directory:
        root = Path(directory)
        input_path, output_path = root / 'request.json', root / 'response.json'
        input_path.write_text(json.dumps({'request': request, 'bundle': bundle,
            'library_snapshot': expected_version, 'runtime': runtime}, ensure_ascii=False,
            allow_nan=False), encoding='utf-8')
        try:
            code = await asyncio.wait_for(_child([sys.executable, '-m',
                'packages.domain_bridge.atlas_runner', str(input_path), str(output_path)]), timeout_seconds)
            if code != 0 or not output_path.is_file() or output_path.stat().st_size > 5_000_000:
                raise ValueError('atlas_execution_failed')
            result = json.loads(output_path.read_text(encoding='utf-8'))
            if (result['runtime'] != runtime or result['library_snapshot'] != expected_version
                    or result['request'] != request or capture_atlas_runtime() != runtime):
                raise ValueError('atlas_snapshot_changed')
            return result
        except (TimeoutError, OSError, KeyError, json.JSONDecodeError, RecursionError):
            raise ValueError('atlas_execution_failed') from None
