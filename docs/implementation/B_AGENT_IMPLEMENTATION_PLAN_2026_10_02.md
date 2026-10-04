# B 模块开发计划：接入 A 前端与预留 C 检索

日期：2026-10-02。基线：`Zhihong-Wu` / `7054c45323abf7d63d9725f03f81dab892c98110`。
开发位置：独立 Git worktree `Asia-Tax-AI-Agent-B`，分支 `feat/b-agent-workflow`。
本文件先于本轮代码实现编写；完成情况见末尾执行记录，不以设计完成替代运行验收。

## 1. 目标和职责

B 交付可接 A 页面运行的 Agent 业务后端：聊天/资料查询/案件事实路由、必要追问、事实修订、检索权限、依据与引用、候选分析、最终复核状态、异常和版本管理。
A 继续负责页面和交互；B 保持现有 API/SSE 协议，仅增加展示必需的类型与模拟资料标记。C 负责语料库、检索质量和来源授权；B 负责调用 C 及解释不同返回状态。
范围沿用香港境外股息 FSIE 的 L0 研究原型。Mock 只验证业务路径，不构成真实税务依据。流程中途不引入顾问节点；用户核对自身事实不等于顾问审批。

## 2. 已有代码与缺口

| 已有 A 实现 | 本次 B 开发 |
|---|---|
| React/TypeScript/Vite 页面；FastAPI `/api` | 保留路由、认证、同源代理和 case 数据结构 |
| ChatStore JSON 案件、revision、request_id 回执 | 继续作唯一案件状态源，增加 workflow 元数据与报告快照 |
| 模型产生 chat/research/intake 路由 | 增加确定性业务控制与范围/追问结果，模型不能改系统状态 |
| research 先写检索前导语，后附原文 | 检索后构建受权限约束的答复；无依据明确说明 |
| SQL 关键词搜索 | Provider 契约、Mock、现有检索适配器、C HTTP 插槽 |
| 客户确认 facts 后运行候选规则 | 保留用户确认；检索缺口和主观事项集中放最终复核 |
| SSE 可直接透传模型 JSON 中 reply | 业务回答校验后才输出；普通/SSE 共用业务路径 |

## 3. 技术选择

- Python >=3.11、FastAPI、Pydantic v2：沿用项目，强类型验证 Provider 边界。
- LangGraph 1.x `StateGraph`：编排每轮 route → facts → retrieve → compose → validate。确定性条件边控制节点，模型仅负责语言理解/受限表达。
- 不强制引入 LangChain 高层 Agent：继续项目已有 OpenAI-compatible 模型适配器和 DeepSeek 配置习惯，不更换供应商、不在浏览器配置密钥。
- SQLAlchemy + PostgreSQL 保存案件（本地测试 SQLite）。每轮图计算无数据库写副作用，最后 ChatStore 乐观锁提交一次。等待用户通过持久化案件状态结束当前调用；新消息重新加载案件执行。
- 首版不同时引入 LangGraph checkpointer，避免案件库与 checkpoint 双份状态。进程中断未提交轮次可重跑，已提交 request_id 返回回执；不能宣称具备节点级故障续跑。后续确有长任务需求再增加持久化 checkpoint 与事务 outbox。
- HTTP JSON 接 C 最简便，MCP 可作为另一种 Provider adapter，Agent 和前端协议不因此改变。前端无需调用 MCP。
- 不新增 Redis、队列、向量库或多 Agent 自主循环。长任务、全量条文覆盖与专业评估另行推进。

官方依据：[LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) 明确可独立于 LangChain 使用；[Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) 区分图 checkpoint 与应用持久化。本次选择有界单轮图 + 现有案件存储。

## 4. 模块划分与调用链

```text
A 页面 api.stream / api.mutate
  → FastAPI 认证与输入验证
  → ChatService（owner 隔离、revision、request_id）
  → B TurnWorkflow（LangGraph，无持久化副作用）
      route → facts/scope → retrieval → answer → validation
                   ↓ waiting_user / unsupported / paused_gap
  → ChatStore 原子提交 → SSE done{case} 或 JSON Case

C 数据边界：KnowledgeProvider.search_evidence / get_evidence
  ├─ MockKnowledgeProvider：服务端指定 MOCK-01..08
  ├─ LegacyKnowledgeProvider：现有只读检索，仅展示原文
  └─ CKnowledgeProvider：受信服务端配置的 HTTP 地址，失败不会切 Mock
```

计划新增 `packages/agent/`：contracts.py、providers.py、knowledge.py、workflow.py、review.py；修改 `packages/chat/service.py`、`streaming.py`、`analysis.py` 与 `apps/api/chat.py`。保留现有规则引擎，不用大模型重写税务计算。

## 5. 业务行为与状态

| 情况 | 期望行为 | 工具/状态 |
|---|---|---|
| 普通问候/产品帮助 | 自然回复，不检索，不清空确认状态 | chat |
| 一般税务概念/查法条 | 查询资料，不强制案件访谈 | research |
| 描述/补充具体案件 | 只更新当前消息明确事实，保留版本 | intake |
| 必要背景不明 | 每轮仅一个主要问题；回答未知后不重复强问 | waiting_user |
| 新旧事实不同 | 保存候选值和旧值，要求用户澄清或编辑确认 | needs_resolution |
| 无匹配资料 | 说明无依据与缺口，不形成税务结论 | no_match / paused_gap |
| 资料仅可展示 | 原文展示，排除出所有模型上下文 | reference_only |
| 权限未知 | 默认拒绝入模和展示 | evidence_restricted |
| 时间/地区不匹配 | 不用于支持该条件，记录缺口 | evidence_insufficient |
| 范围外 | 明确目前支持范围，形成范围说明 | unsupported |
| 主观判断/规则缺失 | 候选稿记录未决事项，最后顾问复核 | pending_final_review |
| 服务失败 | 区分 model_failed / knowledge_unavailable | technical_error |

事实与对话分离：用户说不知道保留 unknown；空值表示删除，不能变成 no/0。相同事实不使报告过期；实际变更使旧分析 stale、清除事实确认和复核有效性。事实冲突不会由模型自主覆盖确认。
现有 fact dictionary 尚无个人/公司字段时，应以独立 consultation context 表示主体类型，不能把个人臆断成公司；字段变更须同步字段目录与页面兼容性。

## 6. 与 A 的接口契约

继续使用：POST `/api/cases/{id}/messages`，`{text,data_approved,revision,request_id}`。
JSON 返回完整 Case；SSE 返回 `delta{text}`、`done{case}` 或 `error{code}`。首版税务回复可只发送校验后 delta+done，保证不流出未校验结论。
继续使用 facts PATCH、confirm POST、analyze POST。`confirm` 是用户核对事实；所有分析保持 `review_required`，不得由聊天批准。
新增字段只增不删：message.workflow（status、reason_code、trace、timings）、research.provider/is_synthetic/reason_code、answer（summary、conditions、claims/citations、limitations、review_status）。旧页面仍显示 text/passages。
检索页 GET `/api/knowledge/search` 和分析接口也走同一 Provider，避免只接聊天而旁路仍直接连 C 数据库。
错误沿用 A 已有小写 code，业务无匹配用正常回复，不伪装成网络错误。revision_conflict 让 A 刷新；重试沿用同一 request_id。
最终复核先提供后台 service + API 契约，审批身份必须由服务端授权，普通账号不能请求自封顾问。无顾问配置保持待复核。A 后续实现按钮/审核页。

## 7. C 插槽与授权

完整契约见 `../architecture/KNOWLEDGE_PROVIDER_CONTRACT_V0_1.md`。
请求包含 query/intent、法域/主题、适用日期、必要事实筛选、request_id/trace_id/limit/deadline。owner/权限来自服务端 trusted_context，不接受前端伪造。
响应区分 ok/partial/no_match/error，包含 corpus_version、coverage、evidence、timings。每份证据包含版本/定位/hash、model_use/display_use、policy_version；get_evidence 按精确版本读，不回退最新版本。
Mock 由服务端配置选择，不允许用户文本切换场景。8 组 fixtures 作为契约测试输入。C HTTP 适配器配置缺失应显式报错；真实 C 未接入不能写成联调成功。
允许入模文本单独构建白名单投影；display 原文、内部元数据不能把整个 search_response 序列化进 prompt。历史研究消息也不把仅展示文本带回模型。
资料有权入模但无权展示时首版禁止生成可向用户披露该内容的摘要，等待 C 明确衍生内容授权，防止通过摘要绕过展示许可。
外部文本视作数据，不能更改系统提示词、调用权限或业务规则。

## 8. 回答和分析边界

检索回答包含：回答重点、适用条件、对应引用、缺口和待复核标记。引用必须存在于本次允许使用的证据，hash/版本匹配；校验失败输出缺口说明，不保留失败草稿。
首版可用可验证的摘录组织回答；不把生成式长篇推理当作已验证税务意见。范围、日期和资料授权不满足时停止相关结论。
候选规则引擎继续生成内部分析，新增证据覆盖门控/节点状态、缺口列表、合成标记。现有少量规则不能宣称完成整个税务判断链。既有 human gate 表述映射为最终复核任务，不触发中途人工工具。
最终复核针对固定报告 hash + facts/rules/source 版本；事实变化后旧审批失效。批准、退回修订、不能确认都留审计信息。Mock 分析禁止正式批准。

## 9. 性能、失败与一致性

- 每轮最多一次路由模型调用，最多两次检索（只对明确可重试故障重试一次）；禁止 no_match 自动反复搜索。
- 3 秒检索总预算，HTTP 调用显式 timeout；模型现有45秒上限，整轮90秒。未知异常只返回安全错误码。
- 历史最多12条、单条4000字；引用最多7个，模型文本有限预算。
- 每节点耗时、检索次数、provider/corpus_version、trace_id 记录进 workflow；不记录凭据/完整 prompt。
- LangGraph 每轮有固定节点/递归上限，无无限反思循环。
- 提交前检查 SSE 断连；计算无持久化副作用。已到数据库提交边界的请求即使断连也可能成功，重新 GET 案件/retry request_id 确认，不能承诺取消能撤销事务。
- 乐观锁避免并发污染；相同请求可能并发重复计算，但只能一次提交，后续调用返回同一结果。需要降低重复模型费用时再引入请求租约。

## 10. 开发顺序与验收

| 阶段 | 产物 | 验收 |
|---|---|---|
| P0 计划/基线 | 本计划、独立 worktree、复制既有设计 | 未覆盖原工作区修改 |
| P1 Provider | 类型、Mock8状态、legacy/C适配、权限投影 | 未授权原文不出现在模型输入；无静默 fallback |
| P2 单轮编排 | LangGraph、事实/追问/检索/回答状态 | 闲聊不查库，unknown不重复问，矛盾不覆盖 |
| P3 A接入 | 普通/SSE统一服务、检索页/分析共用provider | 页面协议兼容、幂等、错误和取消语义 |
| P4 最终复核 | 报告hash、待复核/退回/批准、服务端权限 | 普通用户不能批准、旧版本不能批准、Mock不能批准 |
| P5 回归 | 单元/API/SSE/页面类型构建；可行时浏览器 | 无真实模型/真实C依赖的可复现本地验收 |

必须覆盖：8 mock场景、错误重试次数、权限未知/单向许可、日期失配、引用伪造、查无资料、无匹配≠超时、版本精确读取、跨用户隔离、事实更新失效、单轮一个问题、revision冲突、相同request_id、JSON/SSE一致、最终复核权限与hash。
不把类型校验当作内容正确性评估；真实模型路由准确率、C召回/资料完整性、真实前端登录环境、顾问专业审校仍需要对应集成环境验收。

## 11. 后续扩展条件

C 就绪时共同确认字段/权限/版本/coverage语义，用同一契约测试跑真实接口，再开放 c 模式；不靠替换连接串假定接入完毕。
后续若扩展多个争点和长任务：增加节点依赖调度与 checkpoint/outbox、异步任务取消、法律变更触发。现有业务规则 JSON 是评审基线，本轮应明确哪些规则已由代码实现，不能声称47条都已执行。

## 12. 执行记录

- 计划已写入，代码实现开始前未执行任何线上业务写入。
- 下方由开发结果补充：实现范围、命令/测试结果、未完成及外部依赖。


### 2026-10-02 实施结果

P0–P5 的本地 L0 实现与验证已完成：新增 LangGraph 单轮图、Pydantic Provider 契约、Mock8场景、旧检索适配、C HTTP适配器、权限/日期/hash边界、请求与版本保持、最终复核服务/API；接到 A 的原有 JSON/SSE、检索页和分析入口。前端只做数据标记、字段和复核状态的必要适配。

落地调整：

1. 首版证据回答采用摘录组织，不调用第二次模型进行自由总结；可保证引用来自返回证据，不能代替专业内容评估。
2. LangGraph 持久化使用既有 ChatStore 的轮次结果，不使用内存 checkpoint 冒充故障续跑。
3. 最终复核受服务端 UUID 白名单及案件 owner 双重约束；未新增跨账号分配/审核页面，该项由 A 后续接入。
4. 检索服务默认 legacy 保持 A 兼容；开发者明确配置 mock 使用模拟场景。C 模式只使用 C，不失败降级 Mock。
5. 已知业务规则47条配置未整体接入通用解释器；本轮以显式代码实现当前咨询路径，未来多争点/长期任务调度列为扩展。
6. 普通对话和研究路径均经同一图；SSE只发送校验后 done，页面原有加载/停止逻辑可继续使用。后续优化首字延迟应保持同样的输出校验边界。

验收结果：Python 157 passed / 11 integration deselected；A 页面 Playwright 19 passed；TypeScript+Vite build通过；git diff --check通过。未做真实C、真实模型、真实PostgreSQL或专业税务正确性验收。详见[本地运行与交接](B_AGENT_LOCAL_RUN_AND_HANDOFF.md)。

### 2026-10-02 至 2026-10-03 动态追问及兜底细化结果

新增集中式 `guided-intake-0.2`：入口四项识别、按咨询目标的字段队列、一次一问及说明/示例、两次未答后的选择、unknown/deferred、暂停恢复、字段级更正与冲突历史、混合任务事实保存及检索恢复、部分输出许可与事实版本绑定。核对 GitHub 两分支的原字段/规则/案例与四张裁定卡，追加非现金股息与税项描述分支。文档：[设计及接口](B_GUIDED_INTAKE_DESIGN_2026_10_02.md)、[53 项字段归属核查](B_USER_FACT_FIELD_AUDIT_2026_10_02.md)。

最终验证：Python 199 passed / 11 integration deselected；新增动态访谈测试文件 42 项通过，含回答后继续追问的业务/检索状态一致性检查。20 个浏览器用例均已通过，包含修订旧断言后的针对性复验；最新访谈/冲突/部分稿 3 项再次通过。TypeScript + Vite 构建通过。保留当前合成测试案件并将 8001 手动 API 重启到新代码；5174 页面继续使用。

仍需真实模型路由与抽取评测、C 检索契约/质量/时效、PostgreSQL 和专业规则验收。自由语言更正识别保守兜底；追问完整英文文案、多实体交易图、多查询任务队列属于后续能力，不作为本轮已完成部分。

### 2026-10-03 固定入口与动态调度（首版工程完成）

新计划及执行记录：[三个业务入口与自由对话的统一编排](B_HYBRID_ORCHESTRATION_PLAN_2026_10_03.md)；[54 项验收矩阵及工程记录](B_HYBRID_ORCHESTRATION_ACCEPTANCE_2026_10_03.md)。已复用现有五类意图、字段目录、追问和兜底，接入入口/任务状态、共用子图、有限动态规划、统一分析准入与 A 页面。新增 54 个混合编排及 3 个传输期限测试，完整后端 256 项、页面 25 项、TypeScript/Vite 构建通过。真实模型、C 和 PG 待验收；代码未提交/推送，当前手动页面只用合成模型边界。
