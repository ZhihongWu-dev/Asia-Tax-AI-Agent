# B Agent：本地运行与 A/C 交接

最新统一入口：[2026-10-04 队友交接与迭代清单](B_TEAM_HANDOFF.md)。本文件各日期小节保留当时的历史结果；2026-10-04 已进行真实免费模型测试，但完整连续链路未通过，不能再将“尚未调用模型”作为当前结论。

初版日期 2026-10-02；最新混合编排交接日期 2026-10-03（第 9 节）。代码位于 `feat/b-agent-workflow`，基于 A 的 `7054c45`。
本次是可运行的 L0 开发版本。现有页面无需重写，C 未接入时可通过 Mock 验证业务路径。

## 1. 开发环境

在 `Asia-Tax-AI-Agent-B` 根目录执行：

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-b-agent.lock
.venv/bin/pip install --no-deps -e .
cd apps/web
npm ci
```

已验证环境：Python 3.12、Node 22.13.1、LangGraph 1.2.12。锁文件记录此次 Python 测试环境；前端使用 A 原有 package-lock.json。

## 2. 连接已有登录与模型环境

`config/agent.env.example` 只包含新配置样例，不包含真实凭据。将需要的配置合并到本地私有 `.env`，保留现有 A 的 `FSIE_AUTH_*`、`FSIE_MODEL_*`；不要覆盖已有凭据。

```text
FSIE_AGENT_PROVIDER=mock
FSIE_AGENT_MOCK_SCENARIO=MOCK-01
FSIE_WEB_DATABASE_URL=sqlite:///data/chat_cases.sqlite
FSIE_AGENT_REVIEWER_IDS=[]
```

启动 API（仓库根目录）：

```sh
.venv/bin/python -m uvicorn apps.api.main:app --host 127.0.0.1 --port 8000
```

另开终端，在 `apps/web` 运行 `npm run dev`，页面 `http://127.0.0.1:5173`，Vite 同源代理 `/api` 到后端。正式前端仍需 A 的登录配置，路由理解仍需项目原有模型配置。本轮没有读取/复制私有 `.env`，也没有向真实模型发送数据。

Provider 默认是 legacy，保留 A 当前只读资料搜索；明确设为 mock 才使用模拟资料，配置变更后重启 API。Mock 不能由网页参数或用户话语切换。

## 3. 不需要 C、模型或登录服务的本地联调

以下测试启动器只用于本机测试，使用合成身份和模型输出；不要用于部署：

```sh
# 仓库根目录，终端1
.venv/bin/python tests/chat/serve_browser.py

# apps/web，终端2
FSIE_WEB_API_URL=http://127.0.0.1:8001 npm run dev -- --port 5174
```

浏览器打开 `http://127.0.0.1:5174`。可输入 `你好`、`Synthetic foreign dividend case`、`FOLLOW_UP`、`CONFLICT_TEST`、`Case 68`；模型边界为测试替身，API、存储、LangGraph、事实规则和页面是真实代码。Mock8场景通过下节 API/单元测试验证。

## 4. 可复现验收

```sh
# 根目录
.venv/bin/python -m pytest -q -m 'not integration'

# apps/web
npm run build
# FSIE_TEST_PYTHON 需填上述虚拟环境 Python 的绝对路径；Chrome 已安装时使用 channel=chrome。
PLAYWRIGHT_CHANNEL=chrome FSIE_TEST_PYTHON=/absolute/path/to/.venv/bin/python npm test -- --workers=2
```

历史结果（2026-10-03 动态追问迭代）：199 项 Python 测试通过，11 项真实 PostgreSQL integration 测试未运行；20 个 Playwright 页面用例均已通过（全量回归后对文案/端口断言和一次 Chrome 启动超时进行针对性复验，最新追问/冲突/部分稿 3 项再通过）；TypeScript + Vite 构建通过。首版记录为 157 / 19，最新混合编排结果为 256 / 25，见第 9 节。模型、登录、检索的外部网络边界由替身隔离；这些结果不表示真实 C 或真实模型质量已经验收。

## 5. A 的接入点

现有 `api.ts`、`useWorkspace.ts` 的请求协议保留。新增字段为兼容扩展：

| 数据 | 新字段 | 用途 |
|---|---|---|
| Case / Message | workflow.status/reason_code/trace/timings_ms | 业务状态与节点耗时 |
| Case | fact_conflicts | 冲突旧值和新候选值 |
| Message | answer.summary/conditions/claims/limitations/review_status | 结构化组织回答 |
| research / Passage | provider、is_synthetic、版本、权限摘要 | 明确模拟与真实资料 |
| Analysis | report_hash、review、evidence_gate、节点 workflow_status | 最终复核与版本固定 |

首版研究回复采用确定性摘录和条件/缺口模板。被引用文本必须来自授权资料且匹配哈希；没有接第二次自由生成式总结调用。普通对话仍由原模型产生。SSE 首版只发送业务校验及提交后的 `done{case}`，原页面已支持；等待时显示现有加载/停止按钮。
聊天字段目录现有 53 项：原词典中 42 个可编辑候选字段，加 11 个 B 的主体/目标/地区/实际计划及原始描述字段；不改变 C 的原始词典和过滤契约。候选场景识别先收主体、收入类型、分析地区、咨询目标四项，再按任务补必要描述。已知字段不重复追问，一次一个主要问题。明确更正保存新版本；没有明确更正的数值变化保留冲突，用户可澄清或在事实面板修订。详见 [动态追问规范](B_GUIDED_INTAKE_DESIGN_2026_10_02.md) 与 [逐项字段核查](B_USER_FACT_FIELD_AUDIT_2026_10_02.md)。

新增 Case.identification/fact_gaps/dialogue、Message.question/guided。A 对 guided 消息不再重复显示旧通用问题；部分研究稿显示 intake_gaps。缺项且未明确选择部分稿时，analyze 返回 422 partial_confirmation_required；可以在聊天中输入“先看部分整理”或英文 `partial summary`，再核对事实并分析。资料独立查询不要求补完案件，也不继承旧案件过滤。

最终复核 API：

```text
POST /api/cases/{case_id}/analyses/{report_id}/review
{revision, request_id, report_hash, decision, note}
decision: approved | changes_requested | unable_to_conclude
```

身份来自认证，不读取 body 中的角色。只有服务端 `FSIE_AGENT_REVIEWER_IDS` 列出的 UUID 且有该案件访问权限才可操作。默认无人获批；当前 owner 隔离模型尚未引入跨账号顾问分配，A 后续需顾问页面/案件分配才能形成团队审核体验。普通用户不能通过聊天、confirm 或伪造 role 批准。Mock、资料不完整或规则缺失时不能 approved，可退回/记录无法结论；新事实使旧报告 stale。
退回修改后用户编辑/重新确认并分析，生成新的报告 hash；旧审计保留。系统没有中途顾问工具调用。

## 6. C 的接入点

代码接口为 `packages/agent/contracts.py` 的 KnowledgeProvider；实现 `search_evidence` 与 `get_evidence`。机器可读 JSON Schema 位于 `docs/contracts/knowledge_provider_v0_1/`。
已有 `CKnowledgeProvider` 可对接如下**拟定** HTTP 契约，C 尚未确认其实际服务路径：

```text
POST {FSIE_AGENT_C_URL}/search
{request: SearchRequest, trusted_context: {owner, case_id}}
→ SearchResult

POST {FSIE_AGENT_C_URL}/evidence
{reference: {evidence_id, source_version_id, unit_id}, purpose: display|model,
 trusted_context: {owner, case_id}}
→ EvidenceResult
```

服务端 token 在 Authorization 头，不传浏览器。C 必须认证 B 的服务身份，并按 owner/访问策略验证授权；不能仅相信互联网客户端自报的 trusted_context。
响应 provider=c，request_id/trace_id 必须对应请求。权限缺失默认 unknown。text/hash/版本不符则不展示、不作为依据；无匹配不重试，超时/暂时不可用最多重试一次；不会切 Mock。

v0.1 文档的可选扩展：SearchRequest.kind/locators；Evidence.drift/heading/retrieved_at/coverage_cutoff/snapshot_sha256。fact_filters 仅发送白名单枚举值，不发送公司名、账户等非必要信息。C 字段不一致时只改适配器；权限和覆盖语义不一致必须重新确认契约。
检索期间先核准展示许可；入模白名单还需 model_use=allowed。首版允许仅展示资料展示原文，但不对其生成模型摘要。未验证/适用日期不明的资料可参考，不能使规则节点成为已有依据的确定结论。

## 7. 当前边界与下一轮验收

下列是混合编排前的边界记录；任务调度和期限控制的最新范围由第 9 节补充。专业、资料授权及外部环境边界仍适用。

- LangGraph 编排单轮 route/facts/retrieve/compose/validate；案件存储负责跨轮恢复。没有节点级 checkpoint、任务队列或多争点持久化依赖调度。
- 原有确定性税务规则继续运行，缺少的5个判断节点汇入最终复核清单。业务规则47条 JSON 仍是设计基线，本次没有实现通用规则 DSL 执行器。
- Python fixtures 覆盖 Mock8路径；真实模型的路由/事实抽取正确率需要独立中文场景集及授权后的在线评测。
- C 真实接口、PostgreSQL 部署、RLS角色和账号登录需 A/C 的实际环境验证。
- 案件中的历史引用保留当次授权与版本快照；若 C 需要撤销已保存原文的历史展示权，需要补充权限撤销通知/读取时授权策略，不能仅依赖当次 search 权限。当前 L0 限合成案件和获准公开参考资料，不开真实敏感语料接入。
- 同一请求并发可能重复计算但不会覆盖不同 revision；需要降低并发重复调用成本时再增加持久化请求租约。断连不保证撤销已经进入提交事务的操作，应 GET 案件核对。
- 每次检索预算3秒并限制一次重试；HTTP是连接/读超时，不承诺恶意慢速分块服务的硬实时总限。分析会分别查条文和参考案例。数据库连接/语句超时单独限制。上线需要服务端全请求 deadline。
- 真实顾问批准需完整规则/证据及账号分配；本轮只完成 B 的服务与安全校验，不宣称已有专业结论交付能力。

## 8. 当前手动测试服务与数据保留

2026-10-03 收尾时重启 8001 测试 API，现有 5174 Vite 页面继续使用该 API；保留原先 1 个合成测试案件到 `data/browser_cases_guided_intake_20261002.sqlite`（Git 忽略）。刷新页面即可使用新代码，原对话 ID 保留。该测试服务仍使用合成身份/模型边界，不是在线模型或正式部署。

以后手动重启可保留数据：

```sh
FSIE_TEST_DATABASE_PATH=data/browser_cases_guided_intake_20261002.sqlite .venv/bin/python tests/chat/serve_browser.py
```

自动测试不设置 FSIE_TEST_DATABASE_PATH，仍用独立临时数据库。为避免占用手动测试端口，可以在 apps/web 使用：

```sh
FSIE_TEST_API_PORT=8011 FSIE_TEST_WEB_PORT=5184 FSIE_TEST_PYTHON=../../.venv/bin/python PLAYWRIGHT_CHANNEL=chrome npm test -- --workers=1
```

精确控制词示例：公司（仅当前问题确实问主体时）、不知道、暂时没有资料、继续补充、先看部分整理、暂停、继续案件、重试检索。其他自然语言需要真实模型；测试启动器只提供规定的合成测试输入，不用于衡量自然语言理解准确率。

## 9. 2026-10-03 混合编排首版交接

本轮交付三个入口的兼容契约、共用 LangGraph 父图/三个子图、受限 harness、任务恢复与预算、共享分析准入、A 页面入口与状态。代码与文档在 B 工作区，未提交或推送。设计及实际执行范围见 [统一编排第 17 节](B_HYBRID_ORCHESTRATION_PLAN_2026_10_03.md#17-2026-10-03-首版执行记录)，分层验收见 [工程结果](B_HYBRID_ORCHESTRATION_ACCEPTANCE_2026_10_03.md#7-2026-10-03-工程执行记录)。

| A 发送/读取 | 类型或值 | B 行为 |
|---|---|---|
| Message.entry_hint | auto / dividend_consultation / fact_intake / reference_lookup | 缺省 auto，三按钮带对应提示；编辑预填文字后清除提示 |
| Message.reply_to_question_id | 可选问题 ID | 防止把过期答案绑定到已更换的问题；错误 question_changed，重新加载 |
| Case.orchestration | policy_version、active_task、suspended_task、queued_tasks | 刷新后保留任务；任务恢复仍通过同一个消息 API |
| Message.research_results | 多个已过滤检索束 | 展示组合请求引用；不包含仅入模原文 |
| Case.workflow | task_results、rule_decisions、budget、reason_code | 给 A 解释部分失败与未完成任务 |

原 JSON/SSE、案件确认及分析 API 保留。请求重试必须保留原 text/approval/entry_hint/reply_to_question_id/request_id，不能带当前输入框的新内容。同 ID 改 payload 返回 409 request_payload_conflict；历史无 payload 哈希的旧回执在 hybrid 下不能安全重放，应重新加载并使用新 ID。暂停任务保留；切回 legacy 的兼容投影会显式暂停无法执行的 hybrid 待办，不把孤立“是”自动写入旧事实。

正式 API 的服务端开关（`.env`，修改后重启）：

```text
FSIE_AGENT_ORCHESTRATION=hybrid
FSIE_AGENT_DYNAMIC_PLANNER=false
```

这可启用三个业务路径，但初次理解仍需要原项目可用的模型适配器。只有获准的真实模型评测环境才将 dynamic_planner 改为 true；该开关由服务端控制。默认正式配置仍为 legacy/false。当前 B 本地真实模型未配置，本轮未发在线请求。

手动工程测试无需模型/登录/C，保留现有合成案件：

```sh
# 仓库根目录；启动器端口默认 8001
FSIE_TEST_ORCHESTRATION=hybrid FSIE_TEST_DATABASE_PATH=data/browser_cases_guided_intake_20261002.sqlite .venv/bin/python tests/chat/serve_browser.py
# 另一个终端，在 apps/web
FSIE_WEB_API_URL=http://127.0.0.1:8001 npm run dev -- --port 5174
```

测试启动器默认 hybrid，dynamic_planner=False；既有页面 http://127.0.0.1:5174 刷新后可用三个按钮和规定测试控制词。初次模型解析为替身，不适合任意自然语言质量评测。自动测试使用独立临时数据库；不要用手动数据文件跑自动测试。

最新结果：**256 项 Python 通过、11 项真实 PG 未运行；25 项 Playwright 在 hybrid 下完整通过；TypeScript/Vite 构建通过。** 新增 54 项混合编排与 3 项传输期限测试。模型、C 的外部语义及专业税务正确性仍待验收。

当前动态调度支持最多三个任务顺序执行、一个活动和一个暂停任务、无匹配时一次范围内查询改写。每轮 45 秒预算、4 次模型/4 次动作/3 次搜索/14 次原文读取，嵌套分析与重试计入同一预算；源文本不进入调度观测。模型/C 的分块读取检查累计时长和 2 MB 大小，同步 socket 调用仍可能在剩余读取超时内返回，部署需额外服务超时控制。没有后台自治、节点级 checkpoint、任意 SQL/代码工具或自动批准。

C 就绪后对接 KnowledgeProvider/CKnowledgeProvider，不改 A 的聊天入口。现有 C HTTP 路径为拟定契约，实际字段、版本/权限/覆盖语义须双方验证。资料答复继续采用摘录、适用条件与缺口模板，单纯入模许可不足以允许展示。专业未决项只进最终顾问复核，不新增中途顾问任务。

## 10. 2026-10-03 免费模型评测准备与回归

新增 [62 个多轮脚本及实际模型评测程序](../../evals/b_workflow/README.md)，共 135 步，15 个首轮冒烟脚本；复用 GitHub 两分支的候选案例、自然语言材料及 A 的历史测试表，来源 commit/哈希随数据集保存。

当前免费候选为 OpenRouter Qwen `:free`；每次运行先检查零价格、账号免费余量和全局请求上限，不自动切收费型号。没有免费密钥时报告 blocked；本轮完整预检 62 blocked、0 次模型调用。原 Qwen Token Plan 需用户另行确认可用额度后才复用，未更换本地手动页面配置。

构建评测时修复了金额更正中的万/亿/千位分隔符单位校验，以及只汇总事实的独立 summary 动作。summary 保留 pending/任务，不确认事实或授权部分稿；首次直接汇总没有旧 dialogue.status 也可返回。工程回归现为 268 passed、11 deselected；受影响的 `hybrid.spec.ts` 页面回归 6 项全部通过（包括新增事实汇总）。这不是62脚本真实模型通过报告，先前25项页面完整回归仍作为历史记录。
