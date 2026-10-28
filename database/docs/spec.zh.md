# 数据库规范（最小集）

本规范用中文，供人阅读。AI 写进文件的文字（statement、note、session_log.md）用英文；原件、条文、引文、文件标题保持原文语言，不翻译。法律同时有本地语言正本和英文译本时，两份都登记，参数引正本；英文本本身就是正本的（如香港、新加坡的法律），只登记英文本；只有英文译本可取时，在 note 写明 "unofficial translation"。

2026-10-23。目标：支持"亚洲跨境股息优化"流程（收款人分公司与个人，11 个地区：中国大陆、中国香港、新加坡、印尼、越南、马来西亚、泰国、阿联酋、日本、韩国、印度）的最小数据库。

英文副本：`database/database_spec.en.md`（本规范）、`database/collection_task_sheet.en.md`（采集任务单）。两者不一致时以中文版为准；改中文版时同步改英文副本。

动手前先读 `database/采集任务单.md`：那里按顺序列出每个地区要跑的命令和每个 csv 的示例行；本规范是它引用的完整说明。

## 1. 最小流程

```text
官方网站（税务局 / 财政部 / 法律库 / 公报）
   │  每国按 9 类内容 + 3 类网页逐项收，每项 0 份、1 份或多份；每个地区对 1 份完整协定（清单见第 2 节）
   │  做法见第 4 节
   ▼
A  原件
   raw/<jur>/<doc_id>.<ext>（原样保存）  +  text/<doc_id>.txt（纯文本）
   ──▶ files（路径、哈希、字节数）
   ▼
B  登记
   doc（一份文件一行：地区、类型、类别、标题、出处 URL、文件路径、哈希、语言、生效期）
   decision 缺项记录（某地区某类没有文件，或某主体某槽位法律没有规定时一行：地区、类别或主体 + 槽位、说明、引文）
   treaty（一个地区对一行：协定 doc_id，无协定则 doc_id 留空并注明）
   ▼
C  切条
   clause（一条一行：cite_id = <doc_id>#<条号>，正文逐字，不改字）
   ▼
D  抄数
   param（每个数字或判定标准一行：槽位 × 主体 × 地区或地区对 → 值、单位、逐字引文、cite_id、生效期）
   ▼
E  覆盖检查
   11 地区 × 12 类（9 类内容 + 3 类网页），每格有文件或缺项记录
   11 地区 × {公司, 个人} × 6 槽位，每格有参数或缺项记录
   55 个地区对，每对有协定行或"无协定"行
```

## 2. 每国要收的信息（最小范围）

每国按下面 9 类内容和 3 类网页逐项核对，每个地区对收 1 份完整协定。

类指内容，不指文件数：一项可能对应 0 份、1 份或多份文件，一份文件也可能同时属于几类（第 1、3、4 类常在同一部所得税法里）。每份文件在 `doc.category` 里写它属于哪几类，取值是 `1`–`9`、`page_treaties`、`page_rates`、`page_deadlines`，多个用分号隔开。

某地区某类没有文件时，在 `decision` 表登记一条缺项记录：`jur`、`category` 填上，`statement` 写明缺什么、查过哪里。第 1–4、9 类的缺项必须引界定该税征税范围的条款并逐字摘引；第 5–8 类和网页没有条文可引时可以不引。

**每国 9 类内容**

1. 所得税法中的四处条文：出境股息预提税（税率、豁免）、收到境外股息的课税与免税条件（含境外所得免税制度的条件，如来源地税率门槛）、公司居民判定、外国税抵免方式与限额。
2. 个人所得税法中的三处条文：个人股息税率 / 免税、个人居民判定、个人外国税抵免。
3. CFC 条文及其附带名单（白名单、低税率名单、豁免条件）。
4. 反滥用条文：GAAR、协定待遇的国内限制（PPT 落地条款）。
5. 受益所有人判定要素文件（公告 / 指引）。
6. 居民判定指引（实际管理机构标准、个人居住天数计算）——法律延伸到指引时才需要。
7. 协定待遇申报 / 备案程序文件及表格（谁报、何时报、报什么）。
8. 居民身份证明程序（签发条件、申请方式）。
9. 股权转让所得税条文（含视同处置、非居民间接转让）——只为搭结构的一次性成本。

**每国 3 类网页**：协定清单页（`page_treaties`，生效日期）、预提税税率表（`page_rates`，交叉核对，不作引用来源）、预提税申报期限页（`page_deadlines`）。

**每个地区对**：完整协定 + 议定书 + MLI 综合文本，用到第 1–4 条（范围、居民、加比规则）、第 10 条及"受益所有人"定义、消除双重征税条款、利益限制 / PPT。整份登记，只对需要的条款出参数；无协定的地区对也登记一行"无协定"。MLI 怎么处理见第 4.2 节。

漏核任何一项，对应的税率、条件、证明或时间线就缺来源。

## 3. 最小数据库架构

```text
                 ┌──────────────┐
                 │ jurisdiction │ 11 行，预填
                 └──────┬───────┘
                        │ 1:n
   ┌──────────┐   ┌─────▼─────┐        ┌────────┐
   │  files   │◀──│    doc    │───────▶│ treaty │ 55 行，每个地区对一行
   │ 桶内文件 │   │ 一份文件  │ 1:0..1 │        │
   └──────────┘   └─────┬─────┘        └────────┘
                        │ 1:n
                  ┌─────▼─────┐
                  │  clause   │ 一条条文，正文逐字
                  └─────┬─────┘
                        │ 1:n
                  ┌─────▼─────┐
                  │   param   │ 一个数字，带逐字引文
                  └───────────┘

   decision：缺项记录，一行 = 某地区某类没有文件，或某主体某槽位法律没有规定（引 clause）
```

| 表 | 列 | 索引 |
|---|---|---|
| `jurisdiction` | code（小写两字母；地区对按字母序写作 `cn-hk`）, name, currency, company_in_scope, individual_in_scope（预填） | — |
| `files` | path, sha256, bytes | path |
| `doc` | id, jur（地区代码；协定、议定书写地区对，如 `cn-hk`；MLI 等多边文件写 `intl`）, type, category（第 2 节的类别，可多个，分号隔开）, title, url, file, sha256, lang（必填，文件的语言代码，如 zh、en、th、ar）, effective_from, effective_to, note | id |
| `treaty` | pair, doc_id（空 = 无协定）, in_force_from, mli_doc_id, note | pair |
| `clause` | cite_id, doc_id, label, text | cite_id, doc_id |
| `param` | param_id, scope（地区或地区对）, subject（company / individual / all）, slot（outbound_wht / inbound / final / residence / cfc / anti_abuse）, name, value, unit, cite_id, quote, effective_from, effective_to, note | param_id |
| `decision` | id, jur, category, subject, slot, statement, cite_id, quote（每行是一条缺项记录：填 category，或填 subject 和 slot；见第 2 节、第 4.4 节） | id |

**各表、各列的含义**（例子都取自库里的真实行）

`jurisdiction`：收录的地区，一行一个，预先填好，不要改。
- code：地区代码，两个小写字母，如 `cn`（中国大陆）、`hk`（中国香港）。两个地区组成"地区对"时按字母序连写，如 `cn-hk`，用在协定和协定参数上。
- name：地区名称。
- currency：本币代码，如 `HKD`；参数的单位可以写它。
- company_in_scope、individual_in_scope：这个地区要不要收公司、个人的规则（yes / no）。覆盖检查按它决定查不查这一主体的 6 个槽位。

`doc`：收进库的一份原件，可以是一部法律、一份公告、一页网页，或一份协定、议定书。
- id：文件编号，如 `cn.law.eit`（企业所得税法）、`treaty.cn-hk.2006.zh`（内地和香港安排的中文本）。以地区代码、`treaty.<地区对>.` 或 `intl.` 开头。
- jur：文件属于哪个地区。协定类写地区对，MLI 等多边文件写 `intl`。
- type：文件种类：law（法律）、regulation（法规）、guidance（公告、指引）、treaty（协定类）、form（表格）、page（网页）。
- category：属于第 2 节的哪几类，如 `1;3;4`。
- title：原文标题，不翻译。
- url：官方出处地址。
- file：本地原件路径，如 `raw/cn/cn.law.eit.html`。
- sha256：原件的指纹。原件被改动时，构建会报错。
- lang：原件的语言，如 zh、en。
- effective_from、effective_to：文件的生效、失效日期，知道才填。
- note：补充说明，如怎么抓到的、效力标注、副本来源。

`files`：每个原件（`raw/`）和从它抽出的纯文本（`text/`）各一行，由构建生成。
- path：文件路径，也是它在远端存储桶里的名字。
- sha256、bytes：文件的指纹和大小。

`clause`：从文件里切出的一条条文（一条、一款、一段或一页），正文逐字，由构建生成。
- cite_id：条文编号，即文件 id + `#` + 条号，如 `cn.law.eit#26`（第 26 条）、`hk.cap112#s26`（第 26 节）、`treaty.cn-hk.2006.zh#10.2`（第 10 条第 2 款）。参数和缺项记录都用它指向出处。
- doc_id：条文所在的文件。
- label：给人看的条号，如"第26条"、"Article 10(2)"。
- text：条文原文，一字不改。

`treaty`：两个地区之间有没有税收协定，一个地区对一行（共 55 对）。
- pair：地区对，如 `cn-sg`。
- doc_id：协定文件；留空表示两地之间没有协定。
- in_force_from：协定生效日。
- mli_doc_id：MLI 综合文本，即协定被 MLI 修改后的文本；没有就留空。
- note：MLI 是否适用、从哪天起适用，以及日期的出处。

`param`：从条文里抄出的一个数字或一条判定标准，是库里最核心的内容。
- param_id：参数编号，即 scope.slot.name，必要时加后缀，如 `cn.outbound_wht.dividend_wht_rate`（中国大陆向境外付股息的预提税率）。
- scope：适用范围。本地法写地区代码（如 `cn`），协定写地区对（如 `cn-hk`）。
- subject：对谁适用：company（收款人是公司）、individual（收款人是个人）、all（两者都适用）。
- slot：属于股息税负的哪个环节：
  - outbound_wht：本地公司向境外付股息时的预提税；
  - inbound：居民收到境外股息时怎么征、怎么免、怎么抵免；
  - final：股息并入应税所得后的最终税率，或本地股息免税；
  - residence：怎样才算本地居民；
  - cfc：受控外国企业规则；
  - anti_abuse：一般反避税规则，以及对协定待遇的限制（PPT）。
- name：具体是什么数，如 dividend_rate（股息税率）、holding_pct_min（最低持股比例）。
- value、unit：值和单位，如 `10` 和 `%`、`12` 和 `months`、`yes` 和 `bool`。
- cite_id、quote：出处条文和逐字引文。构建时检查引文确实出现在那条条文里。
- effective_from、effective_to：这个数从哪天起、到哪天止适用。
- note：说明，如适用条件、例外、日期的出处。

`decision`：缺项记录，说明"这里本来就没有"，把它和"还没收"区分开。每行要么填 category，表示某地区没有这一类文件（如香港没有 CFC 规则）；要么填 subject 和 slot，表示法律对这一环节没有规定（如香港不征股息预提税）。
- id：编号，如 `hk.absent.cfc`。
- jur、category、subject、slot：缺的是哪个地区的哪一类，或哪个主体的哪个环节。
- statement：说明缺什么、为什么缺、查过哪里。
- cite_id、quote：界定征税范围的条文和逐字引文，证明"确实没有"。

**远端**：上传后，这七张表在远端 Postgres 的 schema `database` 里，与存档库的 schema `official` 并列；`files` 表列出的文件在存储桶 `database` 里。它们是可以直接查询的真表，不是快照，但只在上传时更新：每次上传都整个换成本地已通过验收的数据，不保留历史版本。

**本地文件约定**：本地一张表一个同名 csv，与 `raw/`、`text/` 同放在 `database/` 下；`jurisdiction / treaty / doc / param / decision` 五个 csv 由 AI 或人工填（`jurisdiction.csv` 已预填，`doc.csv` 经 fetch.py 写入），`files.csv`、`clause.csv` 由 build 生成，不由 AI 或人工填；fetch.py 另写 `blocked.csv`，会话记录写在 `session_log.md`。csv 里由 AI 填写的文字（statement、note 等）和会话记录用英文，引文和标题保持原文。另有一个辅助 csv `superseded.csv`（doc_id, clause, by, since, note, phrase），由 AI 或人工填，登记被议定书或 MLI 替换的条款；它不是库表，只在构建时用来把这些条款排除出 `clause`。

**构建**：运行 `python database/tools/build.py`。它把原件转成 `text/`，切条，生成 `clause.csv`、`files.csv`，做全部检查，写出 `database.sqlite` 和 `STATUS.md`；加 `--jur <地区代码>` 时只检查该地区，不写任何产物（第 5 节）。有错误时退出码为 1；覆盖空格只在 `STATUS.md` 里列出，不算错误。

**环境**：Python 3.11，依赖和安装命令见 `database/requirements.txt`。原件是 .doc / .rtf / .xls / .ppt 时还需要 LibreOffice，路径在 build.py 顶部的 `SOFFICE` 里设置。

## 4. 数据采集方法

采集方先在本地按第 3 节的本地文件约定做完，再整体交付（第 4.5 节）。每一步对应第 1 节的 A–D。

### 4.1 选源

- 只收官方域名：税务局、财政部、法律汇编库、公报。第三方转载、律所摘要、维基不收，税率表网页只作交叉核对。build 对 url 不在官方域名表（fetch.py 的 `OFFICIAL`）里的文件报错；表里漏了某个政府域名时，按第 4.9 节补进 `OFFICIAL` 并记进会话记录，不要换成第三方地址。
- 优先现行合并本（consolidated）；没有合并本的，收原法 + 各修正案，并在 note 里写明哪些条已被修正。
- 协定优先收英文本（多数协定的英文本是同等作准文本之一）；没有英文本的收中文本；两者都没有时，收缔约一方的官方语言本，并在会话记录里写明（这种文本只能按页或整篇切）。
- 每份文件记一个备用地址。fetch.py 每次自动重试两次；仍失败时按下面的顺序换办法，全部失败才用 `fetch.py --blocked` 写进 blocked.csv（id、url、原因，`--alt-tried` 写试过哪些办法），转第 4.7 节人工采集，不留空位假装存在。

**抓不到时依次试**：

1. 换引擎：有的站（如国家税务总局）先返回一段设置 cookie 的脚本，加 `--engine curl`，它会带上 cookie 再请求一次；证书配置有问题的站加 `--insecure`。新加坡法令库（sso.agc.gov.sg）请求太密时回 HTTP 202，这是它的人机验证（AWS WAF），不绕过：隔几分钟到一小时再抓。
2. 换官方接口：法律库提供数据接口的，直接抓接口返回的结构化文件，比网页稳定，build 对这两种 XML 有专门切法：
   - 日本 e-Gov：`https://laws.e-gov.go.jp/api/1/lawdata/<法令ID>`
   - 韩国 law.go.kr：`https://www.law.go.kr/DRF/lawService.do?OC=<OC>&target=law&type=XML&LM=<法律名>`；`<OC>` 原样写，fetch.py 下载时从 .env 的 `LAW_GO_KR_OC` 取编号，doc.csv 里保留 `<OC>`（申请见第 4.7 节）
3. 换同一政府的其他官方站：同一文件常同时登在税务局、财政部、法律汇编库、政府公报上；只要是政府域名，就算官方来源。
4. 先搜索定位：用 `site:<官方域名> <文件名或文号>` 搜到官方站上的确切文件地址，再交给 fetch.py。
5. 慢站、大文件：fetch.py 的超时不够时，用 curl 手工下载，放长超时（`-m 600`），中断后用 `-C -` 从断点续传；下完核对文件完整（PDF 末尾有 `%%EOF`，XML 闭合到根标签），再用 `--register-file` 登记。
6. 长页面分段：一次加载会超时的长页面，分段加载后拼成一个文件，用 `--register-file` 登记，`--note` 写明由哪几段拼成。新加坡法令库的整部法令页（`?WholeDoc=1`）只先给前几部分，其余部分 fetch.py 会逐个补齐（note 里记补了几部分），不用手拼；网站对不用浏览器的请求只放行几次就回 202，fetch.py 会每次等 4 分钟再接着抓同一部分，整部所得税法约需一小时，放在后台跑。
7. Internet Archive 存档：官方站连不上时，先列出该地址的全部存档：
   `http://web.archive.org/cdx/search/cdx?url=<原地址>&fl=timestamp,statuscode,length`
   挑状态码 200、大小最完整的一次，用 `https://web.archive.org/web/<timestamp>id_/<原地址>` 下载；`id_` 让存档站返回当时的原始字节，不插入它自己的工具栏。登记用 `--register-file`，`--note` 写"Internet Archive 存档 <timestamp>"。原站恢复后用 `--force` 换成原站文件。
8. 换时间再试：当时连不上的先记 blocked.csv，下次会话再抓。

用 `--register-file` 登记时，`--url` 一律写原官方地址，副本怎么来的写在 `--note`。

不做的：绕过人机验证、验证码或登录墙。遇到这类页面，换站或记 blocked.csv。

清单页的内容由脚本加载、抓下来只有空壳时（如新加坡税务局的协定清单），照常登记这一页并在 note 写明；协定的生效日期改从协定文件抬头或生效公告取，在 treaty 行的 note 写来源。

### 4.2 下载与登记（A、B 步）

一份文件一次调用：

```bash
python database/tools/fetch.py --id <doc_id> --jur <jur> --type <law|regulation|guidance|treaty|form|page> --category <1–9 / page_treaties / page_rates / page_deadlines，多个用分号> --title "..." --url https://... [--effective YYYY-MM-DD] [--effective-to YYYY-MM-DD] [--lang en] [--note "..."] [--with-attachments] [--engine curl]
python database/tools/fetch.py --register-file <本地副本> --id ... --jur ... --type ... --category ... --title "..." --url <原官方地址> --note "<副本来源>"
python database/tools/fetch.py --blocked --id ... --jur ... --title "..." --url ... --reason "..." [--alt-tried "..."]
```

- `doc_id` 命名：法律 `<jur>.<简称>`（如 `my.ita1967`、`id.pph`），公告 `<jur>.<机关>.<年-号>`，协定 `treaty.<a>-<b>.<年>.<语言>`，网页 `<jur>.<机关>.<页名>`，多边文件 `intl.<简称>`。id 必须以 `<jur>.`、`treaty.<地区对>.` 或 `intl.` 开头，fetch.py 和 build 都会检查。
- 同一份法律登记两种语言（本地语言正本和英文译本）时，id 末尾加语言代码，如 `th.rc.th`、`th.rc.en`；`--lang` 必填。
- 原件按原字节存 `raw/<jur>/<doc_id>.<ext>`，不做任何转换；纯文本抽到 `text/<doc_id>.txt`（HTML 去标签；PDF 逐页抽字；doc/xls 经 LibreOffice 转换），记 sha256；抓取时间、抓取方式、非官方域名提示由 fetch.py 自动写进 note。
- 附件（公告所附办法、表格）用 `--with-attachments` 随主文件一起下载，id 为 `<主文件 id>.a01` 起，类型 attachment，note 里记 `parent=<主文件 id>`。
- 同一 id 再抓会跳过；确要替换用 `--force`，旧行和旧文件一起换掉。`--jur` 只接受 jurisdiction.csv 里的代码、地区对或 intl。
- 拿不到原站文件、只能用其他途径得到副本时（如 Internet Archive 存档），用 `--register-file` 登记，`--url` 写原站地址，`--note` 写副本来源。
- 每份文件按第 2 节写 `--category`；协定和地区对、intl 的文件可以不写，附件默认沿用主文件的类别，不对时直接改 doc.csv。
- 登记行写进 doc.csv，列与第 3 节 `doc` 表一致；协定、议定书的 `--jur` 写地区对（如 `cn-hk`），MLI 文本写 `intl`；协定另在 treaty 登记一行，议定书、MLI 文本各自登记为独立 doc，treaty 行里引用。
- **MLI**：
  1. 先查 MLI 是否适用于这个地区对：在 OECD 的 MLI 匹配数据库（MLI Matching Database）里，两边都把这份协定列为被涵盖协定、且对两边都已生效，才适用。结论写进 treaty 行的 note：`MLI applies from YYYY-MM-DD` 或 `MLI not applicable`。匹配数据库打不开时，看一方税务机关发布的 MLI 最终立场文件（Reservations and Notifications，第 2 条的通知列出该方的被涵盖协定）：一方没列这份协定就不适用。立场文件登记为 `intl.mli.positions.<地区>.<语言>`，jur 写 intl，在 note 里引用；两方都列了时，还要查另一方的立场文件和两边的生效日。一方对 MLI 第 35 条第 7 款作了保留的（如香港），MLI 要等它通知完成内部程序后才开始适用：OECD 公布的第 35(7)(b) 通知文件列出每份协定的通知日期，登记为 `intl.mli.notification-35-7b.<地区>.en`。清单写明已被 MLI 修改、但综合文本还没出的，按 MLI 第 35 条和双方的生效、通知日期算出开始适用日，写进 note 并注明 computed。
  2. 适用时，收任一方税务机关发布的综合文本（synthesised text），登记为 `treaty.<地区对>.<协定年份>.mli.<语言>`，type 写 treaty，jur 写地区对，再填进 treaty 行的 mli_doc_id。原协定和议定书照常登记。新加坡用本国法令落实 MLI，税务局的协定 PDF 把修改列在附件 A，没有带框的综合文本：这份 PDF 同时填进 doc_id 和 mli_doc_id，PPT 等规定引附件 A 的条目（如 `treaty.sg-th.2015.en#annexA.2`）。
  3. 有综合文本时，这个地区对的协定参数一律引综合文本：没被改动的条款照原样引；被 MLI 改动或补充的规定引框内条文，cite_id 是 `<doc>#<条>.mli<MLI 条号>`，如防止协定滥用 `treaty.jp-my.1999.mli.en#26.mli7`。综合文本是否合入双边议定书各地不同（国家税务总局的只合入 MLI，议定书附在文末；香港税务局的连议定书一并合入），看文本开头的说明。没合入的，被议定书改过的规定引议定书条文，并在 superseded.csv 里对原协定和综合文本各登记一行（第 4.3 节）；综合文本里方括号中的"[REPLACED by …] [原文]"也登记为被替换。
  4. 适用但两边都没发布综合文本时，登记 MLI 公约文本（`intl.oecd.mli.en`，jur 写 intl，全库只登记一次），受影响的参数引公约条款（如 `intl.oecd.mli.en#7.1`），在 note 写明依据，并记进会话记录。

### 4.3 切条（C 步）

切条由 build.py 自动做；遇到新格式或切坏了，采集方按第 4.9 节修切法。下表是各家族的 cite_id 形式，抄参数时照这个形式引用：

| 家族 | 条文标题的样子 | cite_id 形式 | 状态 |
|---|---|---|---|
| 大陆法规、中文协定 | `第X条`、`一、` | `<doc>#12`、`<doc>#12.1` | 已核 |
| 香港条例（e-Legislation） | `12A.<Tab>标题` | `<doc>#s12A` | 已核 |
| 新加坡法令（SSO HTML） | 页面锚点 `pr12A-` | `<doc>#s12A` | 已核 |
| 英文协定、综合文本 | `ARTICLE 10` + `1.`；MLI 框以 "... of Article 7 of the MLI applies" 开头；修订议定书里 "Article 5 of the Agreement shall be replaced" 这类引用行不当条标题 | `<doc>#10.1`；框内 `<doc>#26.mli7` | 已核（日本财务省发布的 4 份，含 MLI 框；中印 2018 年议定书 13 条；MLI 公约文本 39 条） |
| 协定之后的附件、附表 | 协定最后一条之后的 `ANNEX A`、`Schedule 2` 等标题；从第 1 条重新开始的文书（议定书、旧协定，`ARTICLE IV` 这样的罗马数字照数字记）按条切，其余按编号条目切 | `<doc>#annexB.4`、`<doc>#annexA.2`（新加坡附件 A 的 MLI 修改）、`<doc>#sch2.1`（香港 s.49 令附表 2）；香港令第 1 附表第 2 部的议定书段落 `<doc>#protocol.3`；没有标题、直接接在协定后面的议定书 `<doc>#annex1.3` | 已核（香港 s.49 令 7 份，新加坡税务局协定 PDF 2 份，国家税务总局综合文本后附的议定书） |
| 马来西亚法令 | `109B. 标题`，节号前可能带 `*` | `<doc>#s109B(1)` | 已核（所得税法 1967 重印本，249 节） |
| 泰国税法典 | `มาตรา 70 ทวิ`、`Section 70 Bis` | `<doc>#s70bis(1)` | 已核（第 3 章泰文正本 73 节，英文译本 68 节） |
| 阿联酋法令 | `المادة (45)`、`Article 45 – 标题` | `<doc>#a45(1)` | 已核（2022 年第 47 号法令，阿拉伯文正本与英文译本各 70 条）；阿拉伯文要用法规门户 uaelegislation.gov.ae 的网页，PDF 文字层是乱码，build 会报错 |
| 印尼法律 | `Pasal 26` 独占一行；ayat `(1)`、`(1a)` | `<doc>#26(1)` | 已核（UU 36/2008，25 条） |
| 越南法律、法令 | `Điều 4. 标题`；款 `1.` | `<doc>#4.1` | 已核（67/2025/QH15，20 条） |
| 日本法律（e-Gov XML） | 按 XML 结构切；`第四条の二` → `4-2` | `<doc>#4-2.2` | 已核（法人税法，252 条） |
| 韩国法律（law.go.kr XML） | 按 XML 结构切；`제98조의2` → `98-2`，① → `.1` | `<doc>#98-2.1` | 已核（법인세법，181 条） |
| 印度法律 | `195. Other sums.—(1)`（1961 年法）；`393.<制表符>(1)`（2025 年法） | `<doc>#s195(1)` | 已核（2025 年法经 2026 年财政法修订本，537 节；1961 年法，688 节） |
| 指引、网页 | 编号段落 `5.12` | `<doc>#para5.12` | 已核 |
| 兜底 | 按页 / 整篇 | `<doc>#p3` / `<doc>#all` | — |

**切坏了怎么办**：构建后看 `STATUS.md` 的 Documents 表。法律、法规、协定那几行的 slicing 一列应是本国的切法（如 `cn_article`、`vn_article`、`my_section`）。如果是 `whole`（整篇一条）、`page`（按页），或条数明显不对，就是切坏了。这时先按第 4.9 节修切法；修不好的（如只有扫描件、没有可辨认的条号），参数照样引 `<doc>#all` 或 `<doc>#p3`（引文逐字的检查不受影响），并在会话记录里写一行"<doc_id> 切成 whole/page，条数 N"。

**被议定书或 MLI 替换的条款**：登记进 `superseded.csv`，构建时不进 clause；参数改引议定书的条款。逐条读每份议定书的"取消……用下列规定代替""删除""替换"，每处一行；后来的议定书取消了前一份议定书的条款时，也登记一行（doc_id 写前一份议定书）。被删的款或行会同时从所在条的正文里删掉，所以写到最小的那一款或那几行即可；议定书只改一项或几个字时，删掉那一项的行，note 写明改成了什么。每行一条：

| 列 | 写法 |
|---|---|
| doc_id | 被替换条款所在的文件 |
| clause | cite_id 里 `#` 后面的部分，如 `2.3`；连同其下各款整条替换写 `24*`（只匹配第 24 条及 24.x，不含第 240 条）；整份文件被替换写 `*`；只删条款里的几行写 `13.5@4-`（第 4 行到末尾）、`13.5@4-6`（第 4 到 6 行）或 `13.5@2`（第 2 行）；按句删时写所在条款，或写 `all` 表示在整份文件里找 |
| by | 替换它的条款的 cite_id |
| since | 替换在本方开始适用的日期，YYYY-MM-DD；议定书生效日与适用日不同时，note 里写生效日 |
| note | 说明 |
| phrase | 只删一句话时，把这句话逐字写在这里；其余情况留空 |

### 4.4 抄数（D 步）

读切好的条文，一个数字或一条判定标准一行写进 `param.csv`：

| 列 | 写法 |
|---|---|
| param_id | `<scope>.<slot>.<name>`，如 `cn.outbound_wht.dividend_wht_rate`；同一个 id 需要多行时（不同主体、不同期间）加后缀，如 `cn.final.dividend_tax_rate.2026` |
| scope | 国内法写本地区代码，如 `cn`；协定写地区对，如 `cn-hk` |
| subject | `company`、`individual` 或 `all`（两者都适用） |
| slot | 见下表 |
| name | 小写字母、数字、下划线；优先用下表的名字 |
| value | 单位是 `%`、`days`、`months`、`years`、`count` 或币种时只写数字：5% 写 `5`，不写 `0.05`，也不写 `5%`；单位是 `bool` 时写 `yes` 或 `no`；单位是 `text` 时写条文里的原词 |
| unit | `%`、`days`、`months`、`years`、`count`（个数、层数）、`bool`、`text`，或 jurisdiction.csv 里的币种代码（如 `CNY`） |
| cite_id | 数字所在条款的 cite_id，形式见第 4.3 节 |
| quote | 从条文逐字复制，含该数字或标准所在的整句；构建时检查它逐字出现在 cite_id 所指的条款里 |
| effective_from, effective_to | 法律的生效日、协定的适用起始日，YYYY-MM-DD；来源写在 note |
| note | 税率表网页核对的结果、生效期的来源；网页与条文不一致时不改值，写在这里并记进会话记录 |

| slot | company：收款人是公司 | individual：收款人是个人 | 建议的 name |
|---|---|---|---|
| `outbound_wht` | 本地公司向非居民公司付股息的预提税率及减免条件 | 向非居民个人付股息的预提税率 | `dividend_wht_rate`、`holding_pct_min`、`holding_months_min` |
| `inbound` | 居民公司收到境外股息：是否征税、免税条件、外国税抵免 | 居民个人收到境外股息：是否征税、汇入才征税、外国税抵免 | `foreign_dividend_taxable`、`exemption_holding_pct_min`、`source_tax_rate_min`、`ftc_method` |
| `final` | 股息并入应税所得时的公司所得税率，或本地股息免税 | 个人股息所得税率或免税 | `cit_rate`、`domestic_dividend_exempt`、`dividend_tax_rate` |
| `residence` | 公司居民判定标准 | 个人居民判定（天数等） | `residence_test`、`residence_days_min` |
| `cfc` | CFC 是否适用、低税门槛、控制门槛 | 个人股东适用的 CFC | `cfc_applies`、`low_tax_rate_max`、`control_pct_min` |
| `anti_abuse` | GAAR、协定待遇的国内限制（PPT） | 同左 | `gaar_applies`、`ppt_applies` |

**第三国货币**：协定里的门槛用了 jurisdiction.csv 以外的币种（如 `US$10 million`）时，unit 写 `text`，value 写原文。

**名单**（如 CFC 白名单、低税率国家名单）：名单里的每个国家或地区写一行参数，name 写 `<名单名>_<ISO 两字母代码小写>`，如 `cfc_whitelist_us`；value 写 `yes`，unit 写 `bool`，quote 引名单里列出这个国家的那一行。

**找条款和原句**：`python database/tools/find.py <词> [<词> ...] [--jur <jur>]` 列出含这些词的条款的 cite_id 和词所在的整句，这句可直接当 quote；`python database/tools/find.py --cite <cite_id>` 打印一条的全文。

每个地区每个主体的 6 个槽位都要有着落：至少一个 scope 为本地区代码的参数，或一条缺项记录（decision 的 jur、subject、slot 填上，category 留空，引界定征税范围的条款并逐字摘引）。法律对某个槽位没有规定（如不征股息预提税），就登记缺项记录，不写 value 为空或 none 的参数。

### 4.5 交付

一个地区通过第 5 节验收后，用 upload.py 上传。上传会把远端整个换成本地文件夹里已通过验收的地区的数据：

```bash
python database/tools/upload.py --dry-run   # 先看会传哪些地区、多少行和文件，不写任何东西
python database/tools/upload.py
```

它先做一次全库构建，再逐个地区验收；没通过的地区不上传（有空格但零错误的，加 `--partial` 一并上传，并在会话记录里写明），加 `--jur <地区代码>` 只传指定的地区。上传直接覆盖：原件和纯文本写进存储桶（同名的覆盖），再删掉存储桶里多出来的旧文件；然后在一个事务里删掉远端 schema，按七张表重建并写入全部行，中途失败时旧表原样保留。上传不做比较，也不做事后核对。凭证从 .env 读：`database_url`、`supabase_url`、`supabase_key`（存储桶 `database` 上有一条长期规则，允许公开密钥（`sb_publishable_` 开头）读写这个桶，所以公开密钥就能上传；secret key 或旧版 service_role key 也可以。这条规则让拿到公开密钥的人都能读、改、删桶里的文件，项目负责人已接受；文件被删时，从本地重新上传即可恢复）；没有凭证时，交付物就是整个 `database/` 文件夹（打包发回）。上传的是数据（七张表、`raw/`、`text/`），外加规范和采集任务单的中英文版，在存储桶里是 `docs/spec.zh.md`、`docs/spec.en.md`、`docs/task_sheet.zh.md`、`docs/task_sheet.en.md`；工具和样本不上传。

多人分工时按地区分，一个地区只由一人负责。地区对由字母序在前的地区负责：它的协定文件、协定行和协定参数都由那一方登记（如 `cn-hk` 由 cn 登记，`ae-cn` 由 ae 登记）。多个文件夹合并时，csv 按行合并，`raw/` 按文件合并；id 都带地区前缀，不会冲突。上传会把远端整个换掉，所以多人分工时先合并文件夹，再由一人从合并后的文件夹上传；只用自己的文件夹上传，会把别人已传的数据从远端删掉。

### 4.6 记录

- `blocked.csv`：下载失败的文件，由 `fetch.py --blocked` 写入。
- `session_log.md`：会话记录，每次会话结束时在末尾追加一节（英文），格式见采集任务单；需要人做的事写在其中的 `Handoff to a person` 一项（第 4.8 节），改过的工具写在 `Tool changes` 一项（第 4.9 节）。

### 4.7 人工采集

第 4.1 节的办法都试过仍抓不到时，由人用浏览器取原件，再用 fetch.py 登记。常见四种情况：

| 情况 | 例子 | 人工怎么做 |
|---|---|---|
| 网站拒绝本机访问：403、连不上、人机验证页 | 印度税务局、印尼财政部法规库 | 用普通浏览器打开；仍不行就换一个网络（家庭宽带、当地同事的电脑）下载 |
| 网站太慢，下载中断 | 韩国法令库、India Code | 用 curl 放长超时、断点续传（第 4.1 节第 5 步），或在浏览器里下载 |
| 动态检索系统，没有文件直链 | 马来西亚法律库、越南法规库 | 在网站上检索到这份文件的页面，从页面上下载 |
| 接口要求自己的凭证 | 韩国法令库接口的 OC 编号 | 由人申请：在 open.law.go.kr 注册账号，在 Open API 菜单里申请，勾选要用的接口（至少"法令"），并登记调用方的公网 IP；批准后 OC 就是注册邮箱 @ 前面的部分。把它写进 .env 的 `LAW_GO_KR_OC`，url 里写 `OC=<OC>` |

取原件的要求：

- 下载网站提供的原文件（PDF、XML、Word 等）；网页用浏览器的"另存为 → 网页，仅 HTML"保存。不要打印成 PDF，不要复制粘贴正文，不要截图。
- 下载后核对是否完整：PDF 能翻到最后一页，文件大小与网站标示的一致。
- 记下文件所在页面的地址（浏览器地址栏）；下载链接是临时生成的，就记这个页面地址。

登记：

```bash
python database/tools/fetch.py --register-file <下载的文件> --id <doc_id> --jur <jur> --type <type> --category "<类别>" --title "<原文标题>" --url <官方页面地址> --note "Downloaded manually in a browser on YYYY-MM-DD from <page>; fetch failed: <reason>"
```

同一 id 在 blocked.csv 里有记录的，登记后自动视为已解决。

分工：采集方的 AI 不能用浏览器时，按第 4.8 节转人工（H1），由人来下载和登记。

### 4.8 转人工

采集方的 AI 先按本规范自己解决，只有下表七种情况转给人。转人工不等于停下：其余文件和参数照常做完，只把等人的那几格留着；验收结果照实写，留下的空格就是等人的那几格。

每一项写进会话记录的 `Handoff to a person`，一项一行（英文）：编号、文件 id 或格子（如 `cn|individual|cfc`）、已经试过什么、需要人做什么。

| 编号 | 情况 | 转人工前 AI 先做到 | 人做什么 |
|---|---|---|---|
| H1 | 原件取不到：403、连不上、超时、人机验证页 | 第 4.1 节第 1–7 步都试过，包括同一政府的其他官方站和存档副本；用 `--blocked` 记下（第 8 步下次会话照样重试，抓到了就从交接项里删掉） | 用浏览器或换个网络下载，按第 4.7 节登记 |
| H2 | 需要人的身份：账号、登录、验证码、付费、接受条款，或要登记身份、IP 的接口凭证（如韩国法令库的 OC） | 不绕过；确认没有免登录的官方版本 | 申请或登录后下载；凭证写进 `.env` |
| H3 | 没有可用的文字：扫描件或文字层乱码，又找不到有文字的官方版本 | 找过同一文件的其他格式、网页版和其他官方站点 | 另找版本，或决定这份文件不收 |
| H4 | 官方来源说法冲突：两份官方文件对同一数字、日期或条件说法不同，没有后发文件明确取代 | 按"后发优于先发、正本优于译本、发文机关原件优于转载"比过，仍定不下；这个参数先不写 | 裁定用哪一个 |
| H5 | 效力定不下：没有效力标注，也找不到废止或修订文件，但有迹象表明可能已失效或被改 | 查过法规库的效力标注、发文机关的废止清单和后发文件的废止条款；照常登记，doc 的 note 写 `validity not confirmed` | 确认是否现行 |
| H6 | 只有非官方来源：官方域名上找不到任何版本，存档副本里也没有 | 按第 4.1 节找过；不登记，构建会拒绝非官方地址 | 决定收不收、从哪里收 |
| H7 | 别人的数据与规则改动：发现别人登记的行有误；要改第 4.9 节不许采集方改的部分（表的列、检查和验收规则、上传前的验收门槛）才能继续 | 不改别人的行，不放宽检查；记下完整命令、报错和需要改什么 | 改数据或改规则 |

下面这些不转人工，由 AI 自己做（2026-10-23 中国大陆试跑中都由 AI 完成）：

- 找文件：官方站内检索，发文机关、上级或地方机关网站的转载，存档副本（第 4.1 节）。
- 定效力和日期：法规库的效力标注，后发文件的废止条款，生效执行的公告或通知，官方编订文本的脚注。
- 判断 MLI 是否适用：匹配数据库打不开时看一方的立场文件（第 4.2 节）。
- 找出议定书和 MLI 改了哪些条款：逐条读原文，登记 superseded.csv（第 4.3 节）。
- 切坏了、工具出错、网站有特殊情况：按第 4.9 节自己修工具；修不好的切法按第 4.3 节引 `#all` 或按页引，写进会话记录的 Slicing problems。
- 归类：按第 2 节的定义判断，拿不准时在 note 写理由。
- 本地语言正本与英文译本不一致：参数引正本。

### 4.9 维护工具

`database/tools/` 由采集方维护。遇到新格式、切坏了、网站有特殊情况或工具出错时，自己改代码；改完按下面的检查确认没有改坏别的文件和地区。怎么写一种新切法，见 `samples/` 下 README 的 "How a slicer is written" 一节。

**可以改**
- 切法：build.py 的 `slice_*` 函数和按地区、类型分派的 `slice_doc`（新格式、切坏、条号写法）。切法的说明（docstring）写明核过哪些文件、各切出多少条。
- 抓取：fetch.py 里某个网站的特殊处理（cookie、分段加载、等待和重试间隔）；官方域名表 `OFFICIAL` 里补漏掉的政府或官方机构域名。
- 上传：upload.py 的连接、凭证和存储接口。
- 新增辅助脚本。

**不能改**（要改的转人工，第 4.8 节 H7）
- 七张表的列（build.py 的 `TABLES`），id、日期、单位、引文逐字等检查，以及覆盖和验收的判定：放宽检查等于让错的数据通过验收。
- upload.py 上传前的验收门槛：没通过验收的地区不上传。
- 别人登记的数据行。

**改完要做的检查**（缺一项不算改完）
1. 改之前保存当前的条款编号：`python database/tools/clause_diff.py --save`。
2. 跑样本：`python database/samples/slicers-2026-10-23/run_slicers.py`，结果与样本 README 的结果表一致；有意改变的，更新那张表并写明原因。
3. 全库构建：`python database/tools/build.py`，零错误。
4. `python database/tools/clause_diff.py`：列出条款编号有变化的文件；参数、缺项记录或 superseded.csv 还在引用的编号消失时它报错，在同一次修改里把引用改好。
5. 已经通过验收的地区逐个重跑 `python database/tools/build.py --jur <地区>`，都要仍是 `PASSED`。
6. 新格式：把原件放进 `samples/` 下的文件夹，在 run_slicers.py 加一项，在样本 README 的结果表加一行，并在第 4.3 节的表里补一行或改状态。

**记录和交付**：会话记录写 `Tool changes` 一项：改了哪个文件、为什么、在哪些文件上核过、上面检查的结果。upload.py 只上传数据，不上传工具，所以改过工具的，把 `tools/` 和 `samples/` 连同数据一起交回；几个人改了同一个工具时，合并后每个地区重跑验收。

## 5. 验收（采集方，按地区）

一个地区采完后运行：

```bash
python database/tools/build.py --jur <地区代码>
```

它只检查这个地区的数据，不写任何产物。零错误、零空格时输出 `PASSED`（退出码 0），即验收通过；否则逐条列出错误和空格。

检查的数据：该地区的文件和缺项记录，该地区及其地区对的参数、协定文件和协定行，以及 intl 文件。

**错误**：
- 文件缺失、哈希不一致、抽不出文本、阿拉伯文文字层是乱码，url 不在官方域名上，类型或类别不合法，lang 为空，id 前缀不对，协定文件的 jur 不是地区对；
- 参数的 cite_id 不存在、引文不逐字，scope、subject、slot、name、unit 不合法，param_id 不是 `<scope>.<slot>.<name>`，value 与单位不符；
- 缺项记录没有 jur，或 category 与 subject + slot 不是二选一，或第 1–4、9 类和槽位的缺项没引征税范围条款；
- 协定行的地区对写法不对，或引用的文件不存在；
- 日期不是 YYYY-MM-DD（文件、参数的生效日期，协定行的生效日，superseded.csv 的 since）。

**空格**：
- 12 类（9 类内容 + 3 类网页）里既没有文件也没有缺项记录的类；
- 公司、个人各 6 个槽位里既没有本地区参数也没有缺项记录的槽位；
- 该地区负责的地区对（字母序在前的那一方）里没有 treaty 行的；没有协定的，doc_id 留空、note 写"无协定"；
- blocked.csv 里该地区还没进 doc.csv 的下载；确认不需要的，删掉这一行，并在会话记录里写明原因。
