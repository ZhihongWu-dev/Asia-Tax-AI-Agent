"""Capture authored Li rules and executable inputs before reading cloud sources."""
import csv
from hashlib import sha256
import io
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
FILES = (
    'rule/rule.csv', 'rule/variable.csv', 'rule/predicate.csv',
    'rule/decision.csv', 'rule/rule_test.csv', 'optimization/move.csv',
    'rule/tools/common.py', 'rule/tools/eval.py', 'rule/tools/query.py',
    'rule/tools/rule_tool.py', 'optimization/tools/optimize.py',
    'optimization/tools/check.py', 'packages/domain_bridge/planning_library.py',
    'optimization/tools/baseline_frontier.py',
    'packages/domain_bridge/planning_runner.py', 'packages/domain_bridge/planning_runtime.py',
)


def capture_runtime(root=ROOT):
    """Missing files fail closed. Citations correspond to the exact hashed bytes.

    Deployment must keep release directories immutable for an attempt's lifetime;
    before/after equality detects changes but is not a filesystem transaction.
    """
    raw = {name: (Path(root) / name).read_bytes() for name in FILES}
    citations = set()
    for name, field in (('rule/rule.csv', 'cite_ids'),
                        ('rule/predicate.csv', 'factors_cite'),
                        ('rule/decision.csv', 'cite_id')):
        for row in csv.DictReader(io.StringIO(raw[name].decode('utf-8-sig'))):
            citations.update(c.strip() for c in row[field].split(';') if c.strip())
            if name == 'rule/rule.csv':
                # Procedure entries mix document IDs, absence IDs and clause IDs.
                # Only clauses need passage materialization in the source bundle.
                citations.update(c.strip() for c in row.get('procedure', '').split(';')
                                 if '#' in c)
    return {'schema': 1, 'files': {name: sha256(body).hexdigest() for name, body in raw.items()},
            'citations': sorted(citations)}
