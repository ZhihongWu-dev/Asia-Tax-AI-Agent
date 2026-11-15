"""Income-tax facts persisted in the existing owner-scoped case document."""
from copy import deepcopy
from hashlib import sha256
import json
from packages.contracts.income_tax import IncomeTaxCase
from packages.chat.store import RevisionConflict


def view(doc):
    return {"id": doc["id"], "revision": doc["revision"], "income_tax": doc.get("income_tax"),
            "income_tax_status": doc.get("income_tax_status", "not_started"),
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
