"""fields.py (信息收集.md): the dictionary is the core fields plus the union of what the rules read (P1).

    FIELDS                      {"payee.residence_cert": {rule ids that read it}, ...}
    required_fields(graph)      {(flow id, "payee.residence_cert"), ...} for the rules that match the graph's flows (P2)
Nothing here is typed by hand: a field exists because some compiled rule reads it.
"""
from .engine import RULES
from .facts import facts_for, source_of
from .model import Graph
from .rules.eval import Flow, matches, valid_on

CORE = {
    "EVENT": ("flows", "horizon", "budget"),
    "ENTITY": ("id", "type", "loc"),
    "HOLD": ("holder", "held", "ratio", "since", "cost"),
    "FLOW": ("payer", "payee", "income", "amount", "currency", "on"),
}


def fields(rules=None):
    out = {}
    for r in rules or RULES:
        for key in r.reads:
            out.setdefault(key, set()).add(r.id)
    return out


def flow_of(graph: Graph, f):
    facts = facts_for(graph, f)
    return Flow(graph.entities[f.payer].loc, graph.entities[f.payee].loc, f.income, on=f.on,
                target_loc=graph.entities[f.target].loc if f.target else None,
                indirect_cn=bool(facts.get(("flow", "indirect_cn_target"))), id=f.id), facts


def required_fields(graph: Graph, rules=None):
    """Static upper bound of what this case may need: every field read by a rule whose scope matches a flow."""
    need = set()
    for f in graph.flows:
        flow, _ = flow_of(graph, f)
        for r in rules or RULES:
            if matches(r.scope, flow) and valid_on(r, flow.on):
                need |= {(f.id, key) for key in r.reads}
    return need


def missing_fields(graph: Graph, rules=None):
    """Required fields the graph does not state or derive (what the first collection round asks for)."""
    out = set()
    for f in graph.flows:
        flow, facts = flow_of(graph, f)
        for r in rules or RULES:
            if matches(r.scope, flow) and valid_on(r, flow.on):
                for key in r.reads:
                    elem, field = key.split(".", 1)
                    if facts.get((elem, field)) is None:
                        out.add((f.id, key))
    return out
