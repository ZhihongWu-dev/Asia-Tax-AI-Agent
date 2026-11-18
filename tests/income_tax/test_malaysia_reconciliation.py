from decimal import Decimal
import pytest
from packages.contracts.income_tax import IncomeTaxCase
from packages.income_tax.malaysia_reconciliation import IndividualWorkpaper, reconcile


def fixture():
    case = IncomeTaxCase(subject="individual", jurisdiction="my", currency="MYR",
        residency="resident", period_start="2026-01-01", period_end="2026-12-31",
        facts_confirmed=True, claimed_deductions="9000", carried_losses="50000",
        incomes=[dict(category=category, source_jurisdiction="my", gross_amount=gross,
                      description="Synthetic ordinary source")
                 for category, gross in [("business", "20000"), ("employment", "100000")]])
    data = dict(sources=[dict(income_index=i, additions="0", deductions="0",
        statutory_charges="0", statutory_allowances="0",
        explanation="Source documents and adjustment eligibility verified") for i in range(2)],
        eligible_prior_business_losses="50000", schedule4_additions="0",
        allowed_total_income_deductions=[], allowed_personal_reliefs="9000",
        eligibility_verified=True, separate_assessment_verified=True)
    return case, data


def test_prior_business_losses_cannot_reduce_salary():
    case, data = fixture()
    result = reconcile(case, IndividualWorkpaper(**data))
    assert result["prior_losses_used"] == 20000
    assert result["prior_losses_unused"] == 30000
    assert result["chargeable_income"] == 91000


def test_current_loss_and_deduction_stages_are_separate():
    case, data = fixture()
    data["sources"][0]["deductions"] = "25000"
    data["allowed_total_income_deductions"] = ["1000", "2000"]
    case.claimed_deductions = Decimal('37000')
    result = reconcile(case, IndividualWorkpaper(**data))
    assert result["prior_losses_used"] == 0
    assert result["prior_losses_unused"] == 50000
    assert result["aggregate_income"] == 100000
    assert result["current_losses_used"] == 5000
    assert result["total_income"] == 92000
    assert result["chargeable_income"] == 83000


def test_positive_addition_is_preserved_instead_of_gross_ceiling():
    case, data = fixture()
    data["sources"][0]["statutory_charges"] = "60000"
    result = reconcile(case, IndividualWorkpaper(**data))
    assert result["business_statutory_income"] == 80000
    assert result["chargeable_income"] == 121000


@pytest.mark.parametrize("change", ["duplicate", "missing", "unverified", "excess_deduction", "wage_loss"])
def test_unreconciled_or_invalid_workpaper_rejected(change):
    case, data = fixture()
    if change == "duplicate": data["sources"][1]["income_index"] = 0
    if change == "missing": data["sources"].pop()
    if change == "unverified": data["eligibility_verified"] = False
    if change == "excess_deduction": data["allowed_total_income_deductions"] = ["100001"]
    if change == "wage_loss": data["sources"][1]["deductions"] = "100001"
    case.claimed_deductions = (sum((Decimal(s['deductions']) + Decimal(s['statutory_allowances'])
                                   for s in data['sources']), Decimal(0))
                              + sum(map(Decimal, data['allowed_total_income_deductions']), Decimal(0))
                              + Decimal(data['allowed_personal_reliefs']))
    with pytest.raises(ValueError): reconcile(case, IndividualWorkpaper(**data))


def test_saved_deduction_summary_must_match_detailed_claims():
    case, data = fixture()
    case.claimed_deductions = Decimal('0')
    with pytest.raises(ValueError, match='claimed deductions'):
        reconcile(case, IndividualWorkpaper(**data))


def test_assessment_requires_workpaper_and_rejects_mismatched_basis():
    from pydantic import TypeAdapter
    from packages.contracts.income_assessment import Assessment
    from packages.income_tax.assessment import calculate
    case, data = fixture()
    payload = dict(policy="my_individual_2026", chargeable_income="91000",
        ordinary_treatment_confirmed=True, allowed_rebates="0", allowed_tax_credits="0",
        prepaid_tax="0", basis_confirmed=True,
        basis_explanation="Verified adjustments and personal relief schedule")
    adapter = TypeAdapter(Assessment)
    with pytest.raises(ValueError, match="workpaper"):
        calculate(case, adapter.validate_python(payload))
    payload["workpaper"] = data
    result = calculate(case, adapter.validate_python(payload))
    assert result["reconciliation"]["chargeable_income"] == "91000"
    payload["chargeable_income"] = "100000"
    with pytest.raises(ValueError, match="differs"):
        calculate(case, adapter.validate_python(payload))


def test_api_rejection_is_atomic_and_workpaper_survives_reopen(tmp_path):
    from copy import deepcopy
    from types import SimpleNamespace
    from uuid import uuid4
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from apps.api import auth, chat
    from packages.chat.store import ChatStore
    from tests.chat.auth_support import fixture_user
    case, paper = fixture()
    url = 'sqlite:///' + str(tmp_path / 'malaysia.sqlite')
    service = SimpleNamespace(store=ChatStore(url))
    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(chat.router)
    app.dependency_overrides[auth.optional_user] = fixture_user
    app.dependency_overrides[chat.get_service] = lambda: service
    headers = {'x-asiatax-request': '1'}
    basis = dict(policy='my_individual_2026', chargeable_income='100000',
        ordinary_treatment_confirmed=True, allowed_rebates='0', allowed_tax_credits='0',
        prepaid_tax='0', basis_confirmed=True, workpaper=paper,
        basis_explanation='Verified source adjustments and personal relief schedule')
    try:
        with TestClient(app) as client:
            client.get('/api/auth/session')
            case_id = client.post('/api/cases', headers=headers).json()['id']
            path = f'/api/cases/{case_id}/income-tax'
            saved = client.put(path, headers=headers, json=dict(revision=0,
                request_id=str(uuid4()), inputs=case.model_dump(mode='json')))
            assert saved.status_code == 200, saved.text
            before = client.get(path).json()
            request = dict(revision=before['revision'], request_id=str(uuid4()), basis=basis)
            failed = client.post(path+'/runs', headers=headers, json=request)
            assert failed.status_code == 422, failed.text
            assert client.get(path).json() == before
            basis['chargeable_income'] = '91000'
            response = client.post(path+'/runs', headers=headers, json=request)
            assert response.status_code == 200, response.text
            run = response.json()
            assert run['basis']['workpaper']['sources'][1]['income_index'] == 1
            assert run['result']['reconciliation']['prior_losses_unused'] == '30000'
            service.store.engine.dispose()
            service.store = ChatStore(url)
            assert client.get(path+'/runs/'+run['id']).json() == run
            assert client.post(path+'/runs', headers=headers, json=request).json() == run
            # A rejected next attempt must not replace the accepted result.
            current = client.get(path).json()
            invalid = deepcopy(request)
            invalid.update(revision=current['revision'], request_id=str(uuid4()))
            invalid['basis']['workpaper']['sources'][1]['income_index'] = 0
            assert client.post(path+'/runs', headers=headers, json=invalid).status_code == 422
            assert client.get(path).json() == current
    finally:
        service.store.engine.dispose()
