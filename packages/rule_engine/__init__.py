"""L0 rule engine: deterministic execution of the FSIE judgement chain.

The engine is a workflow, not an AI skill: every node is evaluated by pure,
versioned code reading data-driven thresholds from the knowledge package.
Same facts + same rule version => same structured result, every time.
"""

from packages.rule_engine.evaluators import FactView, NodeOutcome
from packages.rule_engine.runner import (
    CaseExpectation,
    ChainRule,
    RunOutcome,
    check_expectation,
    run_chain,
)

__all__ = [
    "CaseExpectation",
    "ChainRule",
    "FactView",
    "NodeOutcome",
    "RunOutcome",
    "check_expectation",
    "run_chain",
]
