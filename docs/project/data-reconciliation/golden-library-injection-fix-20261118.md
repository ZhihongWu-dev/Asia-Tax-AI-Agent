# Golden runner library injection

The external v3 runner replaced `check.op.Optimizer` with a function to inject
the staged library. That also replaced the class name used by recursive
`Optimizer._compare_nodes` calls. It failed while generating open items, before
completing the first golden case. Session 66099 exited with status 1.

`check.run_tests` now accepts an optional keyword-only `lib`, matching the
optimizer's existing constructor interface. Existing callers retain the default
library. The external v4 runner passes the verified library directly and leaves
the optimizer class unchanged.

Preflight using the actual staged PlanningLibrary verified class identity,
nested AND/NOT/OR comparisons, injected-library identity, and flip-value
generation for every authored variable. No monkeypatch was used.

The v4 script is prepared in the external audit directory but has not been
started: the procedure dependency set still includes a rejected source and
the isolated dated Indonesian repair is not promoted yet. Do not describe v3
or the prepared v4 runner as a completed optimizer acceptance.
