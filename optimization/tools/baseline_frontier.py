"""Exact duplicate compression for exhaustive checker destination states.

This does not prune DFS paths or assume epsilon dominance is transitive. Every
unique destination state remains a possible dominator, even if itself dominated.
"""


def state_key(state):
    return (state["node"], state["w"]["floor"], state["w"]["ceiling"],
            tuple(sorted(state["needs"])), state["hops"], state["restructure"],
            tuple(sorted(state.get("transfers", ()))), state.get("new", 0))


def _dominates(a, b, epsilon):
    return (a[0] == b[0] and a[1] <= b[1] + epsilon and a[2] <= b[2] + epsilon
            and a[3] <= b[3] and a[4] <= b[4] and a[5] <= b[5]
            and a[6] <= b[6] and a[7] <= b[7] and a != b)


def nondominated_state_keys(states, *, epsilon=1e-9):
    """Return exactly the state-key set used by the original exhaustive checker.

Path identity is absent from both dominance and the final comparison. Removing
an exact duplicate cannot remove a strictly dominating witness. Grouping by node
only skips pairs which the original predicate necessarily rejects. Keep all
unique states in each group, rather than filtering against a rolling frontier:
with an epsilon tolerance the original relation need not be transitive.
"""
    groups = {}
    for state in states:
        key = state_key(state)
        comparable = (key[0], key[1], key[2], frozenset(key[3]), key[4], key[5],
                      frozenset(key[6]), key[7])
        groups.setdefault(key[0], {})[key] = comparable
    result = set()
    for group in groups.values():
        values = list(group.items())
        for key, candidate in values:
            if not any(_dominates(other, candidate, epsilon)
                       for other_key, other in values if other_key != key):
                result.add(key)
    return result
