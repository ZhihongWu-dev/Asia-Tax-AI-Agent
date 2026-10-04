# KnowledgeProvider 接口契约与模拟检索行为设计 v0.1

| 项目 | 内容 |
|---|---|
| 日期 | 2026-10-02 |
| 状态 | B 模块设计契约；尚未实现 Provider、HTTP/MCP 服务或真实数据库连接 |
| 当前条件 | A 页面已可接入；C 数据库尚未成型 |
| 本次交付 | 统一接口、字段语义、权限/错误映射、固定 Mock 响应样例和验收场景 |
| 关联 | [业务流程 v0.3](AGENT_BUSINESS_WORKFLOW_V0_1.md) · [业务规则 v0.2](AGENT_BUSINESS_RULES_V0_1.md) |
| 样例 | [knowledge_provider_mock_fixtures.v0.1.json](knowledge_provider_mock_fixtures.v0.1.json) |

## 1. 接入边界

```text
A 已有页面
  → B 的 Agent 与业务流程
    → KnowledgeProvider（统一契约）
      → MockKnowledgeProvider（当前开发测试）
      → CKnowledgeProvider（后续 API / MCP / 只读数据库适配）
```

B 定义何时检索、查询内容、返回检查、资料权限过滤、回答结构和异常行为。C 负责资料、数据库、检索及数据权限元信息。A 负责页面及引用展示。B 的对话、案件、待答问题和回复版本独立保存。

提供方由服务端配置选定。正常业务参数不含 fixture_id，用户和模型不得切换提供方或选择 Mock 场景。真实服务失败不自动退回 Mock。开发测试请求的 scenario_id 由测试驱动单独设置，不进入线上查询协议。

概念接口如下，非现有可导入代码：

```text
search_evidence(request, trusted_context) -> SearchResult
get_evidence(reference, purpose, trusted_context) -> EvidenceResult
```

trusted_context 由认证服务/固定开发身份生成，含权限范围、服务端处理环境和访问策略；模型不能提供授权身份。purpose 仅为 model 或 display；get_evidence 仍须校验当前权限，不能因先前 search 成功就放行。

## 2. 查询输入 SearchRequest

| 字段 | 类型与要求 | 语义 |
|---|---|---|
| schema_version | string，必填，0.1.0 | 契约版本；不兼容版本拒绝 |
| request_id、trace_id | string，必填 | 调用身份和跨组件追踪；一次逻辑查询重试保持关联 |
| query | 非空 string | 本轮问题或当前争点，精确编号必须原样保留 |
| intent | enum | concept / reference_lookup / case_analysis |
| jurisdiction、topic、income_type | string 或 null | 已知则筛选；未知显式为空，不能静默默认地区 |
| entity_type | company / individual / unknown / not_needed | 具体案件按必要性使用，查编号无需问主体 |
| applicable_date | ISO 日期或 null | 事实或用户查询指定的适用日期，不用运行当天替代 |
| date_status | actual / planned / unknown / not_needed | unknown/not_needed 对应空日期；actual/planned 要有明确日期 |
| reference_number | string 或 null | 精确条款/裁定等编号，完整保留格式 |
| fact_filters | 数组，必填，可空 | 仅必要事实：field、value、status、fact_version；未知不变成否定 |
| language | string | 期望结果语种；原文语种另由证据返回 |
| limit | 正整数 | 本轮最大返回数，实施时由服务端上限限制 |
| deadline_ms | 正整数 | 本次调用剩余超时预算；不可无限等待 |

只有最少查询信息满足时才调用；不完整上下文先由 B 提问，而不是把问题发给 C 猜。查询不包含完整会话、数据库密码或无关的客户事实。缓存键还须纳入可信访问范围和处理环境。

## 3. 返回 SearchResult

| 字段 | 类型 | 要求 |
|---|---|---|
| schema_version、request_id、trace_id | string | 必须与契约和请求对应 |
| retrieval_id | string | 唯一检索记录标识 |
| provider | mock / c | 由可信适配器写入，不由模型写入 |
| is_synthetic | boolean | Mock 固定 true，真实 C 响应仍按实际数据来源标记 |
| corpus_version | string 或 null | 索引/语料快照版本；无法提供时不能声称版本已核验 |
| status | ok / partial / no_match / error | 查询状态，不直接等于依据充分或法律适用 |
| evidence | Evidence 数组 | error/no_match 为空；返回部分结果时 status=partial |
| coverage | object | status 为 unchecked / partial / sufficient_for_task / not_assessed；附 scope、missing_requirements 和 truncated |
| error | object 或 null | error 时必填 code、message、retryable；message 不含凭证或原始敏感数据 |
| timings_ms | object | db、retrieval、rerank、total 为非负数或 null；Mock 固定 null，不能作为性能基线 |

约束：ok 表示调用正常并有结果；不代表全案条件已满足。sufficient_for_task 必须有对应检查依据及明确任务范围；B 独立检查拟生成主张，不直接信任一个覆盖标签。分页/截断不能标成完整覆盖。调用成功但所有命中材料不能入模，仍返回 ok/partial 和真实权限；B 输出 EVIDENCE_RESTRICTED，不把它变成 no_match。

### Evidence

每项至少包括：

- **身份**：evidence_id、source_id、source_version_id、unit_id、content_hash（原文单元 SHA-256）、is_synthetic。
- **来源**：title、publisher、source_type（law / guidance / case / synthetic_test）、language、url（可空）、locator。
- **适用性**：jurisdiction、topic、publication_date、effective_from、effective_to、verification_status（verified / unverified / unknown）。未知日期为空，不用发布日期代替生效日。
- **权限**：model_use、display_use，均为 allowed / denied / unknown；policy_version、restriction_reason。权限未声明视为 unknown，不默认允许。
- **内容投影**：model_text（string 或 null）、display_ref（object 或 null）。只有 model_use=allowed 才允许 model_text 非空；只有 display_use=allowed 才提供可解析的 display_ref。

本版模型只消费明确获准的 model_text 及经服务端批准的必要元数据投影，禁止把完整 Evidence JSON 直接作为模型上下文。其他字段即使在服务器可见，也不自动获得入模许可。若某项标题等元数据不能展示，适配器必须删除/脱敏或不返回该项，不能机械满足字段要求而泄露内容。

display_ref 由 evidence_id、source_version_id、unit_id 组成，通过 get_evidence(..., purpose=display) 取得原文。此引用是定位信息，不是访问凭证，不能绕过权限。对模型只允许而前端不可展示的资料，不回显原文；缺少允许的出处时标注引用展示缺口，必要时撤下对应主张。

content_hash 对应来源原文，而不是截短摘要。若 model_text 为节选，应保留具体 locator；如 C 提供摘要，则明确摘要类型及来源，不将摘要伪装成原文。Mock 样例使用与单元相同的 model_text 简化演示。

## 4. 按引用取原文

get_evidence 的输入包含 request_id、trace_id、schema_version，以及完整 reference（evidence_id、source_version_id、unit_id），另由服务端指定 purpose。

输出包含：status（ok / not_found / restricted / version_unavailable / error）、reference、content_hash、text、is_synthetic、error。只有 ok 才允许 text 非空，并须与指定引用及内容哈希对应。

不允许把旧版本引用自动解析成最新版本；找不到旧版本则返回 version_unavailable。权限改变后返回 restricted。A 可通过 B 的代理或双方约定的 C 展示服务读取，具体传输路由待与 A/C 确认；无需 B 实现页面组件。

## 5. 检索结果到 Agent 行为的映射

| 结果 | B 检查 | 下一步 |
|---|---|---|
| ok + 获准材料 | 版本、适用范围和本次主张支持情况 | 足够则组织回答；不足则 EVIDENCE_INSUFFICIENT |
| partial | 缺失项、截断范围及是否可支持局部主张 | 仅输出可支持部分，明确限制；需要补充时单问题追问 |
| no_match | 区分确实无匹配与传输失败 | NO_MATCH，说明本次查询缺口，不猜税务结论 |
| 命中但全部不可入模 | 模型权限与展示权限分别检查 | EVIDENCE_RESTRICTED；可展示项列 reference_only |
| 权限缺失/unknown | 默认不入模 | 记录权限缺口；不得请求模型帮忙判断授权 |
| error | 明确错误码、是否临时、剩余预算 | RETRIEVAL_FAILED；仅临时故障可有限重试 |
| 返回字段非法/版本不兼容 | 契约检查 | PROVIDER_CONTRACT_ERROR；不把原文透传给模型 |
| 引用无法解析 | 指定版本与原文校验 | CITATION_UNRESOLVED；修复或撤下对应主张 |

模型失败发生于 B 生成阶段，不伪造成 Provider 的 no_match/error。用 MODEL_FAILED 返回 A；检索快照、权限及事实版本仍有效时复用，以免重复查询。故障重试预算由 B 与底层客户端共享，禁止层层独立重试放大请求。

## 6. MockKnowledgeProvider 行为

Mock 是未来实现规范；本次仅提供可加载的 JSON 样例，没有可调用 Provider 类。测试驱动选择场景，业务请求不暴露测试控制参数。每个场景使用固定结果和版本，可重复执行，不调用网络或生成虚构“真实法条”。

| 场景 ID | 结果 | 检查目的 |
|---|---|---|
| MOCK-01 | ok，允许入模与展示 | 回复包含重点、条件、可解析引用；所有内容标模拟 |
| MOCK-02 | no_match | 不生成无依据结论，不无意义重试 |
| MOCK-03 | ok，仅允许展示 | reference_only 有资料，模型各调用输入没有受限正文 |
| MOCK-04 | error，临时超时 | 有限重试；耗尽后返回检索失败 |
| MOCK-05 | partial，缺少必要材料 | 只保留已支持范围，不能标整体完成 |
| MOCK-06 | ok，权限 unknown | 默认不入模、不展示未知许可正文 |
| MOCK-07 | ok，资料日期不覆盖测试目标日期 | B 识别版本适用缺口，不引用为本案确定依据 |
| MOCK-08 | error，不可重试的权限拒绝 | 不重试、不换身份、不降级成 Mock 成功 |

样例中 display_store 模拟 C 的原文存储，仅由测试版 get_evidence 使用；它不是 search 返回的一部分，禁止将整个 fixture 文件作为模型上下文。原文读取仍按 Evidence 权限检查。

客户端额外应做三类故障注入：删掉必填字段→契约错误；改变引用版本→version_unavailable；让生成模型失败→MODEL_FAILED 并验证是否复用获准检索结果。这些是待实现的运行测试，不是本次已执行的模型/服务测试。

## 7. 切换到 CKnowledgeProvider

1. C 提供真实接口/只读视图说明、数据样例、权限语义和来源版本策略；凭证通过服务配置，不放文档或模型消息。
2. B 建立字段映射，补充缺省处理。缺少权限默认 unknown，缺少时间默认 null；不能假造已验证状态。
3. 共用契约测试，运行正常、无匹配、部分结果、受限资料、故障和旧引用读取。
4. 对比真实原文及引用，记录查询性能、检索质量和语料版本；Mock 检查不能替代真实验收。
5. 通过服务端配置启用 C；必要时仅在测试环境切回 Mock，所有模拟标记保留。

语义相同的字段可直接适配；资料使用范围、版本保留能力或支持范围不同，则需修改契约/业务能力声明并回归，不能承诺任何 C 数据结构都可零修改接入。

## 8. 完成标准与当前状态

设计完成标准：调用边界明确；输入输出及错误可解释；资料有独立的模型/展示许可；Mock 覆盖关键分支；B/C 和 B/A 责任清晰。以上已在本稿定义。

尚待实施：Provider 类、传输接口、可信权限过滤器、上下文构造、原文读取服务、真实模型与页面联调、状态持久化及 C 真实连接。本次样例结构检查只能验证设计一致性，不证明运行时权限隔离、税务正确性或性能。

2026-10-02 检查记录：8 个 Mock 样例的请求/响应标识、状态组合、日期语义、模拟标记、权限与内容投影、引用定位及内容哈希检查通过；相关文档相对链接、代码围栏和 Git 空白检查通过。未执行 Provider、模型、C 数据库或前端集成测试。

## 9. 与 A 的 `Zhihong-Wu` 分支对接（代码核查）

2026-10-02 读取 GitHub 分支提交 `7054c45323abf7d63d9725f03f81dab892c98110`。以下是该提交的实际代码接口，不推定 C 后续数据库已经交付。A 分支已有 React 页面、FastAPI 聊天接口、会话持久化及一版词法/编号检索；这里的检索现状是该分支的实现，不等同于 C 的最终交付。

### 9.1 现有前端如何调用后端

- [`apps/web/src/api.ts`](https://github.com/ZhihongWu-dev/Asia-Tax-AI-Agent/blob/7054c45323abf7d63d9725f03f81dab892c98110/apps/web/src/api.ts)：聊天 `POST /api/cases/{id}/messages`，提交 `text, data_approved, revision, request_id`，请求 `text/event-stream`；只识别 `delta`、`error`、`done`，其中 `done.case` 是完整案件对象。另有 `GET /api/knowledge/search?q=...`、会话/案件、事实修改、确认及分析接口。
- [`apps/web/src/hooks/useWorkspace.ts`](https://github.com/ZhihongWu-dev/Asia-Tax-AI-Agent/blob/7054c45323abf7d63d9725f03f81dab892c98110/apps/web/src/hooks/useWorkspace.ts)：页面提交时生成请求 ID、传案件 revision；失败重试复用同一请求操作；刷新读取案件。B 的处理须保留请求幂等、revision 冲突和相同案件 ID 的恢复语义。
- [`apps/web/src/workspace.ts`](https://github.com/ZhihongWu-dev/Asia-Tax-AI-Agent/blob/7054c45323abf7d63d9725f03f81dab892c98110/apps/web/src/workspace.ts)：前端 `Case` 包含 messages、facts、questions、analyses、confirmed_revision；`Message.kind` 有 chat、research、analysis、intake 等实际使用值；`KnowledgeResult` 为 `status, passages, method, query`。首阶段须保持这些旧字段可用。
- [`apps/web/src/components/Conversation.tsx`](https://github.com/ZhihongWu-dev/Asia-Tax-AI-Agent/blob/7054c45323abf7d63d9725f03f81dab892c98110/apps/web/src/components/Conversation.tsx)：`research` 消息显示 `message.text` 及 `message.research.passages`；`analysis` 消息用 analysis_id 在 `Case.analyses` 查结果。现有 Passages 可展开原文及来源；尚未提供每项回答主张到单条证据的交互链接。

### 9.2 B 应接在哪一层

| 位置 | 该分支现状 | B 的接入动作 |
|---|---|---|
| [`apps/api/chat.py`](https://github.com/ZhihongWu-dev/Asia-Tax-AI-Agent/blob/7054c45323abf7d63d9725f03f81dab892c98110/apps/api/chat.py) | FastAPI 路由调用 ChatService；消息支持普通 JSON 和 SSE；`get_service()` 构造会话服务 | 保持 A 现有路径和请求体，注入/调用 B 的编排服务；统一普通与 SSE 的业务判断，避免两条路径结果不同 |
| [`packages/chat/service.py`](https://github.com/ZhihongWu-dev/Asia-Tax-AI-Agent/blob/7054c45323abf7d63d9725f03f81dab892c98110/packages/chat/service.py) | `plan_turn` 返回 chat/research/intake；`ChatService.commit_turn` 在 research 时调用 `researcher(query)`，保存事实和消息 | 在此引入 B 的对话入口、必要追问、权限/范围/版本检查和统一回复；保留存储、版本及幂等保护 |
| [`packages/chat/streaming.py`](https://github.com/ZhihongWu-dev/Asia-Tax-AI-Agent/blob/7054c45323abf7d63d9725f03f81dab892c98110/packages/chat/streaming.py) | 先产生模型 `reply` 的 delta，随后调用检索并提交 `done.case` | 与普通路径共用 B 的决策及检索处理；实质税务主张校验后再输出。可先只发送进度或直接 done，A 的现有流消费者仍可处理 |
| [`packages/chat/knowledge.py`](https://github.com/ZhihongWu-dev/Asia-Tax-AI-Agent/blob/7054c45323abf7d63d9725f03f81dab892c98110/packages/chat/knowledge.py) | 从 Source/LegalUnit 读取并返回 `available / no_matching_units / unavailable`、passages；原文未传外部模型 | 该模块是现有知识实现或迁移过渡。B 新增 KnowledgeProvider 适配层，把 Mock/C 返回转成统一证据契约，再映射到旧 KnowledgeResult 展示格式 |
| [`packages/chat/store.py`](https://github.com/ZhihongWu-dev/Asia-Tax-AI-Agent/blob/7054c45323abf7d63d9725f03f81dab892c98110/packages/chat/store.py) | `chat_cases` 保存完整文档，revision 乐观锁及 receipts 幂等 | B 的状态、问题及依据版本先写入同一案件记录或受控附表，勿另建互不相认的会话 ID |

仅把 C/Mock 赋值给 `ChatService.researcher` 还不够：现有调用仅传 `query`，缺少争点、适用日期、事实版本、资料使用环境及访问范围。B 须扩展服务层调用上下文或建立专门的 provider adapter，并让普通 JSON 与 SSE 路径使用同一逻辑。前端和模型均不接触 C 的数据库连接。

### 9.3 最小兼容响应与功能差距

首阶段沿用 A 的结构：

```json
{
  "type": "done",
  "case": {
    "id": "沿用现有案件 ID",
    "revision": 2,
    "state": "沿用已协商的状态",
    "messages": [
      {
        "id": "后端生成的消息 ID",
        "role": "assistant",
        "kind": "research",
        "text": "回答重点：……\n\n适用条件：……\n\n对应引用：[1]（模拟示例）",
        "research": {
          "status": "available",
          "method": "mock_provider_adapter",
          "query": "本轮查询",
          "passages": []
        }
      }
    ],
    "facts": {},
    "questions": [],
    "analyses": [],
    "confirmed_revision": null,
    "data_approved": true
  }
}
```

上例只说明字段位置，不能直接用作完整案件响应；正式响应须保留 A 当前所需的 title、时间等字段及真实旧消息。`passages` 只装 **display_use=allowed** 的授权展示投影；模型输入另由获准 `model_text` 构造。不得把整个检索 JSON 送入模型。`Message.text` 可先按“回答重点、适用条件、对应引用”组织 Markdown；如果需要点击正文中的 [1] 直达具体证据，B 定义 `claim → evidence_id` 映射，A 再实现 UI。仅有页面下方可展开资料不等于主张级引用已实现。

当前 `research` 分支保存的 `reply` 是“将查阅什么”的检索前短句，真正返回的是资料片段；B 需要在检索之后根据获准且适用的资料形成已校验的答复。仅有 display_only 原文时提供资料查看与使用限制，不能让模型先总结这段原文再形成答案。没有资料、检索失败和模型失败分别映射为前端已有/新增安全错误码。

现有 `FactEditor` 的“确认事实并分析”仍可承接案件分析入口；它表示用户核对事实，不代表顾问最终批准。B 的唯一最终顾问复核仍需后续服务状态与界面支持，本轮不能把 `review_required` 自动提升为 approved。

### 9.4 联调顺序

1. 在 A 分支或合并后的共同分支先保持 `/api` 路径、消息提交体、SSE 事件及完整 Case 结构；B 以适配器接入 Mock，不让 A 为 Mock 改页面。
2. 先验证 `POST /messages` 的普通聊天、具体事实补充、research 命中、无匹配、仅展示、模型/检索失败；用 `GET /cases/{id}` 核对恢复和引用快照。
3. 验证 `GET /knowledge/search` 仍供资料面板使用；它的 `passages` 与聊天引用要从同一证据适配结果产生，防止两套定位。
4. 再切 C 的真实提供方并重跑同一组测试。确认授权原文、版本、日期和查询性能后，才算完成 C 接入。

此节是对指定 GitHub 提交的只读代码核查和接入建议。当前本地工作分支未包含 A 分支代码；尚未实施或运行这套接线。


## 10. 首版代码落地（2026-10-02）

本 worktree 已实现 `packages/agent/contracts.py`、`providers.py`、`knowledge.py`。Mock fixtures 已有运行实现；C HTTP 路径为拟定协议，尚未完成 C 的真实接口验收。
机器可读模型位于 `docs/contracts/knowledge_provider_v0_1/`。可选增加 kind/locators 供现有 A 搜索与规则分析；Evidence 增加 drift/heading/retrieved_at/coverage_cutoff/snapshot_sha256 以保留原页面来源信息。
具体安装、配置、权限限制、HTTP 请求与测试命令见 `docs/implementation/B_AGENT_LOCAL_RUN_AND_HANDOFF.md`。

## 2026-10-02 对话接入补充

B 增加动态追问、候选场景识别与原始描述字段，但本版本 C 请求字段/过滤白名单不扩张。用户案件事实从用户描述或其授权材料获取，C 的法规和参考案例不能补造用户事实。B 按本轮任务决定是否携带案件过滤：独立资料查询不带旧案日期；案件关联查询中实际/计划与日期同时明确才传适用日期，否则 date_status=unknown。

纯检索故障仍为 knowledge_unavailable；带事实修订的混合消息可在保存修订后返回 workflow.status=partial_failure、reason_code=retrieval_failed、error_code=knowledge_unavailable 与 retryable。完整 Case 内保存 deferred_query，用户明确重试后只恢复查询，不重复事实写入。底层 error 仅透出 code/retryable，不返回原始异常/连接参数。无匹配包含 query 与期间/事实缺口，不等于法规不存在。

A 的可选 question/identification/dialogue 字段详见 [实现规范第 6 节](../implementation/B_GUIDED_INTAKE_DESIGN_2026_10_02.md#6-本轮落地接口与兼容方式)。
