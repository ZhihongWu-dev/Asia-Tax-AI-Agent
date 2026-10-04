# B Agent 多轮业务评测

日期：2026-10-03。数据版本 `b-workflow-0.1`。62 个脚本、135 个步骤，15 个脚本组成首轮冒烟子集。所有案情为合成信息；期望值是工程行为标准，尚未成为专家税务金标。

**2026-10-04 更新**：已使用用户授权的免费 OpenRouter 配置完成部分实际模型调用。普通对话/语言切换、部分事实提取/追问成功；完整连续链路多次受模型超时/限流阻断；指定案例范围、混合更正等也有真实行为失败。当前不能报告全链路或 62 脚本在线通过。下方“待凭据”是 2026-10-03 的历史记录；提交后的最新协作入口是 [B_TEAM_HANDOFF](../../docs/implementation/B_TEAM_HANDOFF.md)。

新增 `v0.1/model_e2e.json`，包含空白案件全流程及三个诊断场景；使用 `--dataset` 选择。每次调用记录 stage（plan_turn/plan_next 等）、费用、耗时及脱敏故障类别，不保存密钥。全流程预期保持原样，失败不会改成通过。2026-10-04 当前工程验证为 270 项后端、26 项浏览器通过，构建/知识包校验通过；这与在线结果不同。

## 资料来源

已执行 `git fetch origin` 并检查 main 与 Zhihong-Wu 两个远程分支。来源的精确 commit、路径及 SHA-256 保存于 [cases.json](v0.1/cases.json) 的 sources，构建器要求本地来源与对应 GitHub blob 完全一致。

- main 的 `tests/fsie/candidate_cases.json`：10 个版本化合成候选案例，结构化前置事实与阻断项。
- main 的 `tests/fsie/natural_language_cases`：6 个既有自然语言案件及 1 个系统指令覆盖攻击。本轮重新定义业务预期，旧 stop_and_escalate/human_review_required 不代表增加中途顾问。
- Zhihong-Wu 的 `docs/project/evaluations/Taxora_测试记录.xlsx` 与 README：20 问历史记录，本轮抽取相关问题和失败方向，覆盖概念/地区、Case 68 日期、指定法条、参与豁免、案情汇总、无匹配、最新修订及无依据免税确认。没有把旧模型答案用作金标，也没有宣称本轮重跑了旧 20 问全表。
- B 的现有追问、混合编排和验收矩阵：补充 unknown、deferred、明确更正/真正矛盾、任务切换/恢复、权限、预算、幂等、部分稿、分析与最终复核。

## 脚本内容与覆盖

每个脚本包含 ID、合成标记、来源、测试前置事实、Mock 情况、多个操作、每步行为断言。seed_facts 只建立前置状态，不能算模型抽取通过。正式消息经原 FastAPI JSON/SSE API、生产 plan_turn/harness、实际 LangGraph、存储、业务校验执行；仅身份和未就绪的 C 为替身。测试启动器的假模型解析器不参与实际模型评测。

| 行为组 | 脚本数 | 重点 |
|---|---:|---|
| 三入口 / 闲聊 / 范围 | 10 | 入口是提示、普通聊天不检索、假设不写事实、个人/其他地区不套香港企业流程 |
| 事实 / 追问目标 / 更正 | 15 | 一次一个问题、未知、暂缺、停止重复问、日期不猜、描述不推断资格、中英文数值、单位更正 |
| 资料 / 无依据 / 权限 | 8 | 指定编号保留、查询承接、无匹配与故障分开、展示/入模许可、版本异常 |
| 任务 / 混合消息 | 8 | 暂停恢复、独立查询与冲突隔离、更正+检索失败、多个结果保留、新客户不覆盖 |
| 分析 / 传输 / 安全 | 11 | 事实确认、部分稿许可失效、唯一最终复核、幂等、问题ID、SSE、刷新与攻击 |
| 历史自然语言 / 报错题 | 10 | 6 个历史案件和参与豁免、汇总、无依据、时效回归 |

检查包括返回状态/错误码、回答是否包含所需已知事实和缺口、字段值与禁止推断、实际搜索次数、查询编号/范围、分析产生时机、重复请求外部调用、禁止原文进入模型。显示专用哨兵植入 MOCK-03；Meter 在每一次真实模型请求发出之前检查，不能用最终回答没泄露来替代上下文检查。

不使用另一个模型自动宣布税务答案正确。上述 62 个脚本覆盖有限原型的行为；未覆盖所有现实税务交易、所有表达变体、真实 C 的召回/覆盖/权限或账号分配。普通聊天的主张过滤仍是保守规则，不能凭少量否定字符串检查宣称无幻觉。

## 免费 API 选择与当前阻断

已查询官方模型目录，OpenRouter `qwen/qwen3.8-27b:free` 当次 prompt/completion 价格为 0，提供兼容 chat/completions 的接口。参考 [官方模型页](https://openrouter.ai/qwen/qwen3.8-27b:free)、[认证示例](https://openrouter.ai/docs/quickstart)、[免费额度与限流](https://openrouter.ai/docs/api/reference/limits)。免费仍需账户密钥；免费型号、额度、可用性随时间改变，运行前重新核验。

匿名 Pollinations 探测：`text.pollinations.ai/openai` POST 返回 404；`gen.pollinations.ai/v1/chat/completions` POST 返回 401。仅发送不含案情的 JSON 问候；没有成功推理、没有获取陌生人的密钥，也没有把模型目录 GET 当成冒烟成功。官方新版文档也要求 API Key，见 [认证说明](https://github.com/pollinations/pollinations/blob/main/gen.pollinations.ai/src/docs/apidocs-recipes.md)。

本地 B 与进程没有免费提供商密钥。原工程存在阿里云 Qwen Token Plan 配置；只检查了存在性、主机及模型名，未打印、复制或调用密钥。是否有足够免费/已包含额度尚未核实，必须收到用户授权才使用此备选。

当前 [完整预检](runs/preflight_full_2026_10_03.json) 是 **62 blocked、0 passed、0 failed、0 次模型调用**，原因 missing_openrouter_key。不是在线通过报告。既有 268 项 Python 工程回归与此 62 个脚本的在线结果须分别报告。

## 运行方式

所有命令在 B 仓库根目录执行。将自己的免费账户密钥仅配置到 Git 忽略的私有 `.env`，变量 `OPENROUTER_API_KEY`；不要在聊天、代码、命令参数或报告中粘贴密钥。代码不会修改现有 .env，不会更换手动页面模型或生产数据库。

```sh
# 只校验脚本，不进行推理，也不计作案例通过
.venv/bin/python scripts/evaluate_b_workflow.py --validate-only

# 首轮 15 脚本：最多40次模型请求，串行间隔3秒
.venv/bin/python scripts/evaluate_b_workflow.py --suite smoke --output evals/b_workflow/runs/smoke.json

# 精选失败脚本复验，保持原数据集预期
.venv/bin/python scripts/evaluate_b_workflow.py --select BWF-017,BWF-059 --output evals/b_workflow/runs/recheck.json

# 全集，仍受免费额度和40次请求上限限制；不够时标blocked，不能自动付费
.venv/bin/python scripts/evaluate_b_workflow.py --suite full --output evals/b_workflow/runs/full.json
```

运行前通过官方目录核实显式非 OpenAI 的 :free 型号及所有公布价格，读取自己账户的免费剩余额度；请求上限取剩余额度和 --max-calls 的较小值。无密钥、价格不为0、预检失败、免费额度耗尽均停止真实调用。默认不切换付费模型、不买额度、不自动降级为 Mock 模型答案；检索依然明确是 Mock。

用户明确授权原 Qwen 套餐后才可运行：

```sh
.venv/bin/python scripts/evaluate_b_workflow.py --provider existing-plan --authorized-existing-plan --env-file ../Asia-Tax-AI-Agent/.env --max-calls 30 --output evals/b_workflow/runs/qwen_plan.json
```

此模式读取原私有配置到内存，不写回；不能标成“免费 OpenRouter 结果”。默认 max-calls 40，可手动设为1～200；免费限额不足时保留阻断/未执行项，不以循环新账户/新密钥规避限流。一个完整多轮集通常需要超过40次调用，按免费额度分批执行并保留每次单独报告；不要用子集通过代替全集。

## 结果与收尾

每步记录合成输入、期望、实际工作流、事实、已过滤页面消息、工具数和耗时；每次模型调用只记状态、异常类型及 usage，不保存 Authorization 或包含密钥的原错误文本。工作区报告保留 `.json` 完整记录和 `.md` 摘要，case DB 使用临时隔离目录并销毁，个人会话不会写入。

发现的工程缺口已补充：金额更正支持万/亿/千位分隔符及明确英文单位；事实汇总独立于部分分析许可，保留原问题与任务、不消费追问次数、不确认事实、不批准报告；首次直接汇总时没有对话状态也能返回。新增工具与边界测试 12 项，完整 Python **268 passed、11 deselected**；受影响的 hybrid 页面组 **6 passed**。真实模型运行仍等待凭据选择，不能据这些工程结果推断所有真实流程成功。
