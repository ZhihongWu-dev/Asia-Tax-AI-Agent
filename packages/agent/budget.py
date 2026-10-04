"""One budget across graph nodes, retries, analysis and nested provider calls."""
from contextvars import ContextVar
from copy import deepcopy
from dataclasses import dataclass, field
from time import monotonic
import json

current_budget: ContextVar = ContextVar('agent_budget', default=None)


class BudgetExceeded(RuntimeError):
    pass


@dataclass
class RunBudget:
    seconds: float = 45
    model_limit: int = 4
    action_limit: int = 4
    search_limit: int = 3
    evidence_limit: int = 14
    started: float = field(default_factory=monotonic)
    counts: dict = field(default_factory=dict)
    cache: dict = field(default_factory=dict)

    def remaining(self):
        return max(0, self.seconds - (monotonic() - self.started))

    def consume(self, kind):
        limit = getattr(self, kind + '_limit')
        if self.remaining() <= 0 or self.counts.get(kind, 0) >= limit:
            raise BudgetExceeded(kind)
        self.counts[kind] = self.counts.get(kind, 0) + 1

    def snapshot(self):
        return {**self.counts, 'elapsed_ms': round((monotonic() - self.started) * 1000, 2)}


def model_call(callback, *args):
    budget = current_budget.get()
    if budget:
        budget.consume('model')
    return callback(*args)


class BudgetedProvider:
    def __init__(self, provider, budget, facts_hash=''):
        self.provider = provider.for_request() if hasattr(provider, 'for_request') else provider
        self.budget, self.facts_hash = budget, facts_hash

    def search_evidence(self, request, context):
        payload = request.model_dump(mode='json', exclude={'request_id', 'trace_id', 'deadline_ms'})
        key = ('search', context.owner, context.case_id, self.facts_hash, json.dumps(payload, sort_keys=True))
        if key in self.budget.cache:
            result = deepcopy(self.budget.cache[key])
            return result.model_copy(update={'request_id': request.request_id, 'trace_id': request.trace_id})
        self.budget.consume('search')
        deadline = min(request.deadline_ms, max(1, int(self.budget.remaining() * 1000)))
        result = self.provider.search_evidence(request.model_copy(update={'deadline_ms': deadline}), context)
        from packages.agent.contracts import SearchResult
        result = SearchResult.model_validate(result)
        if result.request_id != request.request_id or result.trace_id != request.trace_id:
            raise ValueError('Response identity mismatch')
        if self.budget.remaining() <= 0:
            raise BudgetExceeded('time')
        if result.status != 'error':
            self.budget.cache[key] = deepcopy(result)
        return result

    def get_evidence(self, reference, purpose, context):
        key = ('evidence', context.owner, context.case_id, reference.model_dump_json(), purpose)
        if key in self.budget.cache:
            return deepcopy(self.budget.cache[key])
        self.budget.consume('evidence')
        # HTTP adapter enforces this deadline; legacy in-process adapters remain bounded
        # by their own DB timeout and are checked again on return.
        bounded = getattr(self.provider, 'get_evidence_bounded', None)
        result = bounded(reference, purpose, context, min(1, self.budget.remaining())) if bounded else \
            self.provider.get_evidence(reference, purpose, context)
        if self.budget.remaining() <= 0:
            raise BudgetExceeded('time')
        self.budget.cache[key] = deepcopy(result)
        return result
