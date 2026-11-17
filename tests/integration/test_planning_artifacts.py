import base64
from copy import deepcopy
import gzip
from hashlib import sha256
import json

import pytest

from packages.domain_bridge.planning_artifacts import decode, read_json, InvalidPlanningArtifacts


def fixture_run():
    text = json.dumps({'version':'input-pin','amount':0,'taxes':[]})
    raw = json.dumps({'tax.json':text}).encode()
    return {'status':'succeeded','library_snapshot':{'pin':'one'},'runtime_snapshot':{'files':{'engine':'hash'}},
            'result':{'checks':{'status':'passed','scope':'li_checker_run_all'},
                      'version':{'inputs_sha256':'input-pin','database_version':{'library_version':{'pin':'one'}}},
                      'runtime':{'files':{'engine':'hash'}},
                      'artifacts':{'tax.json':{'bytes':len(text.encode()),'sha256':sha256(text.encode()).hexdigest()}},
                      'artifact_payload':{'encoding':'gzip+base64+json','uncompressed_bytes':len(raw),
                                          'sha256':sha256(raw).hexdigest(),
                                          'data':base64.b64encode(gzip.compress(raw)).decode()}}}


def test_round_trip_uses_saved_result():
    run = fixture_run()
    assert read_json(run,'tax.json')['amount'] == 0
    read_json(run,'tax.json')['amount'] = 999
    assert read_json(run,'tax.json')['amount'] == 0


@pytest.mark.parametrize('change', ['base64','truncated','size','oversize','hash','file_hash','files','version','runtime','library'])
def test_damaged_or_mixed_artifacts_fail_closed(change):
    run = fixture_run()
    result = run['result']
    payload = result['artifact_payload']
    if change == 'base64': payload['data'] = '!bad!'
    if change == 'truncated': payload['data'] = base64.b64encode(base64.b64decode(payload['data'])[:-4]).decode()
    if change == 'size': payload['uncompressed_bytes'] -= 1
    if change == 'oversize': payload['uncompressed_bytes'] = 100_000_001
    if change == 'hash': payload['sha256'] = 'wrong'
    if change == 'file_hash': result['artifacts']['tax.json']['sha256'] = 'wrong'
    if change == 'files': result['artifacts']['missing.json'] = deepcopy(result['artifacts']['tax.json'])
    if change == 'version': result['version']['inputs_sha256'] = 'other'
    if change == 'runtime': run['runtime_snapshot'] = {'files':{'engine':'other'}}
    if change == 'library': run['library_snapshot'] = {'pin':'other'}
    with pytest.raises(InvalidPlanningArtifacts): read_json(run,'tax.json')


@pytest.mark.parametrize('status',['queued','running','failed'])
def test_incomplete_run_has_no_result(status):
    run = fixture_run()
    run['status'] = status
    with pytest.raises(ValueError,match='planning_result_not_ready'): read_json(run,'tax.json')


def test_duplicate_archive_keys_are_rejected_even_with_valid_payload_hash():
    result = fixture_run()['result']
    raw = b'{"tax.json":"one","tax.json":"two"}'
    result['artifact_payload'].update(uncompressed_bytes=len(raw),sha256=sha256(raw).hexdigest(),
                                      data=base64.b64encode(gzip.compress(raw)).decode())
    with pytest.raises(InvalidPlanningArtifacts): decode(result)
