# Asia Tax AI Agent

面向企业税务研究与顾问复核场景的东亚税务 AI 平台项目。项目以中国香港境外来源收入豁免征税机制（FSIE）为深度 MVP，并为中国内地、日本和韩国建立可扩展的官方资料与规则框架。

本仓库已完成 L0 内部研究原型工程验收（见 [L0 验收记录](docs/project/L0_ACCEPTANCE_RECORD.md)），尚不提供正式税务意见，也不是可供客户直接使用的产品；进入 L1 须先通过香港税务专家验证与安全门槛。

## 当前交付边界

- **L0 内部研究原型**：2026 年默认目标，只能用于受控研究和工程验证；
- **L1 封闭顾问试点**：必须通过香港税务专家验证、安全和运营门槛；
- **L2 正式客户能力**：不属于 2026 年默认范围。

香港是当前唯一的深度 MVP。中国内地、日本和韩国在保守资源基线下先交付 `source-catalog baseline`，额外工程与知识运营资源到位后再扩展为标准研究包。

## 核心文档

- [产品需求文档](docs/product/PRD.md)
- [技术路线图](docs/architecture/TECHNICAL_ROADMAP.md)
- [2026 项目计划](docs/project/PROJECT_PLAN_2026.md)
- [批判性文档审查报告](docs/reviews/2026-08-15-prd-roadmap-project-plan-plain-language-review.md)
- [文档导航](docs/README.md)

## 仓库结构

| 目录 | 当前用途 |
|---|---|
| `docs/` | 产品、架构、项目计划、审查和设计记录 |
| `apps/` | FastAPI 应用入口与健康检查 |
| `packages/` | 数据契约、事实提取、知识处理、规则执行、持久化和报告模块 |
| `knowledge/` | 可公开并允许版本管理的资料清单、标注定义和规则元数据 |
| `tests/` | 离线单元测试、数据库集成测试和虚构案例评测资料 |
| `scripts/` | 知识包校验与裁定来源内容检查脚本 |
| `infrastructure/` | 本地 PostgreSQL / pgvector 的 Docker Compose 配置 |
| `alembic/` | 数据库版本迁移 |

主分支已包含 L0 后端研究原型。Web 演示及其分析 API 仍在 `demo/hk-web` 分支，尚未整体合并。开发命令见 `Makefile`；其中虚拟环境路径及 Shell 命令按 Linux / WSL 编写。

## 知识与数据安全

- 首版专业资料应优先使用可验证的官方来源；
- RAG 资料、确定性规则和案例评测必须分别管理；
- 不得提交客户案件、个人资料、密钥、`.env` 或受限原始资料；
- `knowledge/` 只保存获准版本管理的清单、元数据、标注规范和规则定义；
- 系统输出必须保留来源、规则版本和适用时间，且最终专业判断由合资格人员负责。

## 项目背景

本项目最初作为 TUM Project Study 开展，后续目标是在受控验证基础上逐步扩展为东亚税务研究与顾问辅助平台。
