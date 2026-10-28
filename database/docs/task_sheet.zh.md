# 采集任务单

本任务单按顺序写清楚每个地区要做的事。每一步后面写了对应的规范章节，`数据库规范.md` 里有完整说明。csv 里由 AI 填写的文字（statement、note）和会话记录用英文；引文、标题保持原文。英文副本是 `database/collection_task_sheet.en.md`，两者不一致时以本文为准。

## 0. 只做一次：准备环境

在项目根目录（`database/` 的上一级）运行：

```bash
conda create -n tax python=3.11
conda activate tax
pip install -r database/requirements.txt
```

原件里有 .doc、.rtf、.xls、.ppt 时还要装 LibreOffice。之后所有命令都在项目根目录、`tax` 环境里运行。

## 1. 每个地区按顺序做

下面用 `<jur>` 表示地区代码（`cn hk sg id vn my th ae jp kr in`）。

1. **列清单**（第 2 节、第 4.1 节）：对照 9 类内容和 3 类网页，逐类找官方网站上的文件，记下地址；再列出这个地区负责的地区对（字母序在前的那一方负责，如 cn 负责 cn-hk、cn-sg，ae-cn 归 ae），查每对有没有协定；协定优先收英文本，没有英文本收中文本；再查 MLI 是否适用、有没有综合文本（第 4.2 节）；一方对 MLI 第 35 条第 7 款作了保留的（如香港），开始适用日看 OECD 公布的通知日期。
2. **抓取**（第 4.2 节）：一份文件跑一次 fetch.py，`--category` 写它属于哪几类。抓不到时按第 4.1 节的 8 步试；全部失败就用 `--blocked` 记下来，再按第 4.7 节人工采集。仍取不到就转人工（规范第 4.8 节 H1）。英文本就是正本的（如香港、新加坡的法律）只登记英文本；本地语言正本和英文译本都有时两份都登记（规范开头）。清单页抓下来是空壳的照常登记，note 写明（第 4.1 节）。
3. **构建**：运行 `python database/tools/build.py`。打开 `database/STATUS.md` 的 Documents 表，检查每份文件的 text 列是 `ok`；再检查法律、法规、协定的 slicing 列是本国切法，不是 `whole` 或 `page`。切坏了先按规范第 4.9 节修切法；修不好再照常继续，记进会话记录（第 4.3 节）。
4. **被替换的条款**（第 4.3 节、第 4.2 节）：逐条读每份议定书和 MLI 修改里的"取消、替换、删除"，每处在 `superseded.csv` 里登记一行，再构建一次。综合文本没合入议定书的，原协定和综合文本各登记一行；后来的议定书取消了前一份议定书的条款，也登记一行；综合文本里方括号中的"[REPLACED by …] [原文]"也登记。
5. **抄参数**（第 4.4 节）：用 `python database/tools/find.py <词> --jur <jur>` 找条款，它会给出 cite_id 和可直接当 quote 的整句；按示例写 `param.csv`，每个数字一行。名单类信息每个国家一行（第 4.4 节）。有 MLI 综合文本的地区对，协定参数引综合文本；新加坡的协定 PDF 把 MLI 修改列在附件 A，PPT 引 `#annexA.<条目>`，这份 PDF 同时填进 doc_id 和 mli_doc_id；MLI 适用但没有综合文本的，引 MLI 公约条款（如 `intl.oecd.mli.en#7.1`）。第三国货币的门槛（如 US$10 million）unit 写 `text`。
6. **缺项记录**（第 2 节、第 4.4 节）：某类没有文件，或某个主体的某个槽位法律没有规定，在 `decision.csv` 写一行。同一件事可能要写两行：一行写类别，一行写槽位，例如"没有 CFC"既是第 3 类没有文件，也是 cfc 槽位没有规定。
7. **协定行**（第 3 节、第 4.5 节）：这个地区负责的每个地区对在 `treaty.csv` 写一行；没有协定的，doc_id 留空，note 写 "No treaty"。不负责的地区对不登记。
8. **验收**（第 5 节）：运行 `python database/tools/build.py --jur <jur>`，按输出的每一行 error 和 gap 去补，直到输出 `PASSED`。
9. **会话记录**：在 `database/session_log.md` 末尾追加一节，格式见第 4 部分。遇到规范第 4.8 节七种情况之一的，写进 Handoff to a person；其余问题自己按规范解决，不转人工。
10. **上传**（第 4.5 节）：`python database/tools/upload.py --dry-run` 先看计划，再去掉 `--dry-run` 上传；上传会把远端整个换成本地已通过验收的地区的数据：多人分工时先合并文件夹，再由一人上传。没有远端凭证时，把整个 `database/` 文件夹打包发回。

## 2. 命令示例

```bash
# 抓取一部法律
python database/tools/fetch.py --id cn.law.eit --jur cn --type law --category "1;3;4" --title "中华人民共和国企业所得税法" --url http://www.npc.gov.cn/zgrdw/npc/xinwen/2019-01/07/content_2070260.htm --lang zh --effective 2008-01-01

# 抓取公告和它的附件（国家税务总局的网站要用 curl 引擎）
python database/tools/fetch.py --id cn.sta.2019-35 --jur cn --type guidance --category "5;7" --title "国家税务总局关于发布《非居民纳税人享受协定待遇管理办法》的公告" --url https://fgk.chinatax.gov.cn/zcfgk/c100012/c5194891/content.html --lang zh --with-attachments --engine curl

# 抓取协定：--jur 写地区对，按字母序；协定不用写 --category
python database/tools/fetch.py --id treaty.cn-hk.2006.zh --jur cn-hk --type treaty --title "内地和香港特别行政区关于对所得避免双重征税和防止偷漏税的安排" --url https://www.chinatax.gov.cn/chinatax/n810341/n810770/c1153751/5131982/files/11537511.pdf --lang zh

# 只拿到存档副本时：--url 写原官方地址，--note 写副本来源
python database/tools/fetch.py --register-file <本地副本路径> --id id.uu36-2008 --jur id --type law --category "1" --title "UU No. 36 Tahun 2008" --url https://jdih.kemenkeu.go.id/fulltext/2008/36TAHUN2008UU.htm --lang id --note "Internet Archive copy, timestamp <timestamp>"

# 所有办法都试过仍下载失败
python database/tools/fetch.py --blocked --id in.ita2025 --jur in --title "Income-tax Act, 2025" --url https://www.incometaxindia.gov.in/ --reason "HTTP 403" --alt-tried "<试过的办法，用分号隔开>"

# 韩国法令库：url 里写 OC=<OC>，编号放在 .env 的 LAW_GO_KR_OC（第 4.7 节）
python database/tools/fetch.py --id kr.cita --jur kr --type law --category "1;3;4" --title "법인세법" --url "https://www.law.go.kr/DRF/lawService.do?OC=<OC>&target=law&type=XML&LM=법인세법" --lang ko

# 找条款和原句
python database/tools/find.py 减按10% --jur cn

# 上传：远端整个换成本地已通过验收的地区
python database/tools/upload.py --dry-run
python database/tools/upload.py

# 改 database/tools/ 前后（规范第 4.9 节）
python database/tools/clause_diff.py --save
python database/samples/slicers-2026-10-23/run_slicers.py
python database/tools/build.py
python database/tools/clause_diff.py

# 浏览库：地图上地区是节点、协定和单向名单是边，点开看文件、参数和条文（只读，每次打开直接读 csv）
python database/viewer/server.py      # 然后打开 http://127.0.0.1:8770

# 构建全库；验收一个地区
python database/tools/build.py
python database/tools/build.py --jur cn
```

`doc.csv` 由 fetch.py 写，不要手填；只有类别填错时，直接改它的 category 列。

## 3. csv 示例行

下面每一行都是真实条文，已经在构建里跑过、零错误。照这个格式写，不要照抄内容。

**param.csv**

```csv
param_id,scope,subject,slot,name,value,unit,cite_id,quote,effective_from,effective_to,note
cn.outbound_wht.dividend_wht_rate,cn,company,outbound_wht,dividend_wht_rate,10,%,cn.reg.eit#91,非居民企业取得企业所得税法第二十七条第(五)项规定的所得，减按10%的税率征收企业所得税,2008-01-01,,EIT Law art. 4 sets 20% for this income; art. 91 of the Implementation Regulations reduces it to 10%.
cn-hk.outbound_wht.holding_pct_min,cn-hk,company,outbound_wht,holding_pct_min,25,%,treaty.cn-hk.2006.zh#10.2,直接拥有支付股息公司至少25%资本的,2007-01-01,,Application date from the STA treaty list (cn.sta.ssty).
cn-hk.outbound_wht.dividend_rate_reduced,cn-hk,company,outbound_wht,dividend_rate_reduced,5,%,treaty.cn-hk.2006.zh#10.2,如果受益所有人是直接拥有支付股息公司至少25%资本的公司，为股息总额的5%,2007-01-01,,Mainland application date; Application date from the STA treaty list (cn.sta.ssty).
cn-hk.outbound_wht.dividend_rate_other,cn-hk,all,outbound_wht,dividend_rate_other,10,%,treaty.cn-hk.2006.zh#10.2,在其它情况下，为股息总额的10%,2007-01-01,,Application date from the STA treaty list (cn.sta.ssty).
cn.cfc.cfc_whitelist_us,cn,company,cfc,cfc_whitelist_us,yes,bool,cn.gsh.2009-37#all,设立在美国、英国、法国、德国、日本、意大利、加拿大、澳大利亚、印度、南非、新西兰和挪威的,,,United States: profits of a controlled foreign enterprise set up there need not be deemed distributed. The notice states no start date (issued 2009-01-21).
sg-vn.outbound_wht.holding_amount_min,sg-vn,all,outbound_wht,holding_amount_min,US$10 million,text,treaty.sg-vn.1994.en#10.2,or more than US$10 million,1993-01-01,,"Alternative condition for the 5% rate: capital contributed of more than US$10 million. USD is not a currency of jurisdiction.csv, so the amount is kept as text."
```

**decision.csv**（缺项记录：要么填 category，要么填 subject 和 slot）

```csv
id,jur,category,subject,slot,statement,cite_id,quote
hk.absent.3,hk,3,,,No CFC rules: profits tax reaches only profits arising in or derived from Hong Kong (s14(1)); the profits of foreign subsidiaries are not attributed to Hong Kong shareholders. Checked the IRO and the IRD pages on international tax.,hk.cap112#s14,"profits tax shall be charged for each year of assessment on every person carrying on a trade, profession or business in Hong Kong in respect of his assessable profits arising in or derived from Hong Kong for that year from such trade, profession or business"
hk.absent.cfc,hk,,all,cfc,No CFC rules: profits tax reaches only profits arising in or derived from Hong Kong (s14(1)); the profits of foreign subsidiaries are not attributed to Hong Kong shareholders. Checked the IRO and the IRD pages on international tax.,hk.cap112#s14,"profits tax shall be charged for each year of assessment on every person carrying on a trade, profession or business in Hong Kong in respect of his assessable profits arising in or derived from Hong Kong for that year from such trade, profession or business"
hk.absent.company.outbound_wht,hk,,company,outbound_wht,"No withholding tax on dividends paid to non-residents: s20B collects tax through the payer only for sums deemed by s15(1)(a), (b), (ba) or (bb) and for entertainers and sportsmen, and a dividend from a corporation chargeable to profits tax is excluded from other persons' profits (s26(a)).",hk.cap112#s20B,"sums deemed by virtue of section 15(1)(a), (b), (ba) or (bb) to be receipts arising in or derived from Hong Kong from a trade, profession or business carried on in Hong Kong"
hk.absent.page_deadlines,hk,page_deadlines,,,"No withholding tax on dividends, so no withholding deadline page applies; the s20B returns for royalties and entertainers are outside this library's scope.",,
```

**treaty.csv**

```csv
pair,doc_id,in_force_from,mli_doc_id,note
cn-id,treaty.cn-id.2001.en,2003-08-25,treaty.cn-id.2001.mli.en,"MLI applies from 2023-01-01 (in China: taxes withheld at source from 2023-01-01; other taxes for taxable periods beginning on or after 2023-06-10), per the dates in the synthesised text published on the STA treaty page."
hk-sg,,,,"No treaty: no comprehensive double taxation agreement (checked hk.ird.dta-list and the IRD Singapore page https://www.ird.gov.hk/eng/tax/dta_singapore.htm); only the 2003 Airline and Shipping Income Agreement (Cap. 112AO) exists, which does not cover dividends."
sg-th,treaty.sg-th.2015.en,2016-02-15,treaty.sg-th.2015.en,"MLI applies from 2023-01-01 (in Singapore: taxes withheld at source on amounts paid on or after 2023-01-01; other taxes for basis periods beginning on or after 2023-01-01), per Annex A item 3 of the IRAS treaty PDF. Singapore gives effect to the MLI by an Order that amends the treaty; IRAS prints the amendments in Annex A of the same PDF, so the PDF is both doc_id and mli_doc_id. The 1975 Convention (Annex B) ceased to have effect (Article 27(3)). Dates from the top of the PDF."
```

没有协定的地区对照 hk-sg 那行写：doc_id 留空，note 以 `No treaty` 开头并写查过哪些清单页；地区代码按字母序。

**superseded.csv**

```csv
doc_id,clause,by,since,note,phrase
treaty.cn-hk.2006.zh,13.5,treaty.cn-hk.2006.p2.zh#5,2008-06-11,"Replaced by the Second Protocol, in force 2008-06-11.",
treaty.cn-hk.2006.zh,2.3@2-4,treaty.cn-hk.2006.p2.zh#1,2008-06-11,"Item (1) (Mainland taxes) replaced by the Second Protocol, in force 2008-06-11.",
treaty.hk-jp.2010.mli.en,26@3-8,treaty.hk-jp.2010.mli.en#26.mli7,2023-04-01,The bracketed former Article 26 text. Replaced by MLI Article 7(1) (principal purpose test); the MLI has effect in Hong Kong from 2023-04-01 for taxes withheld at source and from years of assessment beginning on or after 2024-04-01 for other taxes.,
treaty.sg-th.2015.en,annexB*,treaty.sg-th.2015.en#27.3,2017-01-01,The 1975 Convention printed in Annex B ceased to have effect once this Agreement took effect (Article 27(3)).,
```

## 4. 会话记录格式

每次会话结束，在 `database/session_log.md` 末尾追加：

```markdown
## 2026-10-24 cn
- Registered: cn.law.eit, cn.reg.eit, cn.sta.2019-35, cn.sta.2019-35.a01
- Download failures: none
- Parameters added: 12
- Absence records added: 3
- Slicing problems: none
- Rate-table mismatches: none
- Handoff to a person: none
- Tool changes: none
- Acceptance: NOT PASSED (gaps left: category cn|6, slot cn|individual|cfc)
```

没有的项写 `none`，不要删行。Tool changes 有内容时写明改了哪个文件、为什么、核过哪些文件、规范第 4.9 节六项检查的结果。Handoff to a person 有内容时，每项单独一行，以规范第 4.8 节的编号开头，写明试过什么、要人做什么：

```markdown
- Handoff to a person:
  - H1 in.itr2026: <official page url>; tried requests, curl and the Internet Archive; HTTP 403 every time. Download it in a browser and register it (§4.7).
  - H2 kr.law.cit: the law.go.kr API needs an OC id and .env has none. Apply for one (§4.7).
```

## 5. 看到这些报错时

| 输出里的报错 | 怎么办 |
|---|---|
| `doc …: file missing` | 原件不在 raw/ 下：用 fetch.py 重新抓，不要手改 doc.csv 的 file 列 |
| `doc …: sha256 differs` | 原件被改动过：加 `--force` 重新抓 |
| `doc …: no text (scanned_or_empty)` | 扫描件没有文字层：找有文字的版本；找不到就转人工（H3） |
| `doc …: category empty` 或 `category … not in` | 改 doc.csv 这一行的 category 列 |
| `doc …: id may only hold ASCII letters` 或 fetch 报 `--id may only hold ASCII` | id 只用英文字母、数字、点、下划线、连字符 |
| fetch 报 `HTTP 202`（新加坡法令库） | 这是网站的人机验证：隔几分钟到一小时再抓，不要连续重试；一直不行转人工（规范第 4.8 节 H1） |
| `the url needs the OC id of law.go.kr` | 在 .env 写上 `LAW_GO_KR_OC=<你的编号>`；还没有编号的，转人工（H2），由人按第 4.7 节申请 |
| `doc …: lang empty` | 在 doc.csv 这一行补上语言代码；以后 fetch 时写 `--lang` |
| `doc …: id must start with …` 或 `decision …: id must start with …` | 按提示改 id；doc 的 id 要用 `--force` 重新登记 |
| `doc …: Arabic text layer garbled` | 这份阿拉伯文 PDF 的文字是乱码：改用 uaelegislation.gov.ae 的网页登记 |
| `… must be a date written YYYY-MM-DD` | 日期改成 `2026-01-01` 这种写法 |
| `doc …: a treaty document's jur must be its pair` | 加 `--force`，用地区对作 `--jur` 重新登记 |
| `doc …: url … is not on an official host` | url 改成官方网站的地址；副本的来源写进 note。确实是政府网站但不在表里的，按规范第 4.9 节补进 fetch.py 的 `OFFICIAL` |
| `param …: cite_id not found` | 用 `find.py <引文里的几个字>` 找到正确的 cite_id |
| `param …: quote not found verbatim` | 用 `find.py` 重新取这一句，或用 `find.py --cite <cite_id>` 看全文后复制，一个字都不改 |
| `param …: param_id must be …` | 按提示改成 `<scope>.<slot>.<name>` |
| `param …: value … must be a plain number` | value 只写数字，单位写在 unit 列 |
| `param …: unit … not in` | 改成 `%`、`days`、`months`、`years`、`count`、`bool`、`text` 或币种代码 |
| `decision …: … must cite the clause` | 补上界定征税范围的条款的 cite_id 和逐字引文 |
| `decision …: an absence record needs jur and either category, or subject and slot` | jur 必填；category 与 subject + slot 只能填一种 |
| `treaty …: write the pair in alphabetical order` | 地区对改成字母序，如 `cn-hk` |
| `treaty …: doc_id … not in doc` | 先用 fetch.py 登记这份协定 |
| `superseded.csv: phrase not found` | phrase 必须和条文逐字一致 |
| upload 报 `upload of … failed: HTTP 400`（403 或 row-level security） | 存储桶 `database` 上允许公开密钥读写的规则不见了：转人工（H7），或在 .env 换成 secret key（规范第 4.5 节） |
| clause_diff 报 `… cites …, which no longer exists` | 改工具让条款编号变了：用 `find.py` 找到新编号，改好引用，再跑一遍检查 |
| fetch、build 或 upload 报 `Traceback`，或报错不在本表 | 按规范第 4.9 节修工具，修完做完六项检查；要改表的列或检查规则的，转人工（H7） |
| `gap: category …` | 补这一类的文件，或写一条缺项记录 |
| `gap: slot … without a parameter` | 补这个槽位的参数，或写一条缺项记录 |
| `gap: pair … without a treaty row` | 在 treaty.csv 补一行 |
| `gap: download not resolved` | 按第 4.7 节人工采集，用同一个 id 登记；不能用浏览器的转人工（H1）；确认不需要的，从 blocked.csv 删掉这一行，并在会话记录里写明原因 |

## 6. 不要做的事

- 改 `database/tools/` 不跳过规范第 4.9 节的六项检查；不放宽检查，不改表的列和验收规则（要改的转人工 H7）。
- 不手改 `clause.csv`、`files.csv`、`text/`、`database.sqlite`、`STATUS.md`，它们每次构建都会重写。
- 不编数字：每个参数都要有从条文逐字复制的引文。
- 不用第三方网站当来源；存档副本只能用 `--register-file` 登记，`--url` 写原官方地址。
- 不绕过验证码、人机验证或登录墙。
- 不删、不改别人登记的行；发现有误的转人工（H7）。
- 不因一项转人工就停下其余工作；规范第 4.8 节七种情况以外的问题不转人工。
