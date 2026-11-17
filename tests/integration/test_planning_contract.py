import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from packages.contracts.planning import PlanningInput


ROOT = Path(__file__).resolve().parents[2]


def case():
    return json.loads((ROOT/'optimization/examples/case_jp_sg_individual.json').read_text(encoding='utf-8'))


def test_real_case_preserves_all_existing_inputs():
    inputs = case()
    assert PlanningInput.model_validate(inputs).engine_input() == inputs


@pytest.mark.parametrize('key', ['date', 'mode', 'amount', 'currency', 'payer', 'payee'])
def test_business_request_never_defaults_required_inputs(key):
    inputs = case()
    inputs.pop(key)
    with pytest.raises(ValidationError):
        PlanningInput.model_validate(inputs)


@pytest.mark.parametrize('key,value', [('amount', True), ('amount', '100'), ('amount', -1),
    ('amount', float('inf')), ('amount', float('nan')), ('fx', 'local.json'),
    ('date', '20260201'), ('date', '2026-02-30'), ('mode', 'unknown'),
    ('limits', {'max_hops': True}), ('limits', {'max_hop': 3}), ('currency', 'jpy')])
def test_invalid_inputs_are_rejected(key, value):
    inputs = case()
    inputs[key] = value
    with pytest.raises(ValidationError):
        PlanningInput.model_validate(inputs)


def test_zero_and_both_payee_subjects_supported():
    for subject in ('company', 'individual'):
        inputs = case()
        inputs['amount'] = 0
        inputs['payee']['subject'] = subject
        assert PlanningInput.model_validate(inputs).engine_input()['amount'] == 0
