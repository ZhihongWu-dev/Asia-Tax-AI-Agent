"""Save Li inputs in the existing case; enqueue only that saved revision."""
from copy import deepcopy
from hashlib import sha256
import json

from packages.chat.store import RevisionConflict
from packages.contracts.planning import PlanningInput
from packages.domain_bridge.planning_store import PlanningConflict


def view(doc):
    return {'id': doc['id'], 'revision': doc['revision'],
            'planning_input': deepcopy(doc.get('planning_input'))}


def save_case(store, owner, case_id, revision, request_id, inputs: PlanningInput):
    doc = store.get(owner, case_id)
    payload = inputs.engine_input()
    signature = sha256(json.dumps([revision, payload], sort_keys=True,
                                 separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    receipts = doc.setdefault('planning_receipts', {})
    if request_id in receipts:
        if receipts[request_id] != signature:
            raise PlanningConflict('request_payload_conflict')
        return view(doc)
    if doc['revision'] != revision:
        raise RevisionConflict()
    if len(receipts) >= 1000:
        raise ValueError('case_limit')
    history = doc.setdefault('planning_history', [])
    if doc.get('planning_input') is not None:
        history.append({'revision': revision, 'input': deepcopy(doc['planning_input'])})
    if len(history) > 100:
        raise ValueError('planning_history_limit')
    doc['planning_input'] = payload
    receipts[request_id] = signature
    return view(store.save(owner, doc, revision))


def enqueue_saved(store, jobs, owner, case_id, revision, request_id, library_snapshot):
    doc = store.get(owner, case_id)
    receipt = jobs.find_request(owner, request_id)
    if receipt is not None:
        if (receipt['case_id'] != case_id or receipt['case_revision'] != revision or
                receipt['library_snapshot'] != library_snapshot):
            raise PlanningConflict('request_payload_conflict')
        return receipt
    if doc['revision'] != revision:
        raise RevisionConflict()
    inputs = PlanningInput.model_validate(doc.get('planning_input'))
    # enqueue's INSERT SELECT rechecks owner/revision atomically; a concurrent
    # edit after this read cannot bind these inputs to the newer case snapshot.
    return jobs.enqueue(owner, case_id, revision, request_id, inputs.engine_input(), library_snapshot)


def enqueue_current(store, jobs, owner, case_id, revision, request_id):
    from packages.chat.library_cloud import current_library_snapshot
    doc = store.get(owner, case_id)
    receipt = jobs.find_request(owner, request_id)
    if receipt is not None:
        if receipt['case_id'] != case_id or receipt['case_revision'] != revision:
            raise PlanningConflict('request_payload_conflict')
        return receipt
    if doc['revision'] != revision:
        raise RevisionConflict()
    PlanningInput.model_validate(doc.get('planning_input'))
    return enqueue_saved(store, jobs, owner, case_id, revision, request_id, current_library_snapshot())


def get_run(store, jobs, owner, case_id, run_id):
    from packages.chat.store import CaseNotFound
    store.get(owner, case_id)
    run = jobs.get(owner, run_id)
    if run['case_id'] != case_id:
        raise CaseNotFound()
    return run


def list_runs(store, jobs, owner, case_id, limit=25, before=None):
    store.get(owner, case_id)
    return jobs.list_case(owner, case_id, limit, before)


def get_artifact(store, jobs, owner, case_id, run_id, name):
    from packages.domain_bridge.planning_artifacts import read_json
    run = get_run(store, jobs, owner, case_id, run_id)
    return {'run_id': run['id'], 'case_revision': run['case_revision'],
            'artifact': name, 'content': read_json(run, name)}
