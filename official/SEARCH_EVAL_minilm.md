# SEARCH_EVAL

由 `tools/eval_search.py` 生成，不要手改。金标准取自本项目自己追溯过的引用（参数、规则裁量项、字典缺口各自引用的条款；条约同一条款的中英文对照），命中按条款计：本条、同一条款的其他文本、本条所含的款都算。

向量模型：sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2。权重只在 params 上选（开发集），rules、gaps、xlang 是测试集。

| 集合 | 配置 | 切分 | 条数 | R@1 | R@5 | R@10 | R@50 | MRR@10 |
|---|---|---|---|---|---|---|---|---|
| params (dev) | bm25 | all | 300 | 0.060 | 0.137 | 0.187 | 0.367 | 0.091 |
| params (dev) | bm25 | gold en | 146 | 0.110 | 0.253 | 0.349 | 0.644 | 0.168 |
| params (dev) | bm25 | gold zh | 154 | 0.013 | 0.026 | 0.032 | 0.104 | 0.018 |
| params (dev) | dense | all | 300 | 0.020 | 0.087 | 0.137 | 0.287 | 0.048 |
| params (dev) | dense | gold en | 146 | 0.021 | 0.089 | 0.123 | 0.281 | 0.044 |
| params (dev) | dense | gold zh | 154 | 0.019 | 0.084 | 0.149 | 0.292 | 0.051 |
| params (dev) | balanced bm25+dense | all | 300 | 0.020 | 0.127 | 0.190 | 0.407 | 0.061 |
| params (dev) | balanced bm25+dense | gold en | 146 | 0.041 | 0.151 | 0.199 | 0.479 | 0.080 |
| params (dev) | balanced bm25+dense | gold zh | 154 | 0.000 | 0.104 | 0.182 | 0.338 | 0.043 |
| params (dev) | balanced bm25+dense+graph w.5 | all | 300 | 0.023 | 0.127 | 0.190 | 0.417 | 0.065 |
| params (dev) | balanced bm25+dense+graph w.5 | gold en | 146 | 0.048 | 0.171 | 0.205 | 0.507 | 0.091 |
| params (dev) | balanced bm25+dense+graph w.5 | gold zh | 154 | 0.000 | 0.084 | 0.175 | 0.331 | 0.041 |
| params (dev) | balanced all+exact | all | 300 | 0.023 | 0.127 | 0.190 | 0.417 | 0.065 |
| params (dev) | balanced all+exact | gold en | 146 | 0.048 | 0.171 | 0.205 | 0.507 | 0.091 |
| params (dev) | balanced all+exact | gold zh | 154 | 0.000 | 0.084 | 0.175 | 0.331 | 0.041 |
| rules | bm25 | all | 46 | 0.000 | 0.043 | 0.043 | 0.391 | 0.022 |
| rules | bm25 | gold en | 21 | 0.000 | 0.095 | 0.095 | 0.857 | 0.048 |
| rules | bm25 | gold zh | 25 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| rules | dense | all | 46 | 0.000 | 0.000 | 0.065 | 0.130 | 0.008 |
| rules | dense | gold en | 21 | 0.000 | 0.000 | 0.095 | 0.143 | 0.011 |
| rules | dense | gold zh | 25 | 0.000 | 0.000 | 0.040 | 0.120 | 0.007 |
| rules | balanced bm25+dense | all | 46 | 0.043 | 0.043 | 0.065 | 0.326 | 0.047 |
| rules | balanced bm25+dense | gold en | 21 | 0.095 | 0.095 | 0.095 | 0.571 | 0.095 |
| rules | balanced bm25+dense | gold zh | 25 | 0.000 | 0.000 | 0.040 | 0.120 | 0.007 |
| rules | balanced bm25+dense+graph w.5 | all | 46 | 0.043 | 0.043 | 0.065 | 0.457 | 0.047 |
| rules | balanced bm25+dense+graph w.5 | gold en | 21 | 0.095 | 0.095 | 0.095 | 0.857 | 0.095 |
| rules | balanced bm25+dense+graph w.5 | gold zh | 25 | 0.000 | 0.000 | 0.040 | 0.120 | 0.007 |
| rules | balanced all+exact | all | 46 | 0.043 | 0.043 | 0.065 | 0.457 | 0.047 |
| rules | balanced all+exact | gold en | 21 | 0.095 | 0.095 | 0.095 | 0.857 | 0.095 |
| rules | balanced all+exact | gold zh | 25 | 0.000 | 0.000 | 0.040 | 0.120 | 0.007 |
| gaps | bm25 | all | 65 | 0.015 | 0.046 | 0.123 | 0.338 | 0.037 |
| gaps | bm25 | gold en | 40 | 0.025 | 0.075 | 0.200 | 0.525 | 0.060 |
| gaps | bm25 | gold zh | 25 | 0.000 | 0.000 | 0.000 | 0.040 | 0.000 |
| gaps | dense | all | 65 | 0.015 | 0.031 | 0.031 | 0.138 | 0.021 |
| gaps | dense | gold en | 40 | 0.025 | 0.050 | 0.050 | 0.225 | 0.033 |
| gaps | dense | gold zh | 25 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| gaps | balanced bm25+dense | all | 65 | 0.015 | 0.031 | 0.108 | 0.292 | 0.033 |
| gaps | balanced bm25+dense | gold en | 40 | 0.025 | 0.050 | 0.175 | 0.400 | 0.054 |
| gaps | balanced bm25+dense | gold zh | 25 | 0.000 | 0.000 | 0.000 | 0.120 | 0.000 |
| gaps | balanced bm25+dense+graph w.5 | all | 65 | 0.015 | 0.077 | 0.138 | 0.277 | 0.044 |
| gaps | balanced bm25+dense+graph w.5 | gold en | 40 | 0.025 | 0.125 | 0.225 | 0.375 | 0.072 |
| gaps | balanced bm25+dense+graph w.5 | gold zh | 25 | 0.000 | 0.000 | 0.000 | 0.120 | 0.000 |
| gaps | balanced all+exact | all | 65 | 0.015 | 0.077 | 0.138 | 0.277 | 0.044 |
| gaps | balanced all+exact | gold en | 40 | 0.025 | 0.125 | 0.225 | 0.375 | 0.072 |
| gaps | balanced all+exact | gold zh | 25 | 0.000 | 0.000 | 0.000 | 0.120 | 0.000 |
| xlang | bm25 | all | 240 | 0.083 | 0.304 | 0.354 | 0.383 | 0.176 |
| xlang | bm25 | gold en | 120 | 0.000 | 0.383 | 0.483 | 0.533 | 0.159 |
| xlang | bm25 | gold zh | 120 | 0.167 | 0.225 | 0.225 | 0.233 | 0.192 |
| xlang | dense | all | 240 | 0.046 | 0.121 | 0.142 | 0.279 | 0.078 |
| xlang | dense | gold en | 120 | 0.008 | 0.025 | 0.042 | 0.200 | 0.019 |
| xlang | dense | gold zh | 120 | 0.083 | 0.217 | 0.242 | 0.358 | 0.137 |
| xlang | balanced bm25+dense | all | 240 | 0.075 | 0.204 | 0.237 | 0.379 | 0.123 |
| xlang | balanced bm25+dense | gold en | 120 | 0.000 | 0.158 | 0.200 | 0.392 | 0.061 |
| xlang | balanced bm25+dense | gold zh | 120 | 0.150 | 0.250 | 0.275 | 0.367 | 0.185 |
| xlang | balanced bm25+dense+graph w.5 | all | 240 | 0.062 | 0.417 | 0.562 | 0.775 | 0.213 |
| xlang | balanced bm25+dense+graph w.5 | gold en | 120 | 0.000 | 0.492 | 0.767 | 0.967 | 0.221 |
| xlang | balanced bm25+dense+graph w.5 | gold zh | 120 | 0.125 | 0.342 | 0.358 | 0.583 | 0.205 |
| xlang | balanced all+exact | all | 240 | 0.062 | 0.417 | 0.562 | 0.775 | 0.213 |
| xlang | balanced all+exact | gold en | 120 | 0.000 | 0.492 | 0.767 | 0.967 | 0.221 |
| xlang | balanced all+exact | gold zh | 120 | 0.125 | 0.342 | 0.358 | 0.583 | 0.205 |

局限：查询是建库时写下的简短标识，每条只有一两个标注的相关条款，未标注的相关条款计为未命中（BEIR 的 Hole@10 问题）；xlang 只覆盖条约，因为只有条约在库内同时有中英文文本。
