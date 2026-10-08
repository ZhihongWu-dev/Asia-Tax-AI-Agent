# INDEX

由 `tools/graph.py` 生成，不要手改。知识层的设计、原理与依据见 [README.md](README.md) 第 3.3、6.2、7–9 节，参考文献在第 16 节。

| 表 | 行数 |
|---|---|
| work | 205 |
| expression | 322 |
| provision | 6360 |
| clause_meta | 7805 |
| unit | 29640 |
| edge | 13433 |
| term | 4576 |
| event | 243 |
| tombstone | 16 |
| anchor | 396 |
| alias | 216 |

## 关系（edge）

| kind | status | 条数 |
|---|---|---|
| amends | resolved | 22 |
| attachment_of | resolved | 29 |
| cites | ancestor | 2406 |
| cites | resolved | 5765 |
| cites | unresolved | 392 |
| cites_act | act_only | 2 |
| cites_act | unresolved | 622 |
| contains | resolved | 851 |
| decision_cites | resolved | 27 |
| gap_cites | resolved | 65 |
| interprets | resolved | 5 |
| param_cites | resolved | 304 |
| part_of | resolved | 66 |
| rule_cites | resolved | 48 |
| rule_uses_param | resolved | 447 |
| same_manifestation | resolved | 2 |
| same_provision | resolved | 2325 |
| substitutes | resolved | 55 |

## 交叉引用的解析

显式引用 8563 条，解析到条款 8171 条（其中只到上级条款的 2406 条），未解析 392 条；未解析的保留原文，不猜。

未解析最多的目标：

- `Insurance Act 1966` ×28
- `Central Provident Fund Act 1953` ×27
- `VCC Act` ×26
- `Companies Act 1967` ×20
- `Insurance Act 1966` ×17
- `Securities and Futures Ordinance (Cap. 571)` ×16
- `Buildings Ordinance (Cap. 123)` ×15
- `Banking Ordinance (Cap. 155)` ×14
- `Merchant Shipping Act 1995` ×13
- `Insurance Ordinance (Cap. 41)` ×13
- `Part 1 of Schedule 1 to the Securities and Futures Ordinance` ×12
- `Occupational Retirement Schemes Ordinance (Cap. 426)` ×12

## 检索单元

- clause：3599 个，平均 287 字符，最长 978
- part：26041 个，平均 441 字符，最长 1038

## 引文锚定

- ambiguous：30
- no_quote：1
- unique：365

## 定义词

- cn.so_called：128
- en.quoted：1811
- hk.en_with_zh：1344
- hk.zh_with_en：1293

## 口径（decisions.csv）

| 口径 | 锚点 | 代码引用 | 内容 |
|---|---|---|---|
| D01 | unique 3 | 2 | 可抵免的外国税只是应当缴纳且已实际缴纳的部分：已缴超过应缴的部分不抵（走来源地退税），未缴的不抵；抵免池与逐项抵免都取 min（实缴，应缴） |
| D02 | unique 2 | 2 | 新加坡的补足税（DTT、MTT）不受 Part 14 双重征税减免（第 50、50A、50C 条）的抵免：抵免池不收补足税伪流；内地模型中无补足税 |
| D03 | unique 1 | 1 | 已结税项（时钟全过或案例声明）：实缴额不再变；其法域的规则只改变应缴额，从而改变别处的抵免额（抵免以应缴为限，D01），所以对它有利的一端反转为使应缴额更高的一端 |
| D04 | unique 2 | 2 | 间接抵免中本层企业的税额是其实际缴纳的税额，即本层自己享受直接与间接抵免之后的数；引擎因此对实流、实体级抵免、伪流反复求值到不动点 |
| D05 | unique 3 | 2 | 间接抵免逐层计算，最多五层：第一层由居民企业直接持股 20% 以上；以下各层由单一上一层直接持股 20% 以上，且居民企业直接或经合格各层间接合计持股 20% 以上；不合格的一层，其税额不向上传 |
| D06 | unique 3 | 1 | 本层税额包括它收到股息时被源泉扣缴的税与它间接负担的下层税额；本层税后利润扣除其直接缴纳与被扣缴的税 |
| D07 | unique 2 | 1 | 股息间接负担的是其所分配利润所属年度的税（可以是以前年度的未分配利润）：公式取同一年度的税额与税后利润；方案新设公司的分配年度由其利润分配决议写明，是方案的动作 |
| D08 | unique 1 | 1 | 间接抵免只对居民企业从外国企业分得的境外来源股息：居民企业之间的股息归国内规则，不享受外国税抵免 |
| D09 | unique 1 | 1 | 按实际管理机构判定为内地居民的境外注册企业，同样就其境外所得享受直接与间接抵免 |
| D10 | unique 2 | 1 | 受控外国企业的低税测试按实际税负低于 25% 的一半；年度利润总额低于 500 万元可免；本层在模型各笔流之外的税额是数据，未知时实际税负只取下限，测试可能成立则待定 |
| D11 | unique 1 | 1 | 新加坡抵免池只收在所得来源地已缴外国税的境外所得：新加坡来源的所得不进池 |
| D12 | ambiguous 1, unique 1 | 1 | 支柱二收入门槛按最终母公司合并报表的集团收入判断：一个集团一个数，成员陈述不一致即为待问的冲突 |
| D13 | unique 4 | 2 | 新加坡国内补足税（DTT）按 MMT 法第 30 条套用第 16–21 条：补足税比例 = 最低税率 − 有效税率（第 16(5) 条），有效税率 = 调整后涵盖税额 ÷ GloBE 所得（第 17 条），超额利润 = GloBE 所得 − 基于实质的排除（第 18 条与附表二）；DTT 中 K（其他法域的合格国内补足税）为零；DTT 为位于新加坡的成员的补足额之和（第 29 条）。第 17 条按法域合计计算，引擎目前按单个成员计算（同一法域多个成员时有偏差，待办） |

## 约束（每次构建检查；Error 使构建失败）

| 约束 | 级别 | 内容 | 违反 | 示例 |
|---|---|---|---|---|
| E01 | Error | 引文（参数、缺口、口径）在所引条款里找不到原文 | 0 |  |
| E02 | Error | 已解析的关系指向不存在的条款 | 0 |  |
| E03 | Error | 规则层引用了库里没有的条款或参数 | 0 |  |
| E04 | Error | 已废止（removed.csv）的文件仍有条文留在库里 | 0 |  |
| E05 | Error | 口径没有被引擎代码引用（代码里写“口径 Dnn”） | 0 |  |
| E06 | Error | 引擎代码引用了 decisions.csv 里没有的口径 | 0 |  |
| E07 | Error | 口径所依条文已失效（valid_to 已过） | 0 |  |
| W01 | Warning | 引文在条款里出现不止一次（锚点取第一处） | 30 | param:sg.wht.interest @ sg.ita1947.full#s43; param:hk.fsie.participation_subject_to_tax @ hk.cap112.en#s15N; param:sg.so |
| W02 | Warning | 参数没有原文引语 | 1 | param:hk-sg.no_comprehensive_dta |
| W03 | Warning | 参数或口径所依条文有替换事件（superseded.csv），值需复核 | 0 |  |
| W04 | Warning | 显式交叉引用未能解析（保留原文，不猜） | 392 | treaty.cn-hk.2006.p2.zh#1 -> unresolved:取消《安排》第二条第三款; treaty.cn-hk.2006.p2.zh#2 -> unresolved:取消《安排》第四条第一款; treaty.cn-hk |
| W05 | Warning | 条款的生效日期未知 | 4638 | treaty.cn-hk.2006.zh#1; treaty.cn-hk.2006.zh#2.1; treaty.cn-hk.2006.zh#2.2; treaty.cn-hk.2006.zh#2.4; treaty.cn-hk.2006. |
| W06 | Warning | 复核下载与登记的哈希不一致（verify.csv）：来源页面可能已改 | 0 |  |

## 与上次构建对照

无变化。

## 检查

- 无 Error。
