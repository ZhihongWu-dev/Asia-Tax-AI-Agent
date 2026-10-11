# 实际验证记录

验证日期：2026-10-11。所有命令从包含 `official/` 和 `tax_graph/` 的项目根目录执行；命令中的路径为相对路径。

源目录的 `official/`、`tax_graph/`、`cases/` 和 `信息收集.md` 共 1,857 个文件，处理前后 SHA-256 均一致。上传副本根目录仅有 `official/` 和 `tax_graph/`，下面的引擎检查与样例也在该副本独立运行通过。

## 配套资料

原先缺少的 **74 个参数、8 个法条引用**已补齐；184 条规则编译通过。D14–D31 已登记，全部 31 个口径共有 145 行引文记录，经忽略空白的逐字匹配验证通过。参数、条款、口径 CSV 与数据库一致，数据库 `integrity_check` 为 `ok`。

材料索引见 [official/HANDOFF.md](../../official/HANDOFF.md)，详细清单见 [official/handoff_audit.json](../../official/handoff_audit.json)。

## 重建

```bash
python tax_graph/validation/run_build.py
python official/tools/audit_handoff.py
```

完整构建使用 Python 3.9.23，依赖版本记录在 [build_environment.json](build_environment.json)。数据库有 396 份文件、8,438 个条款片、390 个参数，知识层有 34,299 个检索单元，复用了全部 34,299 个向量缓存。构建和知识层检查均返回成功，Error 为 0。日志见 [build.log](build.log)。

构建保留了既有 Warning，例如无法解析的交叉引用、未知生效日期、未转写公式图片；它们在 [INDEX.md](../../official/INDEX.md) 中列出。openpyxl 的页眉/页脚解析警告记录在构建日志中。此次验证未声称这些资料缺口已经解决。

## 引擎检查与案例

```bash
python tax_graph/validation/run_checks.py
```

检查和案例使用 Python 3.12.7。全部 13 个执行项成功，命令和退出码见 [results.json](results.json)。

| 执行项 | 结果 | 日志 |
|---|---|---|
| 规则编译 | 184 条规则通过 | [rules.log](rules.log) |
| 引擎 | 94 个候选，0 缺陷 | [check_engine.log](check_engine.log) |
| 字段规范 | 规则读取但未登记的字段为 0 | [check_fields.log](check_fields.log) |
| 文档提取器 | 13 项检查，0 失败 | [check_extract.log](check_extract.log) |
| 规则适用范围 | 96 项检查，0 失败 | [check_scope.log](check_scope.log) |
| 实体计算 | 6 项检查，0 差异 | [check_entity.log](check_entity.log) |
| 内地扣缴 | 22 项检查，0 差异 | [check_cn_wht.log](check_cn_wht.log) |
| 流级税项 | 25 项检查，0 差异 | [check_flow_tax.log](check_flow_tax.log) |
| 香港计算 | 19 项检查，0 差异 | [check_hk_tax.log](check_hk_tax.log) |
| 新加坡 S45 | 19 个官方标签，0 差异 | [check_sg_s45.log](check_sg_s45.log) |
| Meridian 规划器 | 成功执行，输出待补数据问题单 | [meridian.md](../examples/results/meridian.md) |
| Meridian 候选表 | 成功执行 | [meridian.table.md](../examples/results/meridian.table.md) |
| 香港模拟案例候选表 | 成功执行 | [hk_holding_services.synthetic.table.md](../examples/results/hk_holding_services.synthetic.table.md) |

Meridian 缺少集团支柱二数据，规划器实际要求补充 GloBE 所得；本次保留这一结果，没有虚构事实或把问题单改写成最终方案。香港样例是测试电池中的模拟数据。以上检查验证程序行为与配套关系，不替代独立的税务专业审核。
