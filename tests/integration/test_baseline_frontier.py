import ast
import copy
import importlib.util
from pathlib import Path
import random

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('baseline_frontier', ROOT / 'optimization/tools/baseline_frontier.py')
frontier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(frontier)


def original_oracle(states):
    # Execute the actual unchanged checker predicate and key expression, not a
    # separately maintained approximation of its floating-point/set semantics.
    tree = ast.parse((ROOT / 'optimization/tools/check.py').read_text(encoding='utf-8-sig'))
    baseline = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == 'baseline')
    dom = next(n for n in baseline.body if isinstance(n, ast.FunctionDef) and n.name == 'dom')
    key = next(n for n in baseline.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == 'key' for t in n.targets))
    module = ast.fix_missing_locations(ast.Module(body=[dom, key], type_ignores=[]))
    env = {'EPS': 1e-9}
    exec(compile(module, 'original_checker_predicate', 'exec'), env)
    return {env['key'](a) for a in states
            if not any(env['dom'](b, a) for b in states if b is not a)}


def state(floor=1.0, ceiling=2.0, **kwargs):
    return dict(node='cn:company', w=dict(floor=floor, ceiling=ceiling),
                needs=frozenset(), hops=1, restructure=0, transfers=frozenset(), new=0, **kwargs)


@pytest.mark.parametrize('seed', range(40))
def test_matches_actual_exhaustive_checker_with_duplicates_and_epsilon_boundaries(seed):
    rng = random.Random(seed)
    states = []
    for index in range(65):
        a = state(rng.choice([0.0, 1.0, 1.0+0.5e-9, 1.0+1.5e-9, 3.0]),
                  rng.choice([1.0, 2.0, 2.0+0.5e-9, 2.0+1.5e-9, 4.0]))
        a.update(node=rng.choice(['cn:company','hk:company']),
                 needs=frozenset((('bo','true'),) if rng.randrange(2) else ()),
                 hops=rng.randrange(1,4), restructure=rng.randrange(2), new=rng.randrange(2),
                 transfers=frozenset(('sale',) if rng.randrange(2) else ()), path=[str(index)])
        states.extend([a, copy.deepcopy(a)])
    expected = original_oracle(states)
    assert frontier.nondominated_state_keys(states) == expected
    rng.shuffle(states)
    assert frontier.nondominated_state_keys(states) == expected


def test_dominated_witnesses_are_not_discarded_when_epsilon_is_nontransitive():
    states = [state(1.0, 2.0), state(1.0+0.75e-9, 2.0-0.75e-9),
              state(1.0+1.5e-9, 2.0-1.5e-9)]
    assert frontier.nondominated_state_keys(states) == original_oracle(states)


def test_exact_duplicates_compress_without_comparing_each_path(monkeypatch):
    a = state(); b = state(3.0,4.0)
    calls = []
    original = frontier._dominates
    def counted(*args):
        calls.append(1)
        return original(*args)
    monkeypatch.setattr(frontier, '_dominates', counted)
    assert frontier.nondominated_state_keys([copy.deepcopy(a) for _ in range(5000)] + [b]) == {frontier.state_key(a)}
    assert len(calls) == 2


def test_empty_states():
    assert frontier.nondominated_state_keys([]) == set()


def test_missing_optional_fields_and_distinct_paths_are_equivalent_states():
    a = state(path=['first'])
    b = state(path=['second'])
    del b['new']
    del b['transfers']
    assert frontier.state_key(a) == frontier.state_key(b)
    assert frontier.nondominated_state_keys([a,b]) == original_oracle([a,b]) == {frontier.state_key(a)}


def test_equal_cost_states_with_incomparable_obligations_both_survive():
    a, b = state(), state()
    a['needs'] = frozenset({('bo','true')})
    b['needs'] = frozenset({('ppt','true')})
    expected = {frontier.state_key(a), frontier.state_key(b)}
    assert frontier.nondominated_state_keys([a,b,copy.deepcopy(a)]) == original_oracle([a,b]) == expected
