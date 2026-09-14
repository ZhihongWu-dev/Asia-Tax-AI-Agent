# Packages

本目录用于未来可复用的业务与技术模块，例如税务规则执行、资料检索、案例评测和共享数据结构。

规则执行、RAG 检索和案例评测必须保持独立边界，不能把检索结果直接当作确定性规则结论或评测金标。

## 已有模块

- [`contracts/`](contracts/)：跨地区共享的数据契约——状态机枚举、资产 JSON Schema、Python 枚举和香港 FSIE 事实字段字典，是数据库、规则引擎、事实卡和案例的共同上游。详见 [contracts/README](contracts/README.md)。
