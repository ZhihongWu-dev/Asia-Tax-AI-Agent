# official：官方资料库（v1：内地 / 香港 / 新加坡，公司）

只收国家与官方公开的法规、协定、公告、指引、表单和官方工具结果；只保留现行有效的内容；每个数字都带逐字原文引语并在构建时核对；库内没有任何生成的文字。案例事实与标准答案不在这里。

规模（2026-10-09）：文件 396 份（其中 70 份是分段下载的原件片），条款片 8,438 片（另有 317 片因被取代或废止而不保留），参数 390 个，口径 31 条，公式图片转写 15 条，表单栏位映射 458 条，字典缺口核证 73 条，假期日历 102 行；知识层有检索单元 34,299 个、关系 14,243 条（其中显式交叉引用 8,980 条，解析到条款 8,453 条）、定义词 4,719 个、引文锚点 608 个。当前清单见 [STATUS.md](STATUS.md)，知识层统计与构建检查见 [INDEX.md](INDEX.md)，检索评测见 [SEARCH_EVAL.md](SEARCH_EVAL.md)，待办见 [TODO.md](TODO.md)。

目录

1. 总览
2. 目录与文件
3. 构建
4. 标识
5. 登记表（CSV）
6. 数据库表（official.sqlite）
7. 图：关系的种类、抽取与原理
8. 时间与效力
9. 检索单元与索引
10. API
11. 质量约束与构建报告
12. 口径
13. 取件规则与站点经验
14. 检索评测
15. 已知局限
16. 参考文献

---

## 1. 总览

### 1.1 数据流

```text
官方网站 ──fetch.py──► raw/<jur>/<id>.<ext>  +  manifest_<jur>.csv          原件字节不改，记 sha256
                                │
                          build.py │ 转文本、按来源切条款、剔除废止占位与被取代的片、核对引语
                                ▼
               text/<id>.txt   clauses.csv   manifest.csv   STATUS.md
                                │
seed_params.py ──► params.csv   │   decisions.csv  gaps.csv  form_fields.csv  calendars/  labels/
                                ▼
                         official.sqlite：基础表 doc、clause、param、form_field、gap、calendar
                                │
                          graph.py │ 同一个库里加知识层：标识、检索单元、关系图、时间、锚点、口径、约束、向量
                                ▼
       search.py（检索 / 引文核对 / 影响分析 / 按日期取条文）   query.py（精确查）   INDEX.md
                                │
                                ▼
       引擎：tax_graph/params.py 读 params.csv；rules/compile.py 对照条款与参数编译规则；
             procedure_*.py 读 calendars/；planner.py 读 form_fields.csv；check_sg_s45 读 labels/
```

### 1.2 不变式

```text
只收官方      只从官方域名取件；拼装件与非原件（verbatim ≠ raw）在 manifest 里如实标注。
只留现行      全文废止或被取代的文件删除原件，只在 removed.csv 留元数据；部分被取代的，被取代的条、款、段、
              短语不进条款层（superseded.csv）；参数只保留现行版本。早于库内文本的日期回答 NotCovered，不拿现行文本代答。
数从原文来    params、gaps、decisions 的每一行带 cite_id 与原文引语，构建时逐字（忽略空白）核对；
              规则用到的数值型参数，其值还必须出现在引语里（rules/compile.py 编译时核对）。
无生成内容    条文、关系、定义词、摘要都由确定性规则从原文得出；未能确定的关系记为 unresolved，不猜。
              大模型若参与写规则或审阅，只能提出"候选条款 + 原文引语"，引语必须经 ground 逐字找到，最后仍由编译器核对。
```

---

## 2. 目录与文件

| 路径 | 内容 | 由谁写 | 谁读 |
|---|---|---|---|
| `raw/<jur>/` | 原件（html、pdf、doc、rtf、xls、ppt、json…），字节不改 | `fetch.py` | `build.py` |
| `manifest_<jur>.csv` | 每份文件一行元数据（§5.1），按法域分文件 | `fetch.py` | `build.py` |
| `manifest.csv` | 合并后的清单，加上转文本与切片结果列 | `build.py` | 入库为 `doc` 表；人工 |
| `text/` | 由原件抽出的纯文本；部分被取代的文件不留纯文本副本 | `build.py` | 人工、`check_form_fields` |
| `_conv/` | LibreOffice 转换缓存（按原件 sha256 前 16 位命名），可随时删 | `build.py` | `build.py` |
| `clauses.csv` | 条款层：每片一行 | `build.py` | `rules/compile.py`（无 sqlite 时） |
| `params.csv` | 参数层（§5.2） | `seed_params.py` | 引擎 `Params`、`build.py` 核对 |
| `decisions.csv` | 口径（§12） | 人工（逐字引语） | `graph.py` |
| `formulas.csv` | 法规在线把公式印成图片时，图片原件（`raw/sg/img/`，核对 sha256）与读出的公式（§5.10） | 人工（读官方图片） | `build.py` |
| `gaps.csv` | 字典缺口核证（§5.4） | 人工 | `build.py` |
| `form_fields.csv` | 官方表单栏位到字段字典的映射（§5.5） | 人工 | `build.py`、`planner.py` |
| `superseded.csv`、`removed.csv`、`currency.csv`、`repealed_stubs.csv` | 时效处理（§5.6） | 人工、`prune.py`、`build.py` | `build.py`、`graph.py` |
| `aliases.csv` | 法名别名（§5.7） | 人工 | `graph.py` |
| `verify.csv`、`blocked_<jur>.csv` | 复核下载结果、取不到的文件 | `verify.py`、`fetch.py --blocked` | `graph.py`、`build.py` |
| `calendars/` | 公众假期（§5.8） | `calendar_sg.py`、人工 | `build.py` 核对；引擎期限顺延 |
| `fx/` | 人民币汇率中间价缓存 | `fx_cny.py` | 引擎、人工 |
| `labels/` | 官方计算器结果与官方算例，以及只见于官方工具的规则（§5.9） | 人工 | `check_sg_s45`、`rules/compile.py` |
| `inbox/` | 待登记的来件（人工放入） | 人工 | 人工 |
| `official.sqlite` | 数据库（§6） | `build.py` + `graph.py` | `search.py`、`query.py`、`rules/compile.py` |
| `_index/` | 向量缓存 `vec_cache.sqlite`、所用向量模型 `dense_model.txt`、构建指标 `metrics.json` | `graph.py` | `graph.py` |
| `STATUS.md`、`INDEX.md`、`SEARCH_EVAL.md` | 生成的报告，不要手改 | `build.py`、`graph.py`、`eval_search.py` | 人工 |
| `tools/` | 全部脚本（§10.1） | — | — |

---

## 3. 构建

### 3.1 命令

在包含 `official/` 和 `tax_graph/` 的项目根目录执行以下命令，命令中的路径均相对于该目录。§2 的目录表和各节中的库内文件路径相对于 `official/`。不要求特定的本地 conda 环境；完整构建在 Python 3.9.23 下验证，引擎和案例在 Python 3.12.7 下验证，运行说明见 [tax_graph/README.md](../tax_graph/README.md)。

基础构建依赖安装命令为 `python -m pip install -r official/requirements.txt`。LibreOffice 用于未缓存的旧版 Office 文件转换，程序从 `PATH`、`SOFFICE` 环境变量或系统安装目录查找。重建缺失的稠密向量或运行稠密检索时，还需安装 `official/requirements-dense.txt` 中的依赖及对应模型。仅重建词面检索与关系图时可加 `--no-dense`，该方式不生成向量表；发布的数据库包含完整向量表。

```bash
python official/tools/fetch.py --id ... --jur ... --title ... --url ...   # 取件并登记（§10.1）
python official/tools/seed_params.py      # 参数有改动时
python official/tools/build.py            # 全量构建，最后自动运行 graph.py
python official/tools/graph.py [--dense[=MODEL]]   # 只重建知识层
```

`build.py` 删除并重建 `official.sqlite`，再调用 `graph.main()`。有错误时退出码非 0，问题列在输出与 `INDEX.md`"检查"一节。转换与向量都有缓存：没有新文件时全量构建约 30 秒；新加文件只转换、只向量化新的部分；首次为 29,640 个单元算 BGE-M3 向量在 GPU 上约 14 分钟。

### 3.2 build.py 的步骤

```text
1 合并清单      manifest_<jur>.csv → manifest.csv；核对原件存在且 sha256 一致；字节相同的文件只切第一份，其余记 alias_of
2 判类型        按文件头判断真实格式（real_kind），扩展名不可信
3 转文本        html：BeautifulSoup；pdf：PyMuPDF 逐页；docx、xlsx：直接读；doc、rtf、xls、ppt、pptx：LibreOffice
                无界面转换（缓存到 _conv/）；动态 PDF 表单：读内嵌的 XFA 模板（xfa_text.py）
4 切条款        按来源选切法（下表），每片一个 cite_id
5 剔除          香港电子版法例与新加坡法规在线的废止占位（如 "18A. [Repealed by Act 21 of 2003]"）移出条款层，
                列入 repealed_stubs.csv；重复 cite_id 只留第一片；按 superseded.csv 去掉被取代的片、行或短语
6 写出          manifest.csv、clauses.csv；部分被取代的文件不写纯文本
7 核对          params、gaps 的 cite_id 存在且引语逐字出现（忽略空白）；form_fields 的 label 逐字出现在表单文本；
                calendars 与 labels 中带 doc_id 的行，其引语逐字出现在来源网页
8 入库          official.sqlite 的基础表（§6.1）；生成 STATUS.md；调用 graph.py
```

| 切法 `slice_mode` | 用于 | 片号示例 | 份数 |
|---|---|---|---|
| `cn_article` | 内地法律、法规、协定中文本、附件里的办法（第 X 条，第 Y 款） | `#13`、`#13.2` | 32 |
| `cn_item` | 内地公告、通知（一、二、…） | `#i4` | 30 |
| `en_article` | 协定英文本（Article N，paragraph） | `#10.2` | 9 |
| `hk_section` | 香港电子版法例整章（section、Schedule） | `#s15K`、`#sch17FC` | 3 |
| `sso_section` | 新加坡法规在线（页面锚点 `pr…-`、`Sc…-`） | `#s50C`、`#sch2` | 27 |
| `numbered_para` | 指引、算例（1. / 5.3） | `#para12`、`#para5.3` | 15 |
| `html_section` | 网页小节 | `#h3` | 27 |
| `html_faq` | 问答页 | `#q7` | 4 |
| `xfa_subform` | 香港动态表单，按子表单 | 子表单名 | 4 |
| `page` | 只能切到页的 PDF（表单、国别指南、OECD 文件等） | `#p4` | 48 |
| `whole` | 无法再切 | `#all` | 47 |
| `skipped_part`、`alias` | 分片原件（由拼装文本 `<id>.full` 代表）、同字节别名：不单独切 | — | 75 |

### 3.3 graph.py 的步骤

```text
1 标识         work、expression（FRBR，§4.3），规范文本 canonical；alias（aliases.csv + 法规标题）
2 条款元数据   provision（与语言无关的条款）、clause_meta（层级路径、语言、文本哈希）
3 检索单元     unit + unit_fts（§9）
4 关系         contains、same_provision、文件间关系、显式交叉引用（§7.2）、参数 / 缺口 / 规则 / 口径的依赖边
5 定义词       term（§6.2）
6 时间         event、tombstone、clause_time（§8）
7 锚点与口径   anchor（参数、缺口、口径的引语 → 字符区间）；decision；decision_ref（扫描 tax_graph/ 代码中的"口径 Dnn"）；
               verify_result（读 verify.csv）
8 约束         CONSTRAINTS 逐条执行，结果写 constraint_result；Error 记入问题，构建失败（§11）
9 向量         --dense[=MODEL]：按文本哈希增量计算；不带参数时沿用 _index/dense_model.txt 记下的模型
10 报告        INDEX.md；_index/metrics.json 与上次比较
```

---

## 4. 标识

### 4.1 文件标识 doc id

```text
<jur>.<kind>.<key>[.<变体或语言>]
jur    cn | hk | sg | treaty | intl
例     cn.law.eit            企业所得税法            cn.reg.eit            企业所得税法实施条例
       cn.cs.2009-125        财税〔2009〕125号        cn.sta.2010-01.a01    国家税务总局公告 2010 年第 1 号的附件 1
       cn.gsf.2009-02        国税发〔2009〕2号        hk.cap112.en / .zh    税务条例（第 112 章）英 / 中文本
       hk.ord.2025-21        2025 年第 21 号修订条例   sg.ita1947.full       新加坡所得税法（拼装的全文）
       sg.memta2024.s16      新加坡最低税法第 16 条的单条款视图
       treaty.cn-hk.2006.zh  内地与香港安排中文本     treaty.cn-hk.2006.p2.zh   第二议定书
       treaty.cn-sg.2007.mli.zh   中新协定与 MLI 的整合文本        intl.oecd.mli.sg   OECD 文件
后缀   .zh / .en / .zh-hk 语言；.full / .consolidated / .sso / .pdf / .flk / .sh 同一作品的不同文本；.mli 整合文本；
       .s<N> / .sch<N> 单条款视图；.frag<NN> 分段下载的原件片；.a<NN> 附件
```

### 4.2 条款标识 cite_id

```text
cite_id = <doc id>#<片>
片     条款 #10.2；公告的项 #i4；条例的条 #s15K、条的款 #s15K(1)；附表 #sch8B；指引的段 #para12、#para5.3；
       网页小节 #h3；问答 #q7；页 #p4；随附议定书 #protocol.3；全文 #all
引用、参数、规则、口径都指向 cite_id；cite_id 在重建之间保持不变。
```

### 4.3 作品与文本（FRBR）

`graph.identity(doc_id) → (work_id, variant, part_of)`：去掉语言后缀、文本变体后缀、`.mli`、单条款视图后缀（协定与国际文件除外），剩下的就是作品 id。

```text
hk.cap112.en           → work hk.cap112，        variant ""
sg.ita1947.full        → work sg.ita1947，       variant full
sg.memta2024.s16       → work sg.memta2024，     variant view
treaty.cn-sg.2007.mli.zh → work treaty.cn-sg.2007，variant mli
sg.ita1947.frag03      → part_of sg.ita1947（原件片，不单独成为 expression 的内容）
```

- **canonical**：同一作品、同一语言里最完整的非派生文本。先比变体等级（原文 / full 0 < sso 1 < pdf 2 < consolidated 3 < flk、sh 4 < mli 5 < 单条款视图 6），再比条款片数。检索结果优先报规范文本，其余列为 `variants`。
- **provision**：`<work>#<片>`，与语言、文本无关；同一作品不同文本中片号相同的条款，是同一条款（§7.3）。

### 4.4 参数的作用域与主题

```text
scope  CN | HK | SG | pair(CN,HK) | pair(CN,SG) | pair(HK,SG)
topic  rate | condition | anti_abuse | procedure | limit
unit   数值型：% days months years tiers ratio CNY HKD SGD EUR persons；另有 bool、text（如年份表 "2023:10.0;2024:9.8"）
```

---

## 5. 登记表（CSV）

所有 CSV 为 UTF-8（带 BOM），逗号分隔，第一行是列名。

### 5.1 manifest_<jur>.csv / manifest.csv

| 列 | 含义 |
|---|---|
| `id`、`jur`、`type` | 文件标识；法域；类型 law / regulation / guidance / treaty / form / rates / example / guide / page / attachment |
| `title`、`doc_no`、`issuer` | 标题、文号、发布机关；页面上看不到的留空，不编造 |
| `issued`、`effective_from`、`effective_to` | 发布日、文件写明的生效日与失效日（没写就空） |
| `lang`、`url`、`file`、`ext`、`bytes`、`sha256`、`retrieved_at` | 语言、来源地址、本地路径、扩展名、字节数、哈希、取回时间 |
| `via` | 取法：curl、curl_cli、alt（替代地址）、webfetch_copy（经网页工具取得的副本）、assembled_local（本地拼装） |
| `verbatim` | raw（原件字节）、raw_not_reverified（经 curl 取得、尚未复核下载）、unverified（副本未复核）、derived_from_official_raw（由官方原件拼装） |
| `official_domain`、`parent`、`note`、`alias_of` | 是否官方域名、所属母文件、备注、同字节别名 |
| `real_kind`、`text_status`、`text_chars`、`slice_mode`、`clauses` | 仅 manifest.csv：真实格式、转文本状态、字符数、切法、片数 |
| `validity_label`、`currency`、`currency_note` | 仅 manifest.csv：内地政策法规库页面上的有效性标注；currency.csv 的时效标注 |

### 5.2 params.csv

| 列 | 含义与规则 |
|---|---|
| `param_id` | 如 `cn-hk.div.cap_qualified`、`sg.p2.sbie_payroll_transition` |
| `scope`、`income`、`topic`、`name` | 作用域（§4.4）、所得类型或 ALL、主题、英文短名 |
| `value`、`unit` | 值与单位；数值型的值必须出现在 `quote` 里（编译器核对，含中文数字、"500万"、"$2,000,000" 等写法） |
| `cite_id`、`quote` | 所依条款与逐字引语（忽略空白）；构建时核对 |
| `effective_from`、`effective_to` | 生效区间；规则的有效期取它所读参数区间的交集 |
| `status` | `extracted`：由原文抄出并经引语核对 |
| `cross_check`、`note` | 与官方汇总表的交叉核对（只核对，不作来源）、备注 |

新增参数在 `tools/seed_params.py` 里加一行 `p(...)`，再运行它与 `build.py`。

### 5.3 decisions.csv

`id, seq, statement, cite_id, quote, used_in`：一条口径可有多处锚点（多行，同 id、不同 seq；陈述与使用处只写在 seq 1）。详见 §12。

### 5.4 gaps.csv

`new_id, verdict, cite_id, quote, finding, dictionary_change`：表单映射提出的字典缺口逐项对到条文。`verdict` 取 law / derived / form_only / law_scope / v2 / admin / out；引语按参数的规则核对。

### 5.5 form_fields.csv

`form_id, seq, section, label, maps_to, kind, note`：官方表单的栏位逐项对应到字段字典的字段 id；`label` 必须逐字出现在表单文本里。

### 5.6 时效处理

| 文件 | 列 | 作用 |
|---|---|---|
| `removed.csv` | `id, title, reason, removed_at` | 全文废止或被取代、已删除的文件（`prune.py` 写）；成为 tombstone |
| `superseded.csv` | `doc_id, clause, by, since, note, phrase` | 部分被取代：`clause` 可为片号（`13.4`）、前缀（`24*`）、行区间（`i8@2`、`13.5@4-`）或整份（`*`）；`phrase` 只删一句；成为 event（substitution / repeal） |
| `currency.csv` | `id, currency, note` | 未废止但偏旧或适用受限的文件 |
| `repealed_stubs.csv` | `cite_id, text` | 构建时剔除的废止占位（自动生成） |

### 5.10 formulas.csv

新加坡法规在线把部分公式印成 GIF 图片（如最低税法第 16(2) 条 A × B / C、第 17(1) 条 A / B × 100%），抽文本时图片会丢。每张图片一行：`image, doc_ids, where, url, file, sha256, bytes, fetched_at, transcription, read_on, note`。原件存 `raw/sg/img/<image>.gif`，构建时像清单文件一样核对存在与 sha256；切条款时（`slice_sso`）图片原位替换为 `[formula: <transcription>]`，口径与参数可以逐字引用它。没有登记的图片替换为 `[formula image <id>: not transcribed]`，由约束 W07 报出——该处公式在文本层缺失，不得据此推算。已登记 15 张：最低税法第 8、15、16、17 条，最低税条例第 94 条，所得税法第 10、10L、14 条（规则层引用的条文里的全部公式）；其余 58 处（主要是印花税法附表一的税率分数）未读。

### 5.7 aliases.csv

`alias, work_id, lang, note`：法名别名，如"企业所得税法""征管法实施细则""IRO""ITA""中新税收协定"→ 作品 id。另由法规标题自动生成别名（全名、去掉"中华人民共和国"、"Cap. 112"）。交叉引用解析与精确检索都用它。

### 5.8 calendars/ 与 fx/

| 文件 | 列 | 覆盖 |
|---|---|---|
| `calendars/cn_public_holidays.csv` | `date, kind, name, doc_id, quote` | 2025–2026；`kind` 为 holiday 或调休上班日；来源为国务院办公厅年度通知 |
| `calendars/sg_public_holidays.csv` | `date, weekday, name, doc_id, quote` | 2025–2027；来源为新加坡人力部页面 |
| `fx/cny_central_parity.csv` | `date, pair, rate, source_url, retrieved_at` | 按需取；空值表示当日未发布 |

日历不覆盖的年份，引擎不假设，期限记为缺口并在官方公布后向人索取。

### 5.9 labels/

| 文件 | 内容 |
|---|---|
| `sg_s45/`、`sg_s45_labels.csv` | 用户在新加坡税务局 S45 计算器上人工查得的结果（计算器有人机验证，程序不调用）；`verdict` 列记对答结论 |
| `sg_iras_wht_examples.csv` | 新加坡税务局网页上的官方算例 |
| `observed_rules.csv` | 只见于官方工具输出、找不到公开条文的规则（如周六顺延）；进规则层时为 B 级，不进参数表 |

标签是对答案的用例，不是参数来源。

---

## 6. 数据库表（official.sqlite）

### 6.1 基础表（build.py；全部列为 TEXT）

| 表 | 列 | 说明 |
|---|---|---|
| `doc` | manifest.csv 的全部列 | 一份文件一行 |
| `clause` | `cite_id, doc_id, kind, label, parent, chars, text` | 条款层；`kind` 为 article、section、paragraph、item、schedule、protocol、qa、subform、page、front、whole；`parent` 为上级片 |
| `param` | params.csv 的全部列 | — |
| `form_field` | form_fields.csv 的全部列 | 只收仍在库内的表单 |
| `gap` | gaps.csv 的全部列 | — |
| `calendar` | 日历各列 + `calendar` | 两地日历合在一张表 |

### 6.2 知识层（graph.py）

| 表 | 主要列 | 说明 |
|---|---|---|
| `work` | `work_id, jur, type, title` | 作品 |
| `expression` | `expr_id, work_id, lang, variant, canonical, part_of, alias_of, valid_from, valid_to, sha256, status` | 一种语言或一种文本；`expr_id` 即 doc id |
| `provision` | `provision_id, work_id, fragment, n_expr` | 与语言无关的条款 |
| `clause_meta` | `cite_id, expr_id, provision_id, depth, path, lang, sha1` | 条款片的层级路径（如"附表 2 > 第 1 段"）与文本哈希 |
| `clause_time` | `cite_id, valid_from, valid_to, basis, efficacy_from, efficacy_note` | 效力（§8）；`basis` 为 expression、superseded.csv 或 unknown |
| `unit` | `unit_id, cite_id, seq, start, end, kind, lang, header, sha1, extractor` | 检索单元：条款文本的字符区间 [start, end) |
| `unit_fts` | `header, body` | FTS5 全文索引（§9） |
| `unit_vec` | `unit_id, model, vec` | 可选的句向量（float32） |
| `edge` | `src, dst, kind, status, evidence, src_start, src_end, rule, extractor` | 关系（§7）；`evidence` 为匹配到的原文，`rule` 为抽取规则 |
| `term` | `term, lang, equiv, cite_id, start, end, rule` | 定义词与法例自己印出的另一语言对应词 |
| `event` | `kind, target, by, since, note, source` | 替换、废止事件（只留元数据） |
| `tombstone` | `id, title, reason, removed_at, ends, replaced_by` | 已删除的文件 |
| `anchor` | `owner, cite_id, start, end, occurrences, status` | 引语在条款里的区间；`status` 为 unique、ambiguous、missing、no_quote |
| `alias` | `alias, work_id, lang, source` | 法名别名 |
| `decision` | `id, seq, statement, cite_id, quote, used_in` | 口径 |
| `decision_ref` | `id, location` | 代码中"口径 Dnn"的位置（文件:行） |
| `verify_result` | `id, match, checked_at` | 复核下载结果 |
| `constraint_result` | `id, severity, description, violations, sample` | 本次构建的约束检查结果 |

`extractor` 列记下产生该行的抽取器版本（如 `graph.py/2026-10-08`），抽取规则改动时提升版本号。

---

## 7. 图：关系的种类、抽取与原理

### 7.1 节点与边

节点是条款片（`cite_id`）、文件（`doc:<id>`）、作品（`work:<id>`），以及参数、缺口、规则、口径（`param:`、`gap:`、`rule:`、`decision:`）。边全部有类型、来源与证据，只走显式依据，不建由模型推断的边。

| kind | 方向 | 来源 | status |
|---|---|---|---|
| `contains` | 上级片 → 下级片 | 切片时的层级 | resolved |
| `cites` | 引用方条款 → 被引条款 | 显式交叉引用（§7.2） | resolved / ancestor / unresolved |
| `cites_act` | 条款 → `work:` | 只点名了法、没有条号，或点名的法不在库内 | act_only / unresolved |
| `same_provision` | 条款 ↔ 条款 | 同一作品、同一片号的不同文本（§7.3） | resolved |
| `amends`、`substitutes`、`attachment_of`、`interprets`、`part_of`、`same_manifestation` | 文件或作品之间 | 议定书修订协定、superseded.csv 的替换、附件、解释文件、原件片、同字节别名 | resolved |
| `param_cites`、`gap_cites`、`decision_cites` | 参数 / 缺口 / 口径 → 条款 | 各登记表的 cite_id | resolved |
| `rule_cites`、`rule_uses_param` | 规则 → 条款 / 参数 | 编译后的规则层（`tax_graph.rules.spec`） | resolved / unresolved |

当前统计（INDEX.md）：cites 8,563 条，其中 resolved 5,765、ancestor 2,406、unresolved 392；same_provision 2,325；contains 851；cites_act 624。

### 7.2 显式交叉引用的检测与解析

检测与解析分开做，按规则族记录（I15 的做法）。检测用确定性正则，解析按文件结构。

```text
检测（每种语言一组规则族）
  中文   [《法名》|本法|本条例|本细则|本办法|本规定|本公告|本通知|本协定|本安排|本议定书] 第X条 [第Y款] [第（Z）项]
  英文   section(s) / s. / ss. N[(a)(i)] [, and, or, to M …] [of the <Act / Ordinance / Regulations>]
         Schedule N / First … Tenth Schedule
  协定   Article N[(p)] / paragraph p of Article N
排除     条标题自身（"第十三条 财产收益"）；修订注记（"(Added 4 of 1998 s. 6)" 指修订条例的条）；
         "of this Schedule / Part / Protocol …" 指别的单位；他法的条（"Article 5 of the Convention"）
解析目标作品，依次
  1 点名的法：别名表、文件自定义的简称（"以下简称《通知》"、("SFO")）、Cap. 号
  2 "本法 / 本条例 …"：本作品；条约解释通知里的"本协定 / 协定第X条 / 本议定书"：标题所解释的那份条约或议定书
  3 法名紧接在"第X条"之前（"实施条例第三十八条"）：由近及远取最长的已知名称；未知法名记为 unresolved，绝不当作本法
  4 无点名：本作品若按条切片，指本作品；指引类文本若点名了默认法（如香港"Inland Revenue Ordinance"），指该法
解析目标条款
  在目标作品的、同语言且含该片的文本里，按"最具体在前"找片号：款 → 条；只找到上级片时记 ancestor；
  找不到记 unresolved，保留原文证据，不猜
```

抽查（人工逐条判断）：四轮修正后，均匀抽 100 条已解析引用，98 条正确；两处错误（修订条例注记、缩写指称的外部条例）已改规则并复跑。未解析的大头是库外的法（Insurance Act、Companies Act、Securities and Futures Ordinance 等）。分轮的错误类型见 [literature/notes/I_综合.md](../literature/notes/I_综合.md) 第 3 节。

### 7.3 跨语言的同一条款

条款号本身就是对应关系：同一作品的不同文本（中英文本、整合文本、单条款视图与全文）中片号相同的条款，属于同一个 `provision`，两两以 `same_provision` 相连。跨语言检索因此不依赖词面相似，而依赖这一显式对应（I4 指出跨语言时稀疏通道无效；I17、I19 的作品 / 文本分离）。

### 7.4 图在检索中的用法：个性化 PageRank

检索先由 BM25 与向量两个通道各给出排名，融合后取前 10 个（满足法域、语言、日期过滤的）条款作为种子，在显式边上做个性化 PageRank（PPR），把与种子结构上相关、但词面不像的条款带进来，作为第三个通道（"graph"）参与融合。

```text
子图     种子出发两跳；只用 contains、cites、same_provision、substitutes，且 status 为 resolved 或 ancestor；
         边按无向处理（被谁引用与引用了谁同样重要）
个性化   p(s) ∝ 1 / rank(s)，s 为种子
迭代     π = α · W π + (1 − α) · p，α = 0.5（W 为按出度归一的转移矩阵；networkx.pagerank 的阻尼 alpha）
         α 取 0.5：每步有一半概率回到种子，质量集中在种子附近，避免流向图中枢
特异性   score(c) = π(c) / sqrt(1 + indeg(c))：被大量条款引用的"枢纽"条款（如释义条）降权（仿 I12 的节点特异性）
输出     去掉种子后的前 50 个，按 score 排名，作为 graph 通道的名次
```

为什么只走显式边：由大模型抽取的实体图覆盖不全（约 65% 的答案实体）、构建昂贵，且边不是官方原文、无法逐条核对（I13、I11）；PPR 与节点特异性这两项确定性做法来自 I12。评测中加图扩展使开发集 R@10 从 0.353 升到 0.377，跨语言集 R@10 从 0.717 升到 0.825（§14）。

### 7.5 影响分析：依赖边上的反向可达

`impact(cite_id)` 回答"这一条改了，什么会受影响"：从该条款及其所含下级片出发，沿依赖边反向查找。

```text
参数     param_cites 指向这些片的参数
规则     rule_cites 指向这些片的规则，以及 rule_uses_param 读取上述参数的规则
缺口     gap_cites           口径     decision_cites
被引     cites（谁引用了它）  同一条款 same_provision（其他语言与文本）
```

思想来自溯源半环（I16）：派生结果带着其来源，删去或改动一个来源即可定位须重算的结果。条款被议定书替换时，W03 约束会列出依据它的参数与口径（§11）。

### 7.6 图上的约束

关系图本身受构建约束检查：已解析的边不得指向不存在的条款（E02），规则层的引用必须在库内（E03），口径的锚点必须找到、且被代码引用（E01、E05、E06），依据有替换事件的参数与口径列出复核（W03）。见 §11。

---

## 8. 时间与效力

```text
expression.valid_from / valid_to   只取文件写明的生效日与失效日；没写的是 unknown，不拿签署日或发布日代替
clause_time.valid_from             expression 的生效日；被议定书替换进来的款，取 superseded.csv 的 since
                                   （basis：expression / superseded.csv / unknown）
efficacy_from / efficacy_note      "适用于哪些纳税期间"与"何时在效"是两种时间（I17）；文件写明时才填
event / tombstone                  替换、废止、删除只留元数据：谁、何时、被谁取代；不留旧条文
```

按日期回答（`at`、`search(as_of=...)`）：

| 情形 | 回答 |
|---|---|
| 该日在 [valid_from, valid_to) 内 | 条款 |
| 文件没写生效日 | `NotCovered("validity unknown …")`，即待定，不当作有效 |
| 该日早于库内文本的生效日 | `NotCovered("the library holds this provision only from …")`，不拿现行文本代答（I20） |
| 条款不在库内 | `NotCovered("provision not in the library …")`，附 tombstone 与 event |
| 查询点名了已删除的文件 | `removed()` 给出"已删除、原因、被谁取代"（I14、I20 的错误前提防护） |

现状：4,638 片条款的生效日期未知（W05），主要是协定与没有写明生效日的文件；这些条款在按日期检索时一律答"效力未知"。

---

## 9. 检索单元与索引

### 9.1 检索单元 unit

条款片过长时切成原文区间，不改写文字（I5 的粒度结论，I21 的约 100 词便于核对）：

```text
上限      中文 260 字、其他 700 字符（约 100 个英文词）；条款不超过上限的 1.4 倍时整片为一个单元（kind = clause）
切点      先按法条自身结构：(1)、(a)、(i)、（一）、一、、第X条 / 款 / 项、1.2、a)、Article N；
          块仍过长再按句末（。；;！？!? 与英文句点后大写）；相邻小块合并到上限以内；仍超 1.5 倍上限的硬切
检索字段  header = "文件标题 > 层级路径"，只作检索字段，不作引文；引用与核对仍以条款片为准
```

现有 clause 单元 3,599 个（平均 287 字符），part 单元 26,041 个（平均 441 字符）。

### 9.2 全文索引（BM25）

SQLite FTS5，`unit_fts(header, body)`，分词器 `porter unicode61 remove_diacritics 2`。中文按字二元组写入（"受益所有人" → 受益 益所 所有 有人），英文按词并做词干化。查询时把词元用 OR 连接，按 `bm25(unit_fts, 0.4, 1.0)` 排序（标题权重 0.4、正文 1.0）。零样本下 BM25 是强基线，同语言内可靠（I1、I6、I9）。

### 9.3 句向量（可选）

`graph.py --dense[=MODEL]` 为每个单元算归一化句向量（默认 BAAI/bge-m3，I4），存 `unit_vec`；缓存键为 sha1(模型名 + 标题 + 文本)，存在 `_index/vec_cache.sqlite`，重建只算新单元。查询时用余弦（点积）暴力取前 n 个（3 万个单元无需近似索引）。查询端设置 `HF_HUB_OFFLINE`，不做联网检查；向量运算用 torch（本环境里导入 torch 后 numpy 的矩阵乘会崩溃）。

---

## 10. API

### 10.1 命令行

| 命令 | 作用 |
|---|---|
| `tools/fetch.py --id ID --jur cn\|hk\|sg\|treaty\|intl --type T --title ... --url URL [--doc-no] [--issuer] [--issued] [--effective] [--effective-to] [--lang] [--with-attachments] [--engine requests\|curl] [--insecure] [--pace S] [--min-bytes N] [--force]` | 下载一份文件并登记：1 次尝试 + 2 次重试，成功退出码 0，失败 2 |
| `tools/fetch.py --register-file PATH --id ... --jur ... --type ... --title ... --url ... [--via ...] [--note ...]` | 登记一份已在本地的副本（照记 sha256） |
| `tools/fetch.py --blocked --id ... --jur ... --title ... --url ... --reason ... [--alt-tried ...]` | 记一份取不到的文件到 `blocked_<jur>.csv` |
| `tools/verify.py [--sleep 3] [--retry]` | 重新下载副本并比对 sha256，写 `verify.csv` |
| `tools/prune.py --reason "..." [--with-children] ID ...` | 删除已废止或被取代的文件，写 `removed.csv` |
| `tools/seed_params.py` | 写 `params.csv` |
| `tools/build.py [--dense]` | 全量构建（§3.2），最后运行 graph.py |
| `tools/graph.py [--dense[=MODEL]]` | 只重建知识层（§3.3） |
| `tools/query.py source CITE_ID` | 按 cite_id 取条文 |
| `tools/query.py cell SCOPE INCOME [TOPIC] [--on YYYY-MM-DD]` | 按格子取参数（可只取某日已生效的） |
| `tools/query.py doc DOC_ID` | 一份文件的元数据与各类条款片的片数 |
| `tools/query.py find TEXT [--doc DOC_ID]` | 子串查找（不是相似度检索） |
| `tools/search.py q "QUERY" [--k 10] [--jur CN] [--lang zh] [--as-of DATE] [--channels exact,bm25,dense,graph]` | 混合检索（§10.2） |
| `tools/search.py ground "QUOTE" CITE_ID` | 引语是否逐字出现在条款里 |
| `tools/search.py impact CITE_ID` | 影响分析 |
| `tools/search.py at PROVISION_OR_CITE DATE` | 该日有效的条文 |
| `tools/eval_search.py [--configs ...] [--out FILE]` | 检索评测，写 `SEARCH_EVAL.md` |
| `tools/fx_cny.py DATE CUR ...` | 人民币汇率中间价（取并缓存） |
| `tools/calendar_sg.py` | 由人力部页面生成新加坡假期表 |
| `tools/sso_whole.py DOC_ID URL TITLE TYPE` | 下载新加坡法规在线上分段加载的法规并拼装；整页被拒（HTTP 202 / 503）时改取单条款视图（§13） |
| `tools/xfa_text.py PDF` | 动态 PDF 表单的 XFA 模板文字 |

示例：

```bash
python official/tools/search.py q "受益所有人 判定" --k 5 --jur CN
python official/tools/search.py ground "应当缴纳并已实际缴纳的企业所得税性质的税款" "cn.cs.2009-125#i4"
python official/tools/search.py impact "cn.cs.2009-125#i5"
python official/tools/search.py at "sg.memta2024.s16#s16" 2026-06-30
```

### 10.2 Python：`search.Library`

```python
import sys; sys.path.insert(0, "official/tools")
from search import Library
lib = Library()                       # 打开 official/official.sqlite
```

| 方法 | 返回 | 说明 |
|---|---|---|
| `search(query, k=10, jur=None, lang=None, as_of=None, channels=("exact","bm25","dense","graph"), weights=None, balanced=True, today=None)` | `List[Hit]` 或 `NotCovered` | 混合检索；`as_of` 过滤掉该日已知不在效的条款，全部被滤掉时返回 NotCovered |
| `ground(quote, cite_id)` | `{"ok", "cite_id", "start", "end", "occurrences", "text"}`；条款不存在时 `{"ok": False, "reason"}` | 引语核对（忽略空白的逐字匹配） |
| `impact(cite_id)` | `{"cite_id", "params", "rules", "gaps", "decisions", "cited_by", "same_provision"}` | 影响分析（§7.5） |
| `at(provision_or_cite, date)` | `List[cite_id]` 或 `NotCovered` | 按日期取条文（§8） |
| `removed(query)` | `List[Removed]` | 查询点名的已删除文件 |
| `exact(query)` | `List[cite_id]` | 精确通道：cite_id、参数 id、"section 15 IRO"、"企业所得税法第三条" |
| `bm25(query, n=200)`、`dense(query, n=200)` | 单元行 | 两个检索通道 |
| `expand(seeds, n=50)` | `List[cite_id]` | 图通道（§7.4） |

返回的数据类：

```text
Hit         cite_id, provision_id, expr_id, lang, title, score, channels{通道: 名次}, span(start, end), snippet,
            valid_from, valid_to, variants[同一条款同一语言的其他文本], other_lang[同一条款的其他语言],
            validity: 带 as_of 时 valid | unknown；否则 not yet in force | not asked
NotCovered  reason, detail[]
Removed     id, title, reason, ends, replaced_by
```

融合算法：

```text
倒数排名融合（RRF，I2）   score(d) = Σ_通道 w_通道 / (60 + rank_通道(d))
                          默认权重 exact 1.0、bm25 1.0、dense 1.0、graph 0.5（只在开发集 params 上选定）
语言均衡（balanced=True）  同语言候选按上式排序；跨语言候选只计 dense 与 graph 的贡献（BM25 跨语言无效，I4），
                          两组交替排列、同语言在先
精确命中                  直接排在最前，不参与融合
去重                      同一条款同一语言只报一次，规范文本优先，其余进 variants
```

### 10.3 Python：`graph` 的可复用函数

| 函数 | 作用 |
|---|---|
| `anchor(text, quote) → (start, end, n)` | 忽略空白的逐字定位；n 为出现次数 |
| `identity(doc_id) → (work_id, variant, part_of)` | FRBR 拆分（§4.3） |
| `split_units(text, lang) → [(start, end, kind)]` | 检索单元切分（§9.1） |
| `fts_tokens(text)`、`lang_of(text)` | 中文二元组分词；语言判断（前 2,000 字中汉字超过 20% 为 zh） |
| `CONSTRAINTS` | 约束清单（§11），每项为 (id, 级别, 内容, SQL) |
| `build(dense=None)`、`main(argv)` | 重建知识层 |

### 10.4 其他

`fx_cny.rate(date, "HKD")` → 每 1 外币的人民币中间价（float），当日未发布返回 None。法律规定了用哪一天的中间价（`cn.sta.2017-37#i4`：扣缴义务发生之日；`cn.sta.2025-18#i6`：再投资支付日），所以汇率是参考数据，不是案例输入。

### 10.5 引擎从库里读什么

| 引擎模块 | 读 | 用途 |
|---|---|---|
| `tax_graph/params.py`（`Params`） | `params.csv` | 一切数值；`Params.token` 为文件哈希，用作缓存键 |
| `tax_graph/rules/compile.py` | `official.sqlite` 的条款 id（无库时读 `clauses.csv`）、`labels/observed_rules.csv` | 规则编译时核对参数、条款、观察规则是否存在；求值器登记表所引条款是否在库内 |
| `tax_graph/rules/procedure_cn.py`、`procedure_sg.py` | `calendars/` | 期限遇假期顺延；缺年份记缺口 |
| `tax_graph/planner.py` | `form_fields.csv` | 问题单里注明哪张官方表单问这个字段 |
| `tax_graph/check_sg_s45.py` | `labels/` | 官方计算器与算例对答 |
| 反向：`graph.py` | `tax_graph.rules.spec`、`tax_graph/**/*.py` | 生成规则依赖边；收集代码中的"口径 Dnn" |

---

## 11. 质量约束与构建报告

每次构建执行声明式约束（J10 的做法：约束写成查询，带严重程度，每次构建都跑、结果可比）。Error 使构建失败，Warning 只报告。当前结果：

| 约束 | 级别 | 内容 | 违反 |
|---|---|---|---|
| E01 | Error | 引语（参数、缺口、口径）在所引条款里找不到 | 0 |
| E02 | Error | 已解析的关系指向不存在的条款 | 0 |
| E03 | Error | 规则层引用了库里没有的条款或参数 | 0 |
| E04 | Error | 已删除（removed.csv）的文件仍有条文留在库里 | 0 |
| E05 | Error | 口径没有被引擎代码引用 | 0 |
| E06 | Error | 引擎代码引用了不存在的口径 | 0 |
| E07 | Error | 口径所依条文已失效 | 0 |
| W01 | Warning | 引语在条款里出现不止一次（锚点取第一处） | 32 |
| W02 | Warning | 参数没有原文引语 | 1 |
| W03 | Warning | 参数或口径所依条文有替换事件，值需复核 | 0 |
| W04 | Warning | 显式交叉引用未能解析 | 521 |
| W05 | Warning | 条款的生效日期未知 | 4,801 |
| W06 | Warning | 复核下载与登记的哈希不一致 | 0 |
| W07 | Warning | 条款里有未转写的公式图片（formulas.csv 未登记） | 58 |

报告：`STATUS.md`（文件清单、切法、片数、未取到的文件）；`INDEX.md`（各表行数、关系统计、交叉引用解析、检索单元、锚点、定义词、口径、约束、与上次构建相比变了的指标、检查结论）。指标存在 `_index/metrics.json`，下一次构建与之比较。

---

## 12. 口径

口径是引擎依赖的、对条文的解读，每条登记在 `decisions.csv`，带所依条款与逐字引语；引擎代码在用到处写"口径 Dnn"。构建时双向核对：口径必须被代码引用（E05），代码不得引用不存在的口径（E06），锚点必须找到（E01），所依条文不得失效（E07）。

| 口径 | 内容 |
|---|---|
| D01 | 可抵免的外国税只是应缴且已缴的部分，取 min（实缴，应缴） |
| D02 | 新加坡补足税不受所得税法第 14 部分的抵免 |
| D03 | 已结税项：对它有利的一端反转为使应缴额更高的一端 |
| D04 | 间接抵免中本层税额是其自己抵免之后的实缴数 |
| D05 | 间接抵免逐层、最多五层、单一上层直接 ≥20% 且合计 ≥20% |
| D06 | 本层税额含其收款被扣缴的税与间接负担的下层税 |
| D07 | 股息负担的是所分配利润所属年度的税 |
| D08 | 间接抵免只对外国企业的境外来源股息 |
| D09 | 按实际管理机构判定的内地居民同样享受抵免 |
| D10 | 受控外国企业低税测试与 500 万元豁免；模型外税额是数据 |
| D11 | 新加坡抵免池不收新加坡来源所得 |
| D12 | 支柱二收入门槛按最终母公司合并报表的集团收入 |
| D13 | 新加坡国内补足税按最低税法第 16–18、29、30 条计算，其中 K 为零 |
| D14 | 支柱二按法域合计：同一法域全部成员合并算有效税率与超额利润，补足额按正所得占比分给成员（A × B / C） |
| D15 | 追加当期补足额（新加坡第 21 条、香港第 4.1.5 条）及其分配；新加坡第 21(2) 条选择；亏损追溯归属额是数据 |
| D16 | 支柱二逐财年；被排除股息与股权损益及其上的税不计入；方案新设公司的 GloBE 所得由其流算出 |
| D17 | 过渡期国别报告安全港与微利豁免：合格且选择时该法域该年补足额为零 |
| D18 | 重组步骤：插入新设 HOLD 时 ULT 把 OP 股权转给它；内地特殊性税务处理（递延 / 十年计入 / 转让前利润股息无协定优惠）、港新印花税减免、此后的内地计税基础 |
| D19 | 现有公司离开结构：不能迁出注册地（港新只设迁入、内地无迁册），由新公司承接；撤销或迁出现有 HOLD 时按市值转出 OP 股权再清算；注销的股份不征印花税；方案自身后续转让造成的减免撤回与承诺落空是事实；IP 换持有人未建模、不作为方案 |
| D20 | 收入纳入规则：港新母公司（OECD 名录列为合格 IIR）对内地成员按母公司所在地规则合并计算补足额，按持股链比例缴纳；港新成员由合格国内补足税覆盖；UTPR 未建模 |

完整陈述见 `decisions.csv` 与 INDEX.md。

---

## 13. 取件规则与站点经验

```text
1 只从官方域名取。
2 每个地址：1 次尝试 + 2 次重试；仍失败换一个官方地址或换取数方式再试 1 次；还失败记入 blocked_<jur>.csv，汇总报告。
3 不编造：页面上看不到的文号、日期留空。
4 官方汇总表只用于交叉核对（params.cross_check），不作为参数来源。
5 时效：见 §1.2"只留现行"与 §5.6。
```

| 站点 | 经验 |
|---|---|
| 国家税务总局（www.chinatax.gov.cn、fgk.chinatax.gov.cn） | CDN 对 python-requests 返回约 400 字节的验证脚本（设 `C3VK` cookie）：用 `--engine curl`，fetch.py 会带 cookie 重试一次；请求要放慢。"相关文件"框由 POST `queryManuscriptAssociation`（参数 `id` = 页面 articleId）返回；财税文件页面无有效性标注 |
| 全国人大法律库 | `curl -k` 可取 PDF（fetch.py 的 curl 引擎在该站 TLS 失败） |
| 香港电子版法例 | 整章以 `!en.rtf` 提供，不是 PDF；动态表单的文字在 XFA 模板里 |
| 新加坡法规在线（sso.agc.gov.sg） | 整部法规的正文分段懒加载，整页常返回 HTTP 202 / 503；单条款视图 `https://sso.agc.gov.sg/Act/<ID>?ProvIds=pr<N>-`（附表用 `Sc<N>-`）可由 curl 直接取得，登记为 `<work>.s<N>` / `<work>.sch<N>` |
| 新加坡税务局 S45 计算器 | 有人机验证，程序不调用；由用户人工查询后把结果放入 labels/ |
| 中国外汇交易中心 | 历史中间价接口对 curl 返回 JSON，每页最多 10 条 |

---

## 14. 检索评测

金标准取自本项目建库时自己追溯过的引用（参数、规则裁量项、字典缺口各自所引的条款；协定同一条款的中英文对照）；命中按条款计（本条、同一条款的其他文本、本条所含的款都算）；确定性评分，不用模型评判。权重只在 params（开发集）上选，rules、gaps、xlang 为测试集。查询是简短标识、每条只有一两个标注条款，未标注的相关条款计为未命中，所以绝对数偏低（I1、I3）。

| 配置（向量模型 BGE-M3） | params R@10 / R@50 | 其中中文金标 R@10 | gaps R@10 | xlang R@10 |
|---|---|---|---|---|
| BM25 | 0.187 / 0.367 | 0.032 | 0.123 | 0.354 |
| 稠密 | 0.327 / 0.527 | 0.227 | 0.185 | 0.467 |
| 等权融合（稠密权重 0.5） | 0.240 / 0.393 | 0.039 | 0.169 | 0.367 |
| 语言均衡融合 | 0.353 / 0.593 | 0.318 | 0.246 | 0.717 |
| 语言均衡 + 图扩展（默认） | 0.377 / 0.613 | 0.299 | 0.246 | 0.825 |

结论：同语言内词面检索可靠；跨语言靠显式条款对应与稠密向量；等权融合会把跨语言候选压到同语言词面候选之后，语言均衡是必要的；规则裁量项名是自造的英文词，检索弱（R@10 ≤ 0.13），这类查询走精确通道。完整表格见 SEARCH_EVAL.md（另有 MiniLM 小模型的对照 `SEARCH_EVAL_minilm.md`）。

---

## 15. 已知局限

- 参数的 `status` 全部是 `extracted`：由程序读原文抄出并经引语核对；正确性靠官方原文与证据链判定，没有外部专家复核。
- 只保留现行文本：事件日期早于参数或条文生效日的事后案例无法计算（回答 NotCovered）。
- 4,801 片条款的生效日期未知（W05，新增的 OECD 释义各片未标日期）；521 条交叉引用未能解析（W04，多为库外的法，如香港公司条例第 622 章）；32 处引语在条款中出现不止一次（W01）；1 个参数没有引语（W02：`hk-sg.no_comprehensive_dta`，"港新没有全面性协定"是一个否定事实，无原文可引）。
- 按项编号的通知（"一、二、"切成 `#iN`）被他文以"第 X 条"引用时，只能解析到文件或未解析。
- 假期日历只到内地 2025–2026、新加坡 2025–2027；之后年份要等官方公布。
- 表单、两册国别指南、OECD 文件、少数指引仍只切到页。
- 香港四份动态表单的文字取自内嵌 XFA 模板：栏位名、静态文字、下拉选项可靠，模板里的提示语多为复制粘贴，不可当作栏位标题。
- 新加坡税务局没有静态的协定税率表，计算器有人机验证，所以中新协定参数没有官方汇总表可交叉核对。
- 被部分取代的原件里仍含旧条文，这是官方文件本身，不能改；引擎只读条款层和参数层。
- 新加坡最低税法只按单条款视图收了计算所需的条文（s2、s5、s7、s8、s9、s15–s21、s27–s30、附表一、附表二）；登记、申报、罚则等部分未收，整部法的整页加载仍被拒（blocked_sg.csv）。《最低税条例 2024》（S 1062/2024，2025-12-31 版）整页分段加载在第 5 段超时，改取单条款视图第 2、3、8、9、48、49、65–77、94、95 条，另收 SSO 的 PDF 全文（按页切，`sg.memta2024.regs.pdf`）。
- 香港把欧元门槛折算成其他币种的口径在 OECD 释义中，未入库；安全港与微利豁免的欧元比较用集团提供的折算率。
- 印花税法附表一等 58 处公式图片未转写（W07）。

---

## 16. 参考文献

知识层的设计逐项对应到这些文献；读书笔记在 `literature/notes/`（文件名即编号），原文在 `literature/`，设计与结果的综述见 [literature/notes/I_综合.md](../literature/notes/I_综合.md)。I18（欧盟 ELI 理事会结论）未取到，未使用。

| 编号 | 文献 | 用于 |
|---|---|---|
| I1 | Thakur, Reimers, Rücklé, Srivastava & Gurevych (2021). BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models. NeurIPS 2021 Datasets & Benchmarks. | BM25 作基线；评测按集合分报 |
| I2 | Cormack, Clarke & Büttcher (2009). Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods. SIGIR 2009. | 倒数排名融合，k = 60 |
| I3 | Santhanam, Khattab, Saad-Falcon, Potts & Zaharia (2022). ColBERTv2: Effective and Efficient Retrieval via Lightweight Late Interaction. NAACL 2022. | 评测集的划分；多向量索引未采用 |
| I4 | Chen, Xiao, Zhang, Luo, Lian & Liu (2024). M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation. Findings of ACL 2024. | 稠密通道模型（BGE-M3）；跨语言时稀疏通道无效 |
| I5 | Chen, Wang, Chen, Yu, Ma, Zhao, Zhang & Yu (2024). Dense X Retrieval: What Retrieval Granularity Should We Use? EMNLP 2024. | 检索单元的粒度；不改写原文 |
| I6 | Louis & Spanakis (2022). A Statutory Article Retrieval Dataset in French (BSARD). ACL 2022. | 法条检索基线；法条连同层级标题存储 |
| I7 | Louis, van Dijck & Spanakis (2023). Finding the Law: Enhancing Statutory Article Retrieval via Graph Neural Networks (G-DSR). EACL 2023. | 层级结构有助检索 |
| I8 | Louis, van Dijck & Spanakis (2024). Interpretable Long-Form Legal Question Answering with Retrieval-Augmented Large Language Models (LLeQA). AAAI 2024. | 法条与标题一起存 |
| I9 | Su et al. (2024). STARD: A Chinese Statute Retrieval Dataset Derived from Real-life Queries by Non-professionals. Findings of EMNLP 2024. | 中文法条检索基线 |
| I10 | Lewis et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS 2020. | 检索增强的基本框架 |
| I11 | Edge et al. (2025). From Local to Global: A Graph RAG Approach to Query-Focused Summarization. arXiv:2404.16130v2（预印本）. | 未采用模型抽取的图与社区摘要 |
| I12 | Gutiérrez et al. (2024). HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models. NeurIPS 2024（arXiv:2405.14831v3）. | 个性化 PageRank 与节点特异性 |
| I13 | Han et al. (2026). RAG vs. GraphRAG: A Systematic Evaluation and Key Insights. KDD 2026（预印本 arXiv:2502.11371v3）. | 图只在多跳上有利；模型抽取的图覆盖不全 |
| I14 | Magesh, Surani, Dahl, Suzgun, Manning & Ho (2025). Hallucination-Free? Assessing the Reliability of Leading AI Legal Research Tools. Journal of Empirical Legal Studies. | 引语核对；错误前提防护 |
| I15 | Sannier, Adedjouma, Sabetzadeh & Briand (2017). An Automated Framework for Detection and Resolution of Cross References in Legal Texts. Requirements Engineering. | 交叉引用的检测与解析、按规则族抽查 |
| I16 | Green, Karvounarakis & Tannen (2007). Provenance Semirings. PODS 2007. | 影响分析（依赖边的反向可达） |
| I17 | OASIS LegalDocML TC (Palmirani, Sperberg, Vergottini & Vitali eds.) (2018). Akoma Ntoso Version 1.0. Part 1: XML Vocabulary. OASIS Standard. | 作品 / 文本（FRBR）；在效与适用两种时间 |
| I19 | de Martim (2025). An Ontology-Driven Graph RAG for Legal Norms: A Structural, Temporal, and Deterministic Approach (SAT-Graph RAG). FAIA (IOS Press) 2025 / arXiv:2505.00039. | 结构化、时间化、确定性的法规图 |
| I20 | Cymbler, Guez & Fabre (2026). Temporal Misgrounding in Legal RAG: A Versioned-Corpus Benchmark for French Tax Law (FiscalQA Pro). ICML 2026 Workshop on AI for Law / arXiv:2608.09393. | 按日期回答；NotCovered，不拿现行文本代答 |
| I21 | Gao et al. (2023). Enabling Large Language Models to Generate Text with Citations. EMNLP 2023. | 约 100 词的单元；先检索后引用 |
| I22 | Joren et al. (2025). Sufficient Context: A New Lens on Retrieval Augmented Generation Systems. ICLR 2025（预印本 arXiv:2411.06037v3）. | 未决即 unresolved；程序性弃答 |
| J10 | Schelter, Lange, Schmidt, Celikel, Biessmann & Grafberger (2018). Automating Large-Scale Data Quality Verification. PVLDB 11(12): 1781–1794. | 声明式约束、严重程度、构建间对照 |
| J11 | Rashkin et al. (2023). Measuring Attribution in Natural Language Generation Models. Computational Linguistics 49(4). | 口径必须可归属到具体原文（decisions.csv 的逐字锚点） |
