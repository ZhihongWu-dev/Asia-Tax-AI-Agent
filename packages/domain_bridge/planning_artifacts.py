"""Read immutable planner artifacts without writing archive paths to disk."""
import base64
import binascii
import gzip
from hashlib import sha256
import io
import json
import zlib

MAX_EXPANDED_BYTES = 100_000_000
JSON_ARTIFACTS = frozenset({'tax.json', 'ranking.json', 'paths.json', 'open_items.json',
                          'branches.json', 'deltas.json', 'requirements.json'})


class InvalidPlanningArtifacts(ValueError):
    pass


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidPlanningArtifacts('duplicate_artifact_key')
        result[key] = value
    return result


def _constant(value):
    raise InvalidPlanningArtifacts('nonfinite_artifact_number')


def decode(result):
    try:
        payload = result['artifact_payload']
        size = payload['uncompressed_bytes']
        if (payload['encoding'] != 'gzip+base64+json' or type(size) is not int or
                not 0 <= size <= MAX_EXPANDED_BYTES or len(payload['data']) > 5_000_000):
            raise InvalidPlanningArtifacts('invalid_artifact_envelope')
        compressed = base64.b64decode(payload['data'], validate=True)
        with gzip.GzipFile(fileobj=io.BytesIO(compressed), mode='rb') as stream:
            raw = stream.read(size + 1)
        if len(raw) != size or sha256(raw).hexdigest() != payload['sha256']:
            raise InvalidPlanningArtifacts('artifact_payload_mismatch')
        contents = json.loads(raw, object_pairs_hook=_object, parse_constant=_constant)
        manifest = result['artifacts']
        if not isinstance(contents, dict) or set(contents) != set(manifest) or len(contents) > 10000:
            raise InvalidPlanningArtifacts('artifact_manifest_mismatch')
        total = 0
        for name, content in contents.items():
            if not isinstance(content, str):
                raise InvalidPlanningArtifacts('invalid_artifact_content')
            encoded = content.encode('utf-8')
            total += len(encoded)
            item = manifest[name]
            if (len(encoded) != item['bytes'] or sha256(encoded).hexdigest() != item['sha256'] or
                    total > 50_000_000):
                raise InvalidPlanningArtifacts('artifact_file_mismatch')
        return contents
    except (KeyError, TypeError, ValueError, OSError, EOFError, zlib.error, binascii.Error) as exc:
        raise InvalidPlanningArtifacts('invalid_planning_artifacts') from exc


def read_json(run, name):
    if name not in JSON_ARTIFACTS:
        raise InvalidPlanningArtifacts('unsupported_planning_artifact')
    if run['status'] != 'succeeded':
        raise ValueError('planning_result_not_ready')
    try:
        result = run['result']
        if (result['checks'] != {'status': 'passed', 'scope': 'li_checker_run_all'} or
                result['version']['database_version']['library_version'] != run['library_snapshot'] or
                result['runtime'] != run['runtime_snapshot']):
            raise InvalidPlanningArtifacts('planning_result_snapshot_mismatch')
        contents = decode(result)
        content = json.loads(contents[name], object_pairs_hook=_object, parse_constant=_constant)
        if not isinstance(content, dict) or content.get('version') != result['version']['inputs_sha256']:
            raise InvalidPlanningArtifacts('planning_artifact_version_mismatch')
        return content
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidPlanningArtifacts('invalid_planning_artifacts') from exc
