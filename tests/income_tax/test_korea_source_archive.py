"""The deliverable must include the exact originals cited by Korean adapters."""
import ast
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_korean_manifest_and_inline_source_hashes_resolve_to_delivered_originals():
    archive = json.loads((ROOT/'packages/income_tax/kr_source_archive.json').read_text(encoding='utf-8'))
    by_id = {s['doc_id']: s for s in archive['sources']}
    assert len(by_id) == len(archive['sources'])
    hashes = set()
    for source in by_id.values():
        path = (ROOT/source['file']).resolve()
        assert path.is_relative_to((ROOT/'database/raw/kr').resolve())
        with path.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        assert actual == source['sha256'], source['doc_id']
        hashes.add(actual)
    manifest = json.loads((ROOT/'packages/income_tax/kr_2026_sources.json').read_text(encoding='utf-8'))
    for group in manifest.values():
        for source in group:
            assert by_id[source['doc_id']]['sha256'] == source['sha256']
            assert by_id[source['doc_id']]['url'] == source['url']
    for file in (ROOT/'packages/income_tax').glob('korea*.py'):
        for node in ast.walk(ast.parse(file.read_text(encoding='utf-8'))):
            values = []
            if isinstance(node, ast.Dict):
                values = [v for k,v in zip(node.keys,node.values)
                          if isinstance(k,ast.Constant) and k.value=='sha256']
            elif isinstance(node,ast.Call):
                values = [k.value for k in node.keywords if k.arg=='sha256']
            for value in values:
                if isinstance(value,ast.Constant) and isinstance(value.value,str):
                    assert value.value in hashes, (str(file),node.lineno,value.value)
