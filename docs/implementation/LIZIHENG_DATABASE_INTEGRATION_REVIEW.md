# LiZiheng 数据结构与 B Agent 接入评审

核查日期：2026-10-07。分支：`LiZiheng`；快照：`b09cf7fe283ea277290769ba5b056a5d91b34095`。

## 核查范围

已读取远端文件树、official/README.md、STATUS.md、tools/build.py、tools/query.py、参数和表单 CSV 表头。原有 PostgreSQL 模型、迁移和入库代码通过远端文件树的 Git blob SHA 与本地 Git 对象逐一对应读取，内容与该分支完全相同。未连接部署中的数据库，未执行 SQLite 文件查询或全量内容质量验收；STATUS 的数量是分支生成报告的记录。

## 1. 两套存储

### 官方知识库：official/official.sqlite

CSV 是构建输入；SQLite 是生成的查询产物。README 指定范围 CN/HK/SG、公司主体，保留现行内容，不含案例事实或标准答案。

| 表 | 关键字段 | 用途 |
|---|---|---|
| doc | id, jur, type, title, issuer, url, sha256, retrieved_at, effective_from, effective_to, validity_label, currency, alias_of | 原件元数据及来源追溯 |
| clause | cite_id, doc_id, kind, label, parent, chars, text | 可引用条款片段 |
| param | param_id, scope, income, topic, name, value, unit, cite_id, effective_from, effective_to, quote, status | 税率、门槛、期限等候选参数 |
| form_field | form_id, seq, section, label, maps_to, kind, note | 官方表单与业务字段映射 |

逻辑关联：clause.doc_id -> doc.id；param.cite_id -> clause.cite_id；form_field.form_id -> doc.id。
构建脚本全部建为 TEXT，无显式主键、外键、唯一约束或查询索引。需在适配层做类型、去重、引用完整性检查。不能将 extracted 参数当成已专业核验。

STATUS 记录 220 份入库文件（含 40 个分片原件）、6331 个条款片、132 项参数、256 个表单字段映射；这些不是案例数量或本轮实测数量。

查询能力：source(cite_id) 精确条款查询；cell(scope,income,topic,on) 参数查询；doc(doc_id) 文档元数据；find(text,doc_id,limit) 子串查询。未实现自然语言语义检索或召回覆盖评估。

### 原有 PostgreSQL 业务模型

PostgreSQL 16 / SQLAlchemy / Alembic；容器提供 pgvector，迁移启用 vector 扩展，但模型未定义向量字段或相似度检索。

- 知识定义：rule_sets、rule_nodes、evaluation_cases。
- 业务运行：organizations、cases、facts、fact_versions、rule_executions。
- 评测：evaluation_runs、evaluation_results。
- 审计与配置：audit_events、system_settings。
- 原有资料管线：sources、legal_units。

evaluation_cases 强制 synthetic=true，是合成评测案例，不能充当真实裁定或客户案件依据。官方库与原有 sources/legal_units 未见自动同步管线。

## 2. 接入现状与缺口

1. B 当前 LegacyKnowledgeProvider 查询 PostgreSQL 的 sources/legal_units；改连接字符串无法查询 SQLite 的 doc/clause。
2. B 已有 CKnowledgeProvider HTTP 客户端，但此分支 apps/api/main.py 仅提供 health，未实现契约所需 POST /search、POST /evidence。
3. SQLite 无 model_use/display_use/policy_version，必须另建经双方确认的权限策略，不能以官方来源自动授予模型权限。
4. 仅维护现行资料，不能声称支持任意历史案件。查询早于生效日期或缺少日期依据时须标记不足；空日期不是已确认适用。
5. build.py 删除旧 SQLite 后重建，在线读库需要原子发布和不可变版本快照。PostgreSQL 管线也会替换旧 LegalUnit；哈希不等于可回读的历史版本。
6. 参数源脚本有 Windows 绝对 ROOT，构建脚本的 LibreOffice 路径亦针对 Windows；跨平台生成须改配置。直接读取已构建 SQLite 不依赖这些转换工具。
7. 原有初始迁移用当前 metadata.create_all，后续迁移又显式建 sources/legal_units、system_settings，存在全新初始化重复建表风险，接入前应在空库验证并修复。
8. health 返回 database_url，部署前应移除可能含凭据的信息。

## 3. 推荐接入路径

先实现 B 内只读 OfficialKnowledgeProvider 适配 SQLite，复用 KnowledgeProvider 业务边界；独立部署时让 C 提供同契约 HTTP 服务，B 使用现有 CKnowledgeProvider。首次接入无需 MCP。

```text
A 页面 -> B 意图/追问/事实处理 -> LangGraph / Harness
 -> KnowledgeProvider -> OfficialKnowledgeProvider（建议新增）
 -> official.sqlite（doc / clause）
 -> 权限、版本、日期和引用校验 -> 内部稿 -> 最终顾问复核
```

建议映射：evidence_id/unit_id=clause.cite_id；source_id=doc.id；title/url/publisher=doc.title/url/issuer；content_hash=实际返回文本 UTF-8 SHA256。source_version_id 必须绑定已发布知识库快照及文档内容，不可使用会变化的行号。manifest 文档 sha256 是原件哈希，不能当条款文本哈希。topic 与适用期须按任务和已核对资料确定，不可将全库统一标成 dividend/HK。

权限未知时保持 unknown，B 继续默认不放行。coverage 首期用 unchecked/partial；不能把检索命中或库内数量当成依据足够。

股息路径可继续使用当前 Agent；扩展 CN/SG、利息或转让，需要同时扩展 B 的场景识别、事实字典、规则、工具准入和评测。不得只按 C 的数据覆盖扩大咨询承诺。

param 查询与 form_field 查询建议作为独立的受控工具；当前通用证据检索契约不能替代完整参数执行契约。先保留查询来源，不自动选择税率。案例搜索只接明确存在的真实案例来源，evaluation_cases 永不混入真实依据检索。

## 4. 分阶段推进

1. C 确认知识库发布版本、路径/服务地址、覆盖日期、权限、参数审核状态、真实案例范围。
2. B 完成只读适配：先精确 cite_id，再受控关键词查询；通过 doc JOIN 补齐来源。指定旧引用不可用时返回 version_unavailable。
3. 保留 B chat_cases 案件状态存储，首期不双写 C 的 cases/facts；若未来统一存储，再定义 UUID/整数 ID、owner/organization_id、事实确认状态和版本映射。
4. 检索通路通过后，单独实现参数类型/单位/期间/条件校验及参数工具；以经核验规则驱动计算。
5. A 联调真实页面，检查引用点击、未获准文本、无匹配、服务失败和最终复核状态。
6. 测试精确条款、法规与指引、旧引用失效、日期不足、权限未知、参数条件缺失、案例不支持、数据库不可用；再运行真实模型多轮冒烟。真实依据连通不等于专业税务结论通过验收。

## 源码入口

- https://github.com/ZhihongWu-dev/Asia-Tax-AI-Agent/blob/b09cf7fe283ea277290769ba5b056a5d91b34095/official/README.md
- https://github.com/ZhihongWu-dev/Asia-Tax-AI-Agent/blob/b09cf7fe283ea277290769ba5b056a5d91b34095/official/tools/build.py
- https://github.com/ZhihongWu-dev/Asia-Tax-AI-Agent/blob/b09cf7fe283ea277290769ba5b056a5d91b34095/official/tools/query.py
- https://github.com/ZhihongWu-dev/Asia-Tax-AI-Agent/blob/b09cf7fe283ea277290769ba5b056a5d91b34095/packages/persistence/models.py
- https://github.com/ZhihongWu-dev/Asia-Tax-AI-Agent/blob/b09cf7fe283ea277290769ba5b056a5d91b34095/apps/api/main.py
