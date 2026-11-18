"""Isolated atlas entry point over a trusted, version-pinned source bundle."""
from hashlib import sha256
import json
from pathlib import Path
import sys

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from packages.domain_bridge import tax_atlas
from packages.domain_bridge.planning_library import PlanningLibrary
from packages.domain_bridge.planning_runtime import capture_runtime

ROOT = Path(__file__).resolve().parents[2]


class AtlasRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    operation: Literal['map', 'country', 'glossary', 'clause']
    date: str = Field(default='', max_length=10, strict=True)
    code: str = Field(default='', max_length=2, strict=True)
    cite_id: str = Field(default='', max_length=240, strict=True)


def capture_atlas_runtime():
    return {'engine': capture_runtime(), 'atlas': {
        name: sha256((ROOT / 'packages/domain_bridge' / name).read_bytes()).hexdigest()
        for name in ('tax_atlas.py', 'atlas_runner.py', 'atlas_process.py')}}


def run(request, bundle, *, expected_version, expected_runtime):
    request = AtlasRequest.model_validate(request)
    when = tax_atlas.today(request.date)
    if request.operation == 'country' and request.code not in tax_atlas.ISO:
        raise ValueError('atlas_not_found')
    if (request.code and request.operation != 'country') or (request.cite_id and request.operation != 'clause'):
        raise ValueError('atlas_unexpected_selector')
    if request.operation == 'clause' and not request.cite_id:
        raise ValueError('atlas_missing_citation')
    runtime = capture_atlas_runtime()
    if runtime != expected_runtime:
        raise ValueError('atlas_runtime_changed')
    library = PlanningLibrary(bundle, expected_version=expected_version)
    if request.operation == 'clause':
        from types import SimpleNamespace
        state = {'lib': library, 'version': library.version_metadata(), 'rs': SimpleNamespace(rules=[])}
        result = tax_atlas.clause(state, request.cite_id)
    else:
        # Verify the entire rule dependency closure before importing the engine.
        for citation in runtime['engine']['citations']:
            library.source(citation)
        sys.path.insert(0, str(ROOT / 'rule/tools'))
        from query import Query
        import eval as evaluator
        query = Query(lib=library)
        state = {'lib': library, 'version': library.version_metadata(), 'q': query,
                 'rs': query.rs, 'ev': evaluator}
        if request.operation == 'map':
            result = tax_atlas.map_data(state, when)
        elif request.operation == 'country':
            result = tax_atlas.country(state, request.code, when)
        else:
            result = tax_atlas.glossary(state)
    if result is None:
        raise ValueError('atlas_not_found')
    if capture_atlas_runtime() != runtime:
        raise ValueError('atlas_runtime_changed')
    return {'request': request.model_dump(), 'runtime': runtime,
            'library_snapshot': expected_version, 'result': result}


def main():
    from packages.chat.worker_limits import apply_worker_limits
    apply_worker_limits(cpu_seconds=30, memory_mb=1024)
    request_path, response_path = map(Path, sys.argv[1:])
    payload = json.loads(request_path.read_text(encoding='utf-8'))
    result = run(payload['request'], payload['bundle'],
                 expected_version=payload['library_snapshot'], expected_runtime=payload['runtime'])
    raw = json.dumps(result, ensure_ascii=False, allow_nan=False).encode('utf-8')
    if len(raw) > 5_000_000:
        raise ValueError('atlas_response_limit')
    response_path.write_bytes(raw)


if __name__ == '__main__':
    main()
