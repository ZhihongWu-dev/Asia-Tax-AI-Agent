# 文档导航

本目录保存产品、技术、项目治理、审查和设计记录。规划文档与实现代码分离，以便独立评审范围、规则、风险和验收门槛。

| 分类 | 文档 | 作用 |
|---|---|---|
| 产品 | [PRD](product/PRD.md) | 定义用户、范围、功能、知识治理和验收标准 |
| 架构 | [技术路线图](architecture/TECHNICAL_ROADMAP.md) | 定义技术边界、数据模型、安全和实施阶段 |
| 数据 | [数据集与数据来源说明](architecture/DATA_SOURCES_AND_DATASETS.md) | 定义 L0 所需预置数据集、各自来源渠道、依赖关系和 L1 数据缺口 |
| 实施 | [FSIE 数据提取与校验计划](implementation/FSIE_DATA_EXTRACTION_VALIDATION_PLAN.md) | 定义法源、规则、事实提取、校验、专家审核和回归发布流程 |
| 项目管理 | [2026 项目计划](project/PROJECT_PLAN_2026.md) | 定义时间、资源、负责人、依赖和降级方案 |
| 审查 | [批判性审查报告](reviews/2026-08-15-prd-roadmap-project-plan-plain-language-review.md) | 记录问题、批准修改和回归检查结果 |
| 设计记录 | `superpowers/specs/` | 保存已经形成的设计过程记录 |

规划文档不能代替香港或其他地区税务专家的专业鉴证。


## B Agent 接入开发（2026-10-02）

- **先读：[B 模块队友交接与后续迭代清单（2026-10-04）](implementation/B_TEAM_HANDOFF.md)**：规则、场景、Prompt、兜底、三个入口、A/C 联调、附件输入和未对齐事项。
- [自由对话工具执行循环与开源方案选择](implementation/B_TOOL_HARNESS_DESIGN.md)：能力目录、工具前后校验、预算、观察、停止与开关。
- [三个业务入口与自由对话的统一编排设计及执行记录（2026-10-03）](implementation/B_HYBRID_ORCHESTRATION_PLAN_2026_10_03.md)
- [混合编排验收规范与工程结果（真实模型/C/PG 待验收）](implementation/B_HYBRID_ORCHESTRATION_ACCEPTANCE_2026_10_03.md)
- [B 多轮评测集与实际 API 评测程序（62 脚本；在线全链路未通过）](../evals/b_workflow/README.md)
- [动态追问与对话兜底设计及实现](implementation/B_GUIDED_INTAKE_DESIGN_2026_10_02.md)
- [GitHub 用户侧字段逐项核查表](implementation/B_USER_FACT_FIELD_AUDIT_2026_10_02.md)
- [详细开发计划](implementation/B_AGENT_IMPLEMENTATION_PLAN_2026_10_02.md)
- [本地运行与 A/C 交接](implementation/B_AGENT_LOCAL_RUN_AND_HANDOFF.md)
- [业务流程设计](architecture/AGENT_BUSINESS_WORKFLOW_V0_1.md)
- [业务规则设计](architecture/AGENT_BUSINESS_RULES_V0_1.md)
- [KnowledgeProvider 契约](architecture/KNOWLEDGE_PROVIDER_CONTRACT_V0_1.md)
