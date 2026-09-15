# 香港 FSIE 新增裁定资料与实测

2026-09-15 实时从 IRD 下载 Case 68、72、74、75，四次 HTTP 请求均返回 200。
已将来源、SHA-256、字节数、抓取时间、裁定日期、适用课税年度加入 source_manifest.json。
主法源覆盖截止日仍为 2026-09-01；本次下载不代表对后续法律变更完成审核。

## 新增内容

| 案例 | 官方来源 | 研究用途 | 原有切分器输出 |
|---|---|---|---|
| 68 | https://www.ird.gov.hk/eng/ppr/advance68.htm | 非纯控股实体、人员与外包安排 | 14 块 |
| 72 | https://www.ird.gov.hk/eng/ppr/advance72.htm | 境外股息账户路径、资本认购、参与路径 | 13 块 |
| 74 | https://www.ird.gov.hk/eng/ppr/advance74.htm | 60% 持股、25% 企业税率与 10% 预提税率的区别 | 12 块 |
| 75 | https://www.ird.gov.hk/eng/ppr/advance75.htm | 实物股息和同日向母公司再分派 | 11 块 |

研究卡保存在 knowledge/hong_kong/fsie/ruling_research_cards.json，分别记录事实摘要、
官方裁定摘要、段落定位、待验证问题和现有系统的能力边界。摘要由人工方式整理，未经专业验证。
来源与判断节点的关联只用于研究索引，不改变 rules.json 的执行依据。
IR1298B 本轮未加入，暂保持案件资料优先的范围。

## 实测结果

使用现有 fetch_source 下载到 git-ignored raw 目录，再以 segment_html 切分：共 50 个文本块。
随后运行 scripts/inspect_ruling_sources.py，复用同一批快照并核对清单哈希。
16 个原文抽查点全部命中；切分后保留 12/16，四案的裁定日期均丢失。
原因：现有通用 HTML 切分器会过滤不足 40 字符的块。日期已单独保存到来源元数据，
但切分器本身尚未修复。这是定向抽查，不能解释成全体内容召回率 75%。

知识包校验通过：11 来源、6 规则、8 证据要求、10 合成案例；71 项离线测试通过。
未执行数据库入库、LLM 抽取或规则端到端评测；50 块是解析输出，不是新增落库记录。
当前 L0 模型策略仅允许合成数据，因此公开案例未发送至模型供应商。
这些公开匿名案例 synthetic=false，不放进要求 synthetic=true 的候选评测集。

## 复现

在安装项目 dev 依赖的环境运行：

```sh
python scripts/inspect_ruling_sources.py
python scripts/validate_fsie_package.py
python -m pytest -m "not integration"
```

脚本只抓取研究卡所列四个来源。已有快照将被复用，不是实时更新监控；
新环境会下载官方页面，若与本次固定哈希不一致会停止该案验证并报告差异。
完整运行记录写入 knowledge/hong_kong/fsie/raw/ruling_probe_report.json。
输出中的 retained_in_units=false 是诊断发现；脚本成功退出只表示原文抽查和哈希通过，
不是切分器无损通过。官方短语仅为定位探针，不用于自动判断税务结果。

## 使用边界和后续实验

IRD 公开裁定经匿名处理，只针对特定事实，且不会随法律变更更新：
https://www.ird.gov.hk/eng/ppr/arc.htm

下一轮可以先修复日期与章节归属保留，再开展事实抽取实验。
实验需要将事实背景/安排与裁定答案分离；若将整篇裁定放入检索库，不能用同一案声称盲测成功。
如果仍保持模型仅处理合成数据，则应编写明确标注的合成变体，不能把公开个案改标签冒充合成案例。
