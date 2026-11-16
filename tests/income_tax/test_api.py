from types import SimpleNamespace
from uuid import uuid4
from fastapi import FastAPI
from fastapi.testclient import TestClient
from apps.api import auth, chat
from packages.chat.store import ChatStore
from tests.chat.auth_support import fixture_user

HEADERS = {"x-asiatax-request": "1"}


def test_income_api_uses_existing_auth_and_owner_boundary(tmp_path):
    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(chat.router)
    store = ChatStore("sqlite:///" + str(tmp_path / "cases.sqlite"))
    app.dependency_overrides[auth.optional_user] = fixture_user
    app.dependency_overrides[chat.get_service] = lambda: SimpleNamespace(store=store)
    with TestClient(app) as alice, TestClient(app) as bob, TestClient(app) as anonymous:
        assert anonymous.get(f"/api/cases/{uuid4()}/income-tax").status_code == 401
        alice.get("/api/auth/session");bob.get("/api/auth/session")
        created = alice.post("/api/cases", headers=HEADERS)
        assert created.status_code == 201
        case_id = created.json()["id"]
        url = f"/api/cases/{case_id}/income-tax"
        payload = dict(revision=0, request_id=str(uuid4()), inputs=dict(subject="individual", jurisdiction="sg", period_start="2026-01-01", period_end="2026-12-31", currency="SGD", residency="resident", incomes=[dict(category="employment", source_jurisdiction="sg", gross_amount="80000", description="Salary")]))
        assert alice.put(url, json=payload).status_code == 403
        saved = alice.put(url, json=payload, headers=HEADERS)
        assert saved.status_code == 200, saved.text
        assert saved.json()["income_tax_status"] == "needs_information"
        assert "claimed_deductions" in saved.json()["missing_fields"]
        assert bob.get(url).status_code == 404
        assert bob.put(url, json=payload, headers=HEADERS).status_code == 404
        assert alice.get(url).json()["income_tax"]["subject"] == "individual"
        full_case = alice.get(f"/api/cases/{case_id}").json()
        assert full_case["income_tax"]["subject"] == "individual"
        assert full_case["income_tax_status"] == "needs_information"
        assert "income_tax_receipts" not in full_case
        assert "income_tax_history" not in full_case
        # Rejected inputs must not mutate the saved case or consume its revision.
        import copy
        for value in [0.1, True, "0.0000001", "1000000000000000001"]:
            invalid=copy.deepcopy(payload)
            invalid.update(revision=1, request_id=str(uuid4()))
            invalid["inputs"]["incomes"][0]["gross_amount"]=value
            assert alice.put(url, json=invalid, headers=HEADERS).status_code == 422
            assert alice.get(url).json()["revision"] == 1
        payload["request_id"] = str(uuid4())
        assert alice.put(url, json=payload, headers=HEADERS).status_code == 409
    store.engine.dispose()
