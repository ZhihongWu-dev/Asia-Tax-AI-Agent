# Packages

本目录保存可复用的业务与技术模块。

规则执行、RAG 检索和案例评测必须保持独立边界，不能把检索结果直接当作确定性规则结论或评测金标。

## 已有模块

- [`contracts/`](contracts/)：跨地区共享的数据契约——状态机枚举、资产 JSON Schema、Python 枚举和香港 FSIE 事实字段字典，是数据库、规则引擎、事实卡和案例的共同上游。详见 [contracts/README](contracts/README.md)。
- `intake/`：自然语言事实提取、字典校验和命令行入口。
- `model_adapter/`：模型服务配置与调用适配。
- `knowledge_loader/`：知识包解析、校验和数据库载入。
- `knowledge_pipeline/`：官方来源抓取、快照和法律文本分段。
- `rule_engine/`：确定性规则链与虚构案例评测。
- `persistence/`：数据库模型、连接与系统设置。
- `reporting/`：研究报告组装与 Markdown 输出。
