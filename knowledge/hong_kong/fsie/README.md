# 香港 FSIE 候选知识包

2026-09-15 新增公开裁定 Case 68、72、74、75，来源清单现为 11 项。
研究卡见 [ruling_research_cards.json](ruling_research_cards.json)；
[下载与解析验证记录](../../../docs/project/2026-09-15-ruling-source-validation.md) 记录了
50 块解析输出及四个裁定日期被旧切分器过滤的问题。公开案例不是合成评测案例，未进入模型。
以下 7 来源记录为原始基线历史状态。

这是第一个可校验的研究包骨架，不是税务意见，也不是已验证的规则库。

当前状态：

- 7 个来源已于 2026-09-01 受控抓取验证（HTTP 200），`content_sha256`、字节数等元数据已回填，`parse_status=captured`，原件尚未切分为法律单元；
- 所有来源与规则节点的专业状态仍为 `unverified`，必须经香港税务专家审核后才可激活；
- 测试案例全部为虚构案例，不得替换为客户资料；
- 规则节点只定义输入、证据和停止状态，不输出免税/应税结论；
- 字段名、证据类型、节点键和状态值必须符合 [`packages/contracts`](../../../packages/contracts/README.md) 数据契约。

验证命令：

```bash
python3 scripts/validate_fsie_package.py
```

下一步：实现受控来源管线，把原件解析、切分为法律单元并回填规则的 `source_unit_id`，补全判断链缺失的 4 个节点，并由专家逐条确认规则和证据要求。
