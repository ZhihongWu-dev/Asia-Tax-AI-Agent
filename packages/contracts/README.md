# FSIE 数据契约（Data Contract）

| 项目 | 内容 |
|---|---|
| 版本 | v0.1（契约首版） |
| 日期 | 2026-09-01 |
| 适用 | L0 香港境外股息纵向切片；四地区共用同一契约结构 |
| 状态 | 候选契约；专业语义仍 `unverified`，但结构与命名现在起强制一致 |
| 关联 | [数据提取与校验计划](../../docs/implementation/FSIE_DATA_EXTRACTION_VALIDATION_PLAN.md) · [数据集与来源说明](../../docs/architecture/DATA_SOURCES_AND_DATASETS.md) · [技术路线图](../../docs/architecture/TECHNICAL_ROADMAP.md) |

## 1. 为什么先有契约

契约是数据库表、规则引擎、事实卡、案例、API 的**共同上游**。在写应用和建表之前先固定"有哪些对象、每个对象有哪些字段、字段取什么值、状态往哪流转"，可以避免边写边改表、跨文件字段名对不齐。它对应数据计划的 **Iteration 1：契约与清单**。

契约只规定**结构与取值**，不规定税务结论；所有专业语义在 L0 一律保持 `unverified`。

## 2. 三件套与各自职责

| 组成 | 位置 | 职责 | 谁消费 |
|---|---|---|---|
| 共享枚举/公共结构 | `json_schemas/definitions.schema.json` | 状态机、节点 key、值域的**权威来源** | 所有 Schema、文档 |
| 资产 JSON Schema（7 份） | `json_schemas/*.schema.json` | SourceRecord / LegalUnit / RuleNode / EvidenceRequirement / FactRecord / FactField / CandidateCase 的结构 | IDE、后端模型、校验 |
| Python 枚举 | `enums.py` | 与 definitions 一一对应的代码常量，消灭魔法字符串 | 后端、迁移、脚本 |
| 事实字段字典（DS-03） | `fact_dictionary/hk_fsie_fact_fields.v0.json` | 全系统统一的事实字段、类型、单位、阻断级别、关联节点、证据 | 规则、事实卡、案例、建表 |

`definitions.schema.json` 与 `enums.py` **必须一致**；`scripts/validate_fsie_package.py` 会交叉比对，漂移即失败。

## 3. 固定下来的状态机（不要混用）

系统里有多套独立状态，各管一层：

| 状态机 | 取值 | 用在 |
|---|---|---|
| 资产生命周期 | discovered→captured→parsed→candidate→machine_checked→human_review→verified→active；任意阶段可 rejected/stale/potentially_stale/blocked | 来源、法律单元、规则等知识资产 |
| 专业验证状态 | unverified / verified / rejected | 来源、规则；只有香港税务专家可置 verified |
| 事实确认状态 | client_statement / ai_candidate / advisor_confirmed / externally_evidenced / assumed / unknown / conflict | 运行时每条事实；LLM 只能写 ai_candidate |
| 规则节点输出 | satisfied / not_satisfied / unknown / conflict / condition_not_demonstrated / human_review_required | 单个规则节点执行结果 |
| 案件终态 | research_only_output / stop_and_escalate / human_review_required | 聚合所有节点后在人工门控得出 |
| 证据状态 | provided / missing / conflict / not_applicable | 证据条目 |
| 案件流程状态 | draft/interviewing/waiting_*/analyzing/needs_human_judgment/pending_review/approved/invalidated/archived | 案件生命周期（PRD 第 9 节） |
| 阻断级别 | scope_blocking / conclusion_blocking / supporting | 事实字段：阻断范围、阻断结论或仅补充 |

**铁律：缺事实只能得到 unknown / condition_not_demonstrated，绝不映射成 not_satisfied（否定）。**

### 3.1 两个容易混的设计决策

1. **事实的值与确认状态分离。** 运行时 `FactRecord` 的 `value` 只放纯业务值，"这条事实是谁确认的"放 `confirmation_status`。因此取值里不再有 `candidate_yes` 这种把状态揉进值的写法；候选案例的内联 `facts` 只写业务值或哨兵值 `unknown/conflict/assumed/not_applicable`，载入事实卡时再统一附 `ai_candidate` 状态。
2. **节点输出 ≠ 案件终态。** 单节点只输出 NodeOutputStatus；`research_only_output` 等案件终态是人工门控聚合全部节点后的结果，不写进单节点 outputs。

## 4. 命名规范

- 一律 `snake_case`；
- 百分比后缀 `_pct`，取值 0–100；期间后缀 `_months`（整数月），时点用 `_date`；
- 金额用 `_amount` 数值字段 + 配对的 `_currency`（ISO 4217）字段；
- 不确定的判断不用裸布尔，用受控枚举（才能表达 unknown/conflict）；
- 证据类型取自字段字典 `controlled_evidence_types` 的 26 个受控词，不得新造别名。

本次契约已消除的历史不一致：`holding_percentage`→`holding_percentage_pct`、`continuous_holding_period`→`continuous_holding_period_months`、`receipt_account`→`bank_or_account_path`、经济实质聚合名拆成 `hk_adequate_employees/hk_adequate_premises/...` 细字段、blocker 由自由文本改为引用真实字段名。

## 5. 判断链节点标准键（PRD 5.2 十步 + 人工门控）

| ordinal | node key | IRO 依据（已核对） |
|---|---|---|
| 1 | scope | s.15H |
| 2 | income_characterisation | s.15H/s.15I |
| 3 | receipt | s.15I |
| 4 | financial_entity_exclusion | s.15H/s.15I（L0 暂未建规则，已预留） |
| 5 | economic_substance | s.15K |
| 6 | participation_basic | s.15M（门槛 5%/12 月见 s.15M(2)） |
| 7 | foreign_tax_switchover | s.15N(2)(5)，参考税率 15% 见 s.15N(7) |
| 8 | anti_hybrid | s.15N(3)（L0 暂未建规则，已预留） |
| 9 | main_purpose | s.15N(4)（L0 暂未建规则，已预留） |
| 10 | compliance_filing | s.15J/s.15S（L0 暂未建规则，已预留） |
| 0 | human_gate | 横切门控，非顺序步骤 |

规则的 `ordinal` 必须与本表一致，校验会强制。当前规则库实现了 6 个节点（1/2/3/5/6 + 门控），缺的 4 个节点契约已预留，补全是下一步、不在本次契约范围。

## 6. 事实字段字典（DS-03）

`fact_dictionary/hk_fsie_fact_fields.v0.json` 按 PRD FR-03 八大事实域定义了 **43 个字段**与 **26 类受控证据**。每字段含：域、类型、单位、枚举、阻断级别、关联节点、所需证据、是否第一刀纵切必需（`l0_first_slice`）、法条定位、中文说明。

- `l0_first_slice=true` 的字段约 22 个，是 walking skeleton 第一刀真正要落库和走通的；其余字段为补全 10 节点预留，避免回头改字典。
- 新增字段必须改字典并通过校验，规则、案例、API、表结构只能引用字典里的字段。

## 7. 怎么消费这份契约

- **后端模型**：以 JSON Schema 为准生成 pydantic 模型（或手写并保持一致）；业务代码一律 `from packages.contracts.enums import ...`，不写裸字符串。
- **数据库迁移（下一步）**：契约字段 → 表的映射方向——
  - `SourceRecord`→`legal_sources`，`LegalUnit`→`legal_passages`（全文 + 后续向量列）；
  - `RuleNode`→`rule_sets/rule_nodes`（规则定义仍以 Git 版本为准，库里存发布记录与 `rule_executions`）；
  - `FactRecord`→`facts/fact_versions`（值与确认状态分列，天然支持版本历史）；
  - `CandidateCase`→`evaluation_cases`，运行结果→`evaluation_runs/results`；
  - 字段字典的枚举→数据库 CHECK 约束或查找表；每张业务表第一天带 `organization_id`。
- **校验**：`python3 scripts/validate_fsie_package.py` 同时做包安全检查与跨文件契约一致性检查（字段、证据、节点、枚举、blocker、枚举漂移）。
- **IDE**：在支持 JSON Schema 的编辑器里把各 JSON 关联到对应 schema，可获得字段补全与即时报错。

## 8. v0 范围与未做项

**本次做到**：枚举/状态机、7 份资产 Schema、43 字段字典、Python 枚举、零依赖跨文件校验，并把现有 rules/evidence/cases 三个知识包对齐到契约（校验通过）。

**明确未做（留给后续步骤）**：
1. 补全 4 个缺失规则节点（4/8/9/10）——属规则补全，不是契约；
2. LegalUnit 实例切分（Schema 已就绪，待来源管线产出）；规则候选阈值的 `source_unit_id` 待切分后回填；
3. 数据库表与迁移、后端 pydantic 模型（契约是其输入，本目录不建表）；
4. JSON Schema 的通用结构校验器（当前用零依赖的针对性跨文件检查；后端接入 pydantic 后做完整结构校验）。

## 9. 变更流程

契约是共享上游，改动需谨慎：改枚举/字段 → 同步 `definitions.schema.json` 与 `enums.py` → 同步受影响知识包 → 跑校验到通过 → 在本说明记录版本变化。任何让 `validate_fsie_package.py` 变红的提交不得合入。
