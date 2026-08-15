# 香港境外股息 FSIE 税务分析 Agent — 设计索引

日期：2026-08-15
状态：设计已获用户确认；尚未进入 MVP 实施

## 设计决策

- 从香港开始，首个垂直场景为跨国企业实体取得境外股息；
- 直接用户为香港税务顾问，输出为内部复核稿；
- 自然语言交互采用逐步访谈，不使用固定表单作为主要入口；
- 采用混合型架构：AI 访谈和表达、确定性规则、RAG 引证、人工复核；
- 权威资料、税务规则和专家案例分别管理；
- 首版采用模块化单体、Python API、PostgreSQL、全文检索和 pgvector；
- 首个试点优先单租户隔离环境；
- 在设计和文档批准前不实施 MVP。

## 正式文档

- [产品需求文档](../../PRD.md)
- [技术路线图](../../TECHNICAL_ROADMAP.md)

## 研究参考

- [香港税务局 FSIE 专页](https://www.ird.gov.hk/eng/tax/bus_fsie.htm)
- [香港税务局 FSIE FAQ](https://www.ird.gov.hk/eng/faq/fsie.htm)
- [香港税务局 FSIE 官方示例](https://www.ird.gov.hk/eng/tax/fsie_example.htm)
- [OpenFisca Core](https://github.com/openfisca/openfisca-core)：参考规则与参数分离；因许可和产品定位不直接作为商业底座
- [LQ.AI](https://github.com/LegalQuants/lq-ai)：参考法律引用和审计设计
- [pgvector](https://github.com/pgvector/pgvector)：MVP 的 PostgreSQL 向量检索扩展
