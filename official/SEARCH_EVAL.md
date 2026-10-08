# SEARCH_EVAL

由 `tools/eval_search.py` 生成，不要手改。金标准取自本项目自己追溯过的引用（参数、规则裁量项、字典缺口各自引用的条款；条约同一条款的中英文对照），命中按条款计：本条、同一条款的其他文本、本条所含的款都算。

向量模型：BAAI/bge-m3。权重只在 params 上选（开发集），rules、gaps、xlang 是测试集。

| 集合 | 配置 | 切分 | 条数 | R@1 | R@5 | R@10 | R@50 | MRR@10 |
|---|---|---|---|---|---|---|---|---|
| params (dev) | bm25 | all | 300 | 0.060 | 0.137 | 0.187 | 0.367 | 0.091 |
| params (dev) | bm25 | gold en | 146 | 0.110 | 0.253 | 0.349 | 0.644 | 0.168 |
| params (dev) | bm25 | gold zh | 154 | 0.013 | 0.026 | 0.032 | 0.104 | 0.018 |
| params (dev) | dense | all | 300 | 0.120 | 0.263 | 0.327 | 0.527 | 0.179 |
| params (dev) | dense | gold en | 146 | 0.164 | 0.363 | 0.432 | 0.658 | 0.244 |
| params (dev) | dense | gold zh | 154 | 0.078 | 0.169 | 0.227 | 0.403 | 0.117 |
| params (dev) | balanced bm25+dense | all | 300 | 0.097 | 0.263 | 0.353 | 0.593 | 0.177 |
| params (dev) | balanced bm25+dense | gold en | 146 | 0.171 | 0.301 | 0.390 | 0.692 | 0.226 |
| params (dev) | balanced bm25+dense | gold zh | 154 | 0.026 | 0.227 | 0.318 | 0.500 | 0.131 |
| params (dev) | balanced bm25+dense+graph w.5 | all | 300 | 0.083 | 0.263 | 0.377 | 0.613 | 0.166 |
| params (dev) | balanced bm25+dense+graph w.5 | gold en | 146 | 0.144 | 0.329 | 0.459 | 0.733 | 0.226 |
| params (dev) | balanced bm25+dense+graph w.5 | gold zh | 154 | 0.026 | 0.201 | 0.299 | 0.500 | 0.110 |
| params (dev) | bm25+dense w.5 | all | 300 | 0.083 | 0.177 | 0.240 | 0.393 | 0.126 |
| params (dev) | bm25+dense w.5 | gold en | 146 | 0.151 | 0.329 | 0.452 | 0.705 | 0.231 |
| params (dev) | bm25+dense w.5 | gold zh | 154 | 0.019 | 0.032 | 0.039 | 0.097 | 0.027 |
| params (dev) | bm25+dense+graph w.5 | all | 300 | 0.073 | 0.183 | 0.273 | 0.433 | 0.124 |
| params (dev) | bm25+dense+graph w.5 | gold en | 146 | 0.137 | 0.336 | 0.514 | 0.788 | 0.230 |
| params (dev) | bm25+dense+graph w.5 | gold zh | 154 | 0.013 | 0.039 | 0.045 | 0.097 | 0.025 |
| rules | bm25 | all | 46 | 0.000 | 0.043 | 0.043 | 0.391 | 0.022 |
| rules | bm25 | gold en | 21 | 0.000 | 0.095 | 0.095 | 0.857 | 0.048 |
| rules | bm25 | gold zh | 25 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| rules | dense | all | 46 | 0.022 | 0.087 | 0.087 | 0.239 | 0.040 |
| rules | dense | gold en | 21 | 0.000 | 0.095 | 0.095 | 0.429 | 0.024 |
| rules | dense | gold zh | 25 | 0.040 | 0.080 | 0.080 | 0.080 | 0.053 |
| rules | balanced bm25+dense | all | 46 | 0.043 | 0.087 | 0.087 | 0.391 | 0.065 |
| rules | balanced bm25+dense | gold en | 21 | 0.095 | 0.095 | 0.095 | 0.762 | 0.095 |
| rules | balanced bm25+dense | gold zh | 25 | 0.000 | 0.080 | 0.080 | 0.080 | 0.040 |
| rules | balanced bm25+dense+graph w.5 | all | 46 | 0.043 | 0.065 | 0.087 | 0.391 | 0.058 |
| rules | balanced bm25+dense+graph w.5 | gold en | 21 | 0.095 | 0.095 | 0.095 | 0.762 | 0.095 |
| rules | balanced bm25+dense+graph w.5 | gold zh | 25 | 0.000 | 0.040 | 0.080 | 0.080 | 0.027 |
| rules | bm25+dense w.5 | all | 46 | 0.043 | 0.043 | 0.043 | 0.413 | 0.043 |
| rules | bm25+dense w.5 | gold en | 21 | 0.095 | 0.095 | 0.095 | 0.905 | 0.095 |
| rules | bm25+dense w.5 | gold zh | 25 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| rules | bm25+dense+graph w.5 | all | 46 | 0.000 | 0.043 | 0.130 | 0.457 | 0.028 |
| rules | bm25+dense+graph w.5 | gold en | 21 | 0.000 | 0.095 | 0.286 | 1.000 | 0.062 |
| rules | bm25+dense+graph w.5 | gold zh | 25 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| gaps | bm25 | all | 65 | 0.015 | 0.046 | 0.123 | 0.338 | 0.037 |
| gaps | bm25 | gold en | 40 | 0.025 | 0.075 | 0.200 | 0.525 | 0.060 |
| gaps | bm25 | gold zh | 25 | 0.000 | 0.000 | 0.000 | 0.040 | 0.000 |
| gaps | dense | all | 65 | 0.062 | 0.123 | 0.185 | 0.308 | 0.098 |
| gaps | dense | gold en | 40 | 0.075 | 0.150 | 0.250 | 0.425 | 0.122 |
| gaps | dense | gold zh | 25 | 0.040 | 0.080 | 0.080 | 0.120 | 0.060 |
| gaps | balanced bm25+dense | all | 65 | 0.046 | 0.154 | 0.246 | 0.369 | 0.097 |
| gaps | balanced bm25+dense | gold en | 40 | 0.075 | 0.200 | 0.325 | 0.475 | 0.135 |
| gaps | balanced bm25+dense | gold zh | 25 | 0.000 | 0.080 | 0.120 | 0.200 | 0.037 |
| gaps | balanced bm25+dense+graph w.5 | all | 65 | 0.046 | 0.123 | 0.246 | 0.369 | 0.100 |
| gaps | balanced bm25+dense+graph w.5 | gold en | 40 | 0.075 | 0.200 | 0.325 | 0.475 | 0.149 |
| gaps | balanced bm25+dense+graph w.5 | gold zh | 25 | 0.000 | 0.000 | 0.120 | 0.200 | 0.020 |
| gaps | bm25+dense w.5 | all | 65 | 0.031 | 0.108 | 0.169 | 0.323 | 0.059 |
| gaps | bm25+dense w.5 | gold en | 40 | 0.050 | 0.175 | 0.275 | 0.500 | 0.096 |
| gaps | bm25+dense w.5 | gold zh | 25 | 0.000 | 0.000 | 0.000 | 0.040 | 0.000 |
| gaps | bm25+dense+graph w.5 | all | 65 | 0.031 | 0.077 | 0.169 | 0.385 | 0.062 |
| gaps | bm25+dense+graph w.5 | gold en | 40 | 0.050 | 0.125 | 0.275 | 0.600 | 0.100 |
| gaps | bm25+dense+graph w.5 | gold zh | 25 | 0.000 | 0.000 | 0.000 | 0.040 | 0.000 |
| xlang | bm25 | all | 240 | 0.083 | 0.304 | 0.354 | 0.383 | 0.176 |
| xlang | bm25 | gold en | 120 | 0.000 | 0.383 | 0.483 | 0.533 | 0.159 |
| xlang | bm25 | gold zh | 120 | 0.167 | 0.225 | 0.225 | 0.233 | 0.192 |
| xlang | dense | all | 240 | 0.087 | 0.371 | 0.467 | 0.704 | 0.196 |
| xlang | dense | gold en | 120 | 0.000 | 0.467 | 0.617 | 0.867 | 0.165 |
| xlang | dense | gold zh | 120 | 0.175 | 0.275 | 0.317 | 0.542 | 0.228 |
| xlang | balanced bm25+dense | all | 240 | 0.079 | 0.608 | 0.717 | 0.838 | 0.313 |
| xlang | balanced bm25+dense | gold en | 120 | 0.000 | 0.850 | 0.917 | 0.967 | 0.382 |
| xlang | balanced bm25+dense | gold zh | 120 | 0.158 | 0.367 | 0.517 | 0.708 | 0.244 |
| xlang | balanced bm25+dense+graph w.5 | all | 240 | 0.029 | 0.604 | 0.825 | 0.950 | 0.285 |
| xlang | balanced bm25+dense+graph w.5 | gold en | 120 | 0.000 | 0.733 | 0.950 | 0.992 | 0.326 |
| xlang | balanced bm25+dense+graph w.5 | gold zh | 120 | 0.058 | 0.475 | 0.700 | 0.908 | 0.244 |
| xlang | bm25+dense w.5 | all | 240 | 0.079 | 0.321 | 0.367 | 0.388 | 0.177 |
| xlang | bm25+dense w.5 | gold en | 120 | 0.000 | 0.417 | 0.508 | 0.542 | 0.162 |
| xlang | bm25+dense w.5 | gold zh | 120 | 0.158 | 0.225 | 0.225 | 0.233 | 0.192 |
| xlang | bm25+dense+graph w.5 | all | 240 | 0.033 | 0.192 | 0.367 | 0.792 | 0.107 |
| xlang | bm25+dense+graph w.5 | gold en | 120 | 0.050 | 0.200 | 0.492 | 0.933 | 0.136 |
| xlang | bm25+dense+graph w.5 | gold zh | 120 | 0.017 | 0.183 | 0.242 | 0.650 | 0.078 |

局限：查询是建库时写下的简短标识，每条只有一两个标注的相关条款，未标注的相关条款计为未命中（BEIR 的 Hole@10 问题）；xlang 只覆盖条约，因为只有条约在库内同时有中英文文本。
