"""Income-tax facts persisted in the existing owner-scoped case document."""
from copy import deepcopy
from hashlib import sha256
import json
from packages.contracts.income_tax import IncomeTaxCase
from packages.chat.store import RevisionConflict


def view(doc):
    return {"id": doc["id"], "revision": doc["revision"], "income_tax": doc.get("income_tax"),
            "income_tax_status": doc.get("income_tax_status", "not_started"),
            "income_tax_result": doc.get("income_tax_result"),
            "missing_fields": doc.get("income_tax_missing", [])}


def save_case(store, owner, case_id, revision, request_id, inputs: IncomeTaxCase):
    doc = store.get(owner, case_id)
    payload = inputs.model_dump(mode="json")
    digest = sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    receipts = doc.setdefault("income_tax_receipts", {})
    if request_id in receipts:
        if receipts[request_id] != digest:
            raise ValueError("request_payload_conflict")
        return view(doc)
    if doc["revision"] != revision:
        raise RevisionConflict()
    if len(receipts) >= 1000:
        raise ValueError("case_limit")
    history = doc.setdefault("income_tax_history", [])
    if doc.get("income_tax") is not None:
        history.append({"revision": doc["revision"], "inputs": deepcopy(doc["income_tax"])})
    if len(history) > 100:
        raise ValueError("income_tax_history_limit")
    doc["income_tax"] = payload
    missing = inputs.missing_for_calculation()
    doc["income_tax_status"] = "needs_information" if missing else "awaiting_rule_validation"
    doc["income_tax_missing"] = missing
    # An amended input must never retain an apparently valid old calculation.
    doc.pop("income_tax_result", None)
    receipts[request_id] = digest
    return view(store.save(owner, doc, revision))


def assessment_run(store, owner, case_id, revision, request_id, basis):
    """Atomically save an immutable calculation snapshot in the existing case store.

No background worker is needed for deterministic arithmetic. A disconnect before
commit leaves no run; after commit the same request returns the saved run, even
after an intervening edit. Claims are explicitly scoped to the supplied basis.
"""
    from packages.chat.store import now
    from packages.chat.service import WorkflowError
    from packages.income_tax.assessment import calculate
    doc = store.get(owner, case_id)
    request = {'revision': revision, 'basis': basis.model_dump(mode='json')}
    digest = sha256(json.dumps(request, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    runs = doc.setdefault('income_tax_runs', [])
    for run in runs:
        if run['request_id'] == request_id:
            if run['request_hash'] != digest:
                raise WorkflowError('request_payload_conflict')
            return deepcopy(run)
    if doc['revision'] != revision:
        raise RevisionConflict()
    if len(runs) >= 100:
        raise ValueError('income_tax_run_limit')
    inputs = IncomeTaxCase.model_validate(doc.get('income_tax'))
    result = calculate(inputs, basis)
    snapshot = {'inputs': inputs.model_dump(mode='json'), 'basis': request['basis'], 'result': result}
    snapshot_hash = sha256(json.dumps(snapshot, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    run = {'id': request_id, 'request_id': request_id, 'request_hash': digest,
           'case_id': case_id, 'input_revision': revision, 'created_at': now(),
           'status': 'calculated_basis', 'snapshot_hash': snapshot_hash,
           'scope': 'Calculation of the confirmed basis; not a completed return or legal approval.',
           **snapshot}
    runs.append(deepcopy(run))
    doc['income_tax_result'] = deepcopy(run)
    doc['income_tax_status'] = 'calculated_basis'
    store.save(owner, doc, revision)
    return run


def get_assessment_run(store, owner, case_id, run_id):
    from packages.chat.store import CaseNotFound
    doc = store.get(owner, case_id)
    for run in doc.get('income_tax_runs', []):
        if run['id'] == run_id:
            return deepcopy(run)
    raise CaseNotFound()
