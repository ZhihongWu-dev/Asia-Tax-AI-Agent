"""Owner-scoped immutable credit workpapers, separate from final assessments."""
from copy import deepcopy
from hashlib import sha256
import json

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from packages.chat.store import CaseNotFound, RevisionConflict, now
from packages.chat.service import WorkflowError
from packages.income_tax.vietnam_credit_case import TreatyCreditLine, credit_workpaper
from packages.income_tax.vietnam_credit_dossier import TreatyCreditDossier, review_dossier


class VietnamCreditBasis(BaseModel):
    model_config = ConfigDict(extra='forbid')
    lines: list[TreatyCreditLine] = Field(min_length=1, max_length=200)
    dossier: TreatyCreditDossier


def _hash(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def save_workpaper(store, owner, case_id, revision, request_id, basis):
    doc = store.get(owner, case_id)
    basis = VietnamCreditBasis.model_validate(basis.model_dump() if isinstance(basis, VietnamCreditBasis) else basis)
    payload = basis.model_dump(mode='json')
    digest = _hash({'revision': revision, 'basis': payload})
    runs = doc.setdefault('income_credit_workpapers', [])
    for run in runs:
        if run['id'] == request_id:
            if run['request_hash'] != digest:
                raise WorkflowError('request_payload_conflict')
            return deepcopy(run)
    if doc['revision'] != revision:
        raise RevisionConflict()
    if len(runs) >= 100:
        raise ValueError('income_credit_workpaper_limit')
    result = credit_workpaper(doc.get('income_tax'), payload['lines'])
    dossier = review_dossier(payload['dossier'])
    snapshot = TypeAdapter(dict).dump_python({
        'inputs': deepcopy(doc['income_tax']), 'basis': payload,
        'result': result, 'dossier_review': dossier}, mode='json')
    run = {'id': request_id, 'case_id': case_id, 'input_revision': revision,
           'request_hash': digest, 'snapshot_hash': _hash(snapshot), 'created_at': now(),
           'status': 'credit_workpaper', **snapshot}
    runs.append(deepcopy(run))
    # Does not replace an assessment or change the case's calculation status.
    store.save(owner, doc, revision)
    return run


def get_workpaper(store, owner, case_id, run_id):
    doc = store.get(owner, case_id)
    for run in doc.get('income_credit_workpapers', []):
        if run['id'] == run_id:
            return deepcopy(run)
    raise CaseNotFound()
