# B：场景识别、动态追问与对话兜底

设计日期：2026-10-02；实现收尾及验证：2026-10-03。设计及本轮实现说明；工程行为标准，不是税务正确性金标。A 负责页面，B 负责本契约与编排，C 负责资料及检索。顾问只在最终复核介入。

## 1. GitHub 核查范围与发现

已 fetch GitHub 的全部两个远端分支：`Zhihong-Wu@7054c45323abf7d63d9725f03f81dab892c98110` 与 `main@8974ee78332749eda5c444823399ceca7f184fa9`。核对仓库目录、PRD、两份闭环评审、字段词典、6 条规则、8 类证据要求、10 个合成案例及自然语言样例、求值器、网页/API/模型提取入口。两个分支的字段词典、规则、证据要求、合成案例一致。

关键来源：`packages/contracts/fact_dictionary/hk_fsie_fact_fields.v0.json`、`knowledge/hong_kong/fsie/rules.json`、`knowledge/hong_kong/fsie/evidence_requirements.json`、`packages/rule_engine/evaluators.py`、`tests/fsie/candidate_cases.json`。

- 原词典 43 字段，其中 `expert_decision_status` 是系统/最终顾问字段；不能向普通用户收集。已有 B 的 `recipient_type` 补齐个人/公司入口。
- 词典的 `blocking_level`、规则的 `required_facts`、求值器真正读取的字段并不完全一致。不能把“代码能运行”当成“事实够用”。例如收入节点当前主要看 income_type，不能据此宣称来源性质已成立。
- `source_analysis`、`income_legal_character`、`hk_adequate_employees` 等包含判断。用户只能提供陈述与材料，不能通过一句“足够/免税”自动确立法律结论。
- 数据库里的法规与参考案例不能补写用户自己的交易事实。案例识别是“候选场景/资料检索范围识别”，不等于已匹配具有同样法律结果的案例。

## 2. 先识别，再按任务补充

| 层级 | 用户侧信息 | 用途与边界 |
|---|---|---|
| 入口 | 普通聊天 / 查资料 / 分析当前案件 | 普通聊天不检索；编号查询不问案件全套背景；不清楚就先问想查规则还是分析自己的情况 |
| 候选场景 | recipient_type、income_type、analysis_jurisdiction、consultation_goal | 四项分别确定谁收款、收入种类、分析哪一端/地区、解决什么问题；只收缺项。地区不从币种、语言、公司名称推断 |
| 基础适用性 | payer_jurisdiction、entity_hk_business_status、group_structure_description、income_event_status、accrual_date、payer_entity | 描述经营、集团、实际/计划与交易期间；集团结构陈述不直接推导 MNE 法律资格；别名可用，不要求真实名称或账户号 |
| 收取问题 | bank_or_account_path、receipt_date、set_off_or_clearing_arrangement、cash_pool_arrangement、payment_on_behalf_arrangement | 问实际资金路径和安排，不让用户自行判“视为在港收取” |
| 参股问题 | direct_or_indirect_holding、holding_percentage_pct、continuous_holding_period_months、investee_entity、foreign_tax_description、commercial_rationale | 只问当前路径必需项，税种是否合资格和主要目的保留最终判断 |
| 经济实质问题 | entity_activity_profile、hk_staff_description、hk_premises_description、hk_operating_expenditure_amount/currency、strategic_decision_making_location、outsourcing_and_supervision | 问员工职责、场所用途和实际活动，不问“是否已经满足充分性” |
| 仅支持材料 | 金额/币种、居民地、取得日、底层利润期、材料清单等 | 按问题或规则依赖补收，不作为所有案例的入口门槛；金额不阻断候选场景识别 |

本轮在 B 的聊天字段目录追加分析目标/地区、派息方地区、实际/计划、集团描述、员工描述、场所描述、境外缴税描述；不直接改 C 的原始事实词典或给 C 增加未约定过滤字段。B 的扩展事实随案件保存，C 接口仍使用原白名单过滤字段。

派息方具体地区、经营、集团与日期属于后续判断所需，不能作为识别候选场景的统一前置门槛。候选场景识别不等于相似裁定匹配或税务资格成立。

`identification.status` 只可为 collecting / candidate_identified / unsupported；必要字段 unknown/conflict/缺失都不能标记识别完成。用户已明确个人、非股息或非香港分析时说明能力范围；不从“香港公司”推断一定在港经营。

## 3. 追问状态机

一次最多一个主要问题，包含 `id、field、text、why、example、kind、attempt、based_on_revision`。问题文本由 B 选择，模型只负责把当前消息解析成受校验的候选事实/意图。

顺序：权限与输入 → 明确事实修订 → 本轮任务分流 → 本任务冲突 → 场景识别缺项 → 当前目标的必要事实 → 事实核对/缺口说明 → 有权限的依据 → 内部稿 → 唯一最终顾问复核。

- 已有具体值不再问；用户一次提供多项，全部保存后只问剩余一项。
- unknown 是明确“不知道”；暂时没有材料记 deferred，不改成 no。不能靠检索用户所处行业自动补成客户事实。
- 一项最多展示两次，第二次换说明方式；仍无有效回答进入选择：继续其他信息 / 先看部分整理 / 暂停。无回复不推进，不算同意。
- 不知道或无法提供时立即说明影响并给选择，不强迫连问同一字段。明确选择部分整理才保存与当前事实快照绑定的 consent；事实变化使 consent 失效。
- 部分整理只列已知事实、未知与冲突、缺口影响；不替代确认事实、执行规则或专业结论。缺事实运行研究稿须明确接受部分输出。
- 普通聊天、独立资料查询暂停当前访谈但保留 pending；返回后明确继续，或清楚地补充事实再恢复。暂停后的孤立“是/不知道”不自动绑定旧问题。
- 明确另一个案件时提示使用 A 的新对话入口，原案件不改写；本轮不自动创建跨案件任务。

## 4. 对话决策与兜底验收表

| 场景 | 触发/优先级 | 期望动作 | 兜底与检查 |
|---|---|---|---|
| 问候 + 更正 | 有明确字段更正及原文片段 | 先改指定事实、保留历史、旧报告失效 | 更正授权仅作用于所指字段；其他变化仍走冲突 |
| 新旧值不同 | 无明确更正依据 | 保存 previous/candidate，问一项 | 不覆盖；独立闲聊/资料查询不被旧冲突劫持 |
| 更正 + 查资料 | 可识别修订及查询 | 保存修订后检索 | 检索故障保留事实，返回 knowledge_unavailable，并保留待重试查询 |
| 冲突 + 查资料 | 本次事实冲突 | 先问冲突，保存 deferred_query | 解决后可恢复原查询，不能丢失用户第二个诉求 |
| 意图不明 | 不知道查规则还是分析自身 | 问一项入口问题 | 不直接套个人/公司问题；不清楚继续保留 |
| 暂时未知/无材料 | 对当前问题的明确答复 | 标未知或暂缺，展示影响及选择 | 不等于否定；无限重复被次数预算截断 |
| 目标变更 | 明确转向收取/参股/实质等 | 调整必需字段队列 | 不再问原目标不需要的字段 |
| 无依据 | C 返回 no_match | 说明查询、期间及覆盖缺口 | 不等于法规不存在，不自动补猜 |
| 来源受限/异常 | 权限、版本、哈希不通过 | 排除受限材料/主张 | 展示权限与入模权限各自检查，历史不能漏回模型 |
| 模型故障 | 调用/结构校验失败 | 技术错误，不写入候选事实 | 保留原案件，A 保留输入草稿，可重试 |
| 检索故障 | 有限安全重试仍失败 | 纯查询返回技术错误；混合任务保存事实并明确查询失败 | 不回退 Mock，不冒充 no_match |
| 主观判断 | 资格/充分性/主要目的等 | 收原始事实，列待最终判断 | 中间不新增顾问节点 |

## 5. 开发顺序与验收边界

1. 新增集中式追问策略及可审计的场景缺项计算，替换固定字段顺序。
2. 扩展模型解析契约（兼容原四字段返回）、当前问题上下文、受约束更正与对话动作。
3. LangGraph 接入持久化 dialogue / pending / deferred_query / partial_consent；保留幂等和乐观锁。
4. 给 A 返回 question/identification/dialogue 及清晰错误；原 JSON/SSE endpoints 保持。A 只需兼容不重复展示追问。
5. 合成多轮回归：未知、未回答、无材料、更正、冲突、混合请求、切换/恢复、跨案件、部分结果许可、模型/检索故障、权限与引用。构建与浏览器走查。

工程测试使用受控解析器/Mock 检索。真实模型语言理解质量、真实 C、专业规则验收仍独立进行；不会以这些测试通过宣称税务结论可靠。47 条历史规则配置仍为设计基线，本轮实现对话策略，不宣称通用 DSL 已全部执行。

## 6. 本轮落地接口与兼容方式

仍使用 A 的 `/api/cases/{id}/messages`、`/facts`、`/confirm`、`/analyze`；新增字段均在完整 Case 返回中，JSON 与 SSE done 共用同一工作流。聊天事实目录现在共 53 项，但每轮只给一个 question。字段清单与归属见 [逐项核查](B_USER_FACT_FIELD_AUDIT_2026_10_02.md)。

| 字段 | 含义 | A 的消费方式 |
|---|---|---|
| Case.identification | 候选场景状态、缺失入口字段；不表示税务资格成立 | 可以用于进度提示，不能显示“已确认免税” |
| Case.fact_gaps | 当前目标的全部未决字段及影响 | 信息面板按需展示；不把它当一轮全部问题 |
| Case.dialogue | policy_version、status、pending、attempts、deferred、deferred_query、partial_consent | 随案件持久化；A 不自行改写这些状态 |
| Message.question | id/kind/field/text/why/example/attempt/based_on_revision | 最新主要问题；choice、mode 没有 fact field |
| Message.guided | 本轮已包含完整追问/整理文案 | 不再额外显示旧的通用追问段落与字段列表，避免重复提问 |
| Message.question_fields | 旧接口兼容 | 保留字段列表；应以 question 及消息正文为准 |
| workflow.status/reason_code | 业务状态与原因 | waiting_user、paused、partial_ready、unsupported、partial_failure 等 |
| workflow.retrieval_reason_code | 回答资料问题后继续追问时保留检索结果原因 | 此时 workflow.status=waiting_user，reason_code 表示追问原因；检索结果仍保留于 research 和本字段 |
| workflow.error_code/retryable | 混合任务中的技术失败 | 显示进度已保存、检索可重试，不把整条消息标成未发送 |
| research.error | 仅错误类别和 retryable，不含连接串或原始异常 | 区分 TIMEOUT/HTTP_ERROR/INVALID_RESPONSE 等诊断 |

`partial_confirmation_required` 是业务 422：请用户在聊天中明确选择“先看部分整理”（英文精确命令 `partial summary`），然后核对事实并分析。确认事实与接受缺口是两个不同的动作。部分研究稿保存 intake_gaps、identification、partial_output_authorized；缺项时 evidence_gate=insufficient，不能通过最终批准。

C 仍只收到 `KnowledgeProvider` 已约定的请求与五类 fact_filters；B 新增的描述字段不会未经契约约定直接发给 C。独立资料查询不带客户案件事实。已知日期只有同时明确 planned/occurred 时才带 applicable_date；其余为 date_status=unknown，不能标成已核实适用版本。

## 7. 裁定研究卡暴露的建模补充

核对 `knowledge/hong_kong/fsie/ruling_research_cards.json` 的 4 张卡后，补上 `dividend_form` 与 `transaction_flow_description`。现金与非现金的后续队列不同；股份分配不伪装成银行汇款。卡片还显示企业利润税与股息预提税不能混用，当前先在 foreign_tax_description 分别保留税种/期间/材料描述，不自动推成单一合资格税率。

这些研究卡的 model_input_authorized=false 未被本轮修改；它们没有被注入产品运行时模型提示或当成用户自己的事实。B 目前也没有多实体交易图和税项逐笔计算器；文字描述用于留存材料与最终复核。

## 8. 追问示例（合成对话）

1. “香港公司收到新加坡子公司股息，想看参股条件。”→ 收取公司/股息/香港分析/参股目标/派息地区；不问金额，不从“香港公司”推断实际在港经营。
2. 下一步仅问：“收款公司是否在香港实际经营业务？”并说明注册地与实际经营不同。后续按已知信息逐项推进。
3. “不知道，暂时没有材料。”→ 保存 unknown 或 deferred，说明相关判断暂停，给继续其他信息/部分整理/暂停三个选择。
4. “先看部分整理。”→ 列现有陈述和缺口，绑定本次事实快照的许可；确认事实后可生成有缺口的研究稿，仍需最终复核。
5. “金额刚才说错了，应为 200，另查相关规定。”→ 可明确关联金额时先更新并保留历史，再检索；失败保留金额与 query，回复“重试检索”恢复。
6. “你好。”→ 正常聊天并保留待答问题；“继续案件”再恢复。暂停后的单独“是”不会被自动写成对旧问题的肯定。

## 9. 当前限制

- 这是工程政策实现，不是实时模型识别率或税务正确性验收。精确控制词和当前问题的枚举答复可直接处理；自由语言的场景、事实、更正片段仍依赖模型解析与校验，需接可用模型后用冻结对话集实测。
- 本轮追问文案以中文为主；A 的中英文界面及字段标签保留，追问/部分整理的完整英文文案仍待补齐。不会把切换 UI 语言当成会自动重译全部历史内容。
- 顾问只在最后复核。客户自述的资格、充分性、税款条件仍是候选陈述；描述补齐也不代表证据已核实。
- 只有一个当前案件、一个主要问题和一个 deferred_query。需要多笔交易并行或多个独立查询时，应另开案件或后续扩展任务队列；不会自动把不同交易合并。

## 10. 实现验收记录

- Python（2026-10-03）：`pytest -q -m 'not integration'`，199 passed / 11 integration deselected；其中动态访谈文件 42 项，包含回答后继续追问的状态一致性检查。
- 浏览器：20 个现有/新增用例均通过。首次全量出现旧文案/写死端口断言及 Chrome 启动耗时问题；修改断言后相关用例复验通过。最新访谈、冲突、部分研究稿 3 项再通过，使用独立 8011/5184 端口。
- TypeScript/Vite：`npm run build` 通过。
- 手动服务：旧合成测试数据库备份保留原 1 个案件；8001 API 已加载更新，5174 前端保留现有访问地址。
- 无真实 C、真实模型质量、PostgreSQL integration 或专业税务正确性验收。本轮合成测试不充当税务金标。
