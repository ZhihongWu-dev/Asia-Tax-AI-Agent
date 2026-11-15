# Retrieval evaluation

Written by agent/tools/read_eval.py on 2026-11-03T16:43:50Z (case CASE-20261102-a032c0, sample 120). Golden sets and the adoption rule: the module docstring and agent/retrieval_spec.en.md §12. Even items are the development set, odd items the test set.

| Set | Config | Split | n | R@1 | R@5 | R@10 | MRR@10 | nDCG@10 | s/query |
|---|---|---|---|---|---|---|---|---|---|
| L-params | bm25 | dev | 60 | 0.117 | 0.133 | 0.167 | 0.129 | 0.138 | 0.17 |
| L-params | bm25 | test | 60 | 0.067 | 0.083 | 0.083 | 0.072 | 0.075 | 0.18 |
| L-params | +dense | dev | 60 | 0.083 | 0.150 | 0.200 | 0.113 | 0.133 | 0.32 |
| L-params | +dense | test | 60 | 0.033 | 0.100 | 0.150 | 0.060 | 0.080 | 0.32 |
| L-params | +balance | dev | 60 | 0.083 | 0.267 | 0.350 | 0.156 | 0.202 | 0.28 |
| L-params | +balance | test | 60 | 0.033 | 0.133 | 0.267 | 0.088 | 0.130 | 0.29 |
| L-params | +graph | dev | 60 | 0.067 | 0.233 | 0.367 | 0.150 | 0.200 | 0.32 |
| L-params | +graph | test | 60 | 0.033 | 0.183 | 0.300 | 0.108 | 0.153 | 0.30 |
| L-params | +rerank | dev | 60 | 0.133 | 0.350 | 0.433 | 0.219 | 0.270 | 1.67 |
| L-params | +rerank | test | 60 | 0.133 | 0.317 | 0.383 | 0.210 | 0.252 | 1.46 |
| L-params | -graph+rerank | dev | 60 | 0.133 | 0.350 | 0.417 | 0.218 | 0.265 | 1.23 |
| L-params | -graph+rerank | test | 60 | 0.133 | 0.283 | 0.383 | 0.201 | 0.244 | 1.41 |
| L-rules | bm25 | dev | 60 | 0.300 | 0.350 | 0.383 | 0.324 | 0.320 | 0.17 |
| L-rules | bm25 | test | 60 | 0.250 | 0.250 | 0.300 | 0.256 | 0.234 | 0.16 |
| L-rules | +dense | dev | 60 | 0.333 | 0.350 | 0.350 | 0.342 | 0.320 | 0.32 |
| L-rules | +dense | test | 60 | 0.200 | 0.283 | 0.300 | 0.235 | 0.216 | 0.31 |
| L-rules | +balance | dev | 60 | 0.333 | 0.400 | 0.417 | 0.366 | 0.346 | 0.32 |
| L-rules | +balance | test | 60 | 0.200 | 0.333 | 0.367 | 0.247 | 0.225 | 0.28 |
| L-rules | +graph | dev | 60 | 0.300 | 0.400 | 0.417 | 0.340 | 0.328 | 0.29 |
| L-rules | +graph | test | 60 | 0.200 | 0.300 | 0.367 | 0.243 | 0.222 | 0.29 |
| L-rules | +rerank | dev | 60 | 0.333 | 0.400 | 0.433 | 0.362 | 0.330 | 2.14 |
| L-rules | +rerank | test | 60 | 0.283 | 0.300 | 0.367 | 0.297 | 0.258 | 1.71 |
| L-rules | -graph+rerank | dev | 60 | 0.333 | 0.400 | 0.433 | 0.361 | 0.330 | 1.75 |
| L-rules | -graph+rerank | test | 60 | 0.283 | 0.300 | 0.400 | 0.301 | 0.267 | 1.67 |
| L-decisions | bm25 | dev | 11 | 0.182 | 0.545 | 0.636 | 0.279 | 0.363 | 0.21 |
| L-decisions | bm25 | test | 10 | 0.200 | 0.700 | 0.700 | 0.362 | 0.445 | 0.22 |
| L-decisions | +dense | dev | 11 | 0.091 | 0.636 | 0.636 | 0.326 | 0.405 | 0.34 |
| L-decisions | +dense | test | 10 | 0.200 | 0.700 | 0.700 | 0.425 | 0.495 | 0.35 |
| L-decisions | +balance | dev | 11 | 0.091 | 0.636 | 0.636 | 0.253 | 0.347 | 0.32 |
| L-decisions | +balance | test | 10 | 0.200 | 0.800 | 0.800 | 0.400 | 0.499 | 0.34 |
| L-decisions | +graph | dev | 11 | 0.091 | 0.545 | 0.727 | 0.270 | 0.379 | 0.33 |
| L-decisions | +graph | test | 10 | 0.200 | 0.800 | 0.900 | 0.438 | 0.551 | 0.35 |
| L-decisions | +rerank | dev | 11 | 0.000 | 0.455 | 0.545 | 0.145 | 0.241 | 1.54 |
| L-decisions | +rerank | test | 10 | 0.000 | 0.600 | 0.700 | 0.218 | 0.334 | 1.52 |
| L-decisions | -graph+rerank | dev | 11 | 0.000 | 0.364 | 0.545 | 0.136 | 0.232 | 1.18 |
| L-decisions | -graph+rerank | test | 10 | 0.000 | 0.500 | 0.700 | 0.213 | 0.328 | 1.28 |
| L-xlang | bm25 | dev | 30 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.05 |
| L-xlang | bm25 | test | 30 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.06 |
| L-xlang | +dense | dev | 30 | 0.867 | 0.933 | 0.933 | 0.894 | 0.904 | 0.21 |
| L-xlang | +dense | test | 30 | 0.833 | 0.900 | 0.900 | 0.858 | 0.869 | 0.22 |
| L-xlang | +balance | dev | 30 | 0.867 | 0.933 | 0.933 | 0.894 | 0.904 | 0.20 |
| L-xlang | +balance | test | 30 | 0.833 | 0.900 | 0.900 | 0.858 | 0.869 | 0.22 |
| L-xlang | +graph | dev | 30 | 0.867 | 0.933 | 0.933 | 0.894 | 0.904 | 0.23 |
| L-xlang | +graph | test | 30 | 0.733 | 0.900 | 0.900 | 0.800 | 0.825 | 0.22 |
| L-xlang | +rerank | dev | 30 | 0.800 | 0.933 | 0.933 | 0.861 | 0.880 | 0.96 |
| L-xlang | +rerank | test | 30 | 0.833 | 0.933 | 0.933 | 0.878 | 0.892 | 1.06 |
| L-xlang | -graph+rerank | dev | 30 | 0.800 | 0.933 | 0.933 | 0.861 | 0.880 | 0.91 |
| L-xlang | -graph+rerank | test | 30 | 0.833 | 0.933 | 0.933 | 0.878 | 0.892 | 1.03 |
| P-template | bm25 | dev | 17 | 0.059 | 0.294 | 0.353 | 0.157 | 0.205 | 0.01 |
| P-template | bm25 | test | 16 | 0.125 | 0.250 | 0.312 | 0.182 | 0.214 | 0.00 |
| P-template | +rerank | dev | 17 | 0.412 | 0.588 | 0.647 | 0.494 | 0.494 | 0.40 |
| P-template | +rerank | test | 16 | 0.250 | 0.500 | 0.500 | 0.359 | 0.399 | 0.38 |
| P-hand | bm25 | dev | 5 | 0.600 | 0.600 | 0.600 | 0.600 | 0.525 | 0.00 |
| P-hand | bm25 | test | 5 | 0.600 | 0.600 | 0.600 | 0.600 | 0.525 | 0.00 |
| P-hand | +rerank | dev | 5 | 0.800 | 0.800 | 1.000 | 0.822 | 0.555 | 0.37 |
| P-hand | +rerank | test | 5 | 0.800 | 0.800 | 1.000 | 0.822 | 0.555 | 0.37 |
| C-sources | bm25 | dev | 20 | 0.200 | 0.600 | 0.600 | 0.346 | 0.409 | 0.00 |
| C-sources | bm25 | test | 19 | 0.263 | 0.421 | 0.421 | 0.333 | 0.356 | 0.00 |
| C-sources | +rerank | dev | 20 | 0.300 | 0.550 | 0.600 | 0.384 | 0.436 | 0.11 |
| C-sources | +rerank | test | 19 | 0.368 | 0.421 | 0.421 | 0.395 | 0.402 | 0.09 |

## Decisions (mean change of nDCG@10 and R@10)

| Component | Dev | Test | Adopted |
|---|---|---|---|
| dense | (0.235, 0.233) | (0.226, 0.242) | True |
| balance | (0.009, 0.054) | (0.016, 0.071) | True |
| graph | (0.003, 0.027) | (0.007, 0.033) | True |
| rerank | (-0.023, -0.025) | (-0.004, -0.021) | False |
| products rerank | (0.16, 0.347) | (0.108, 0.294) | True |
| case rerank | (0.027, 0.0) | (0.046, 0.0) | True |

Switches written to agent/retrieval_settings.json: `{"law": {"bm25": true, "dense": true, "balance": true, "graph": true, "rerank": false}, "products": {"rerank": true}, "case": {"rerank": true}}`
