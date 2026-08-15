# 东亚税务 AI 平台（香港 FSIE MVP）— 设计索引

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
- 当前无香港税务专家不阻止研究原型开发，但所有候选规则和案例必须标记为未验证；
- 香港税务专家验证核心规则、判断边界和金标案例，是进入封闭顾问试点的强制门槛；
- 2026 年项目范围限定为中国内地、香港、日本和韩国，香港为深度 MVP，其他三个地区为标准企业税务包；
- 其他亚太地区推迟至东亚 Release 1 验收后规划；
- 在设计和文档批准前不实施 MVP。

## 正式文档

- [产品需求文档](../../PRD.md)
- [技术路线图](../../TECHNICAL_ROADMAP.md)
- [2026 项目计划](../../PROJECT_PLAN_2026.md)

## 研究参考

- [香港税务局 FSIE 专页](https://www.ird.gov.hk/eng/tax/bus_fsie.htm)
- [香港税务局 FSIE FAQ](https://www.ird.gov.hk/eng/faq/fsie.htm)
- [香港税务局 FSIE 官方示例](https://www.ird.gov.hk/eng/tax/fsie_example.htm)
- [OpenFisca Core](https://github.com/openfisca/openfisca-core)：参考规则与参数分离；因许可和产品定位不直接作为商业底座
- [LQ.AI](https://github.com/LegalQuants/lq-ai)：参考法律引用和审计设计
- [pgvector](https://github.com/pgvector/pgvector)：MVP 的 PostgreSQL 向量检索扩展
