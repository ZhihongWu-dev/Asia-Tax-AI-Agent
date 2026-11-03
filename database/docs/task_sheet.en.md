# Collection task sheet

English copy of `采集任务单.md`. If the two differ, the Chinese version applies.

This task sheet lists, in order, what to do for each jurisdiction. Each step names the matching section of the spec (`数据库规范.md`, English copy `database_spec.en.md`), which holds the full explanation. Text that the AI writes into the csv files (statement, note) and the session log is in English; quotes and titles stay in the original language.

## 0. Once only: set up the environment

Run in the project root (the folder above `database/`):

```bash
conda create -n tax python=3.11
conda activate tax
pip install -r database/requirements.txt
```

If the originals include .doc, .rtf, .xls or .ppt files, also install LibreOffice. From then on, run every command in the project root, in the `tax` environment.

## 1. For each jurisdiction, in this order

Below, `<jur>` stands for the jurisdiction code (`cn hk sg id vn my th ae jp kr in`).

1. **List** (spec §2, §4.1): go through the 9 content categories and 3 kinds of pages one by one, find the documents on official websites, and note their addresses. Then list the pairs this jurisdiction owns (the alphabetically first side owns a pair: cn owns cn-hk and cn-sg; ae-cn belongs to ae), and check whether each pair has a treaty. Collect the English text of a treaty first; without one, the Chinese text. Then check whether the MLI applies and whether there is a synthesised text (spec §4.2). Where one side made a reservation under MLI Article 35(7) (such as Hong Kong), the date the MLI starts to apply follows the notification dates published by the OECD.
2. **Fetch** (spec §4.2): run fetch.py once per document; `--category` gives the categories it belongs to. If a download fails, try the 8 steps of spec §4.1. If all of them fail, record it with `--blocked` and collect it by hand following spec §4.7. If it still cannot be had, hand it to a person (spec §4.8, H1). Where the English text is itself authentic (such as the laws of Hong Kong and Singapore), register only the English text. Where there is a local-language original and an English translation, register both (beginning of the spec). A list page that comes down as an empty shell is registered anyway, with a note saying so (spec §4.1).
3. **Build**: run `python database/tools/build.py`. Open the Documents table in `database/STATUS.md` and check that the text column of every document is `ok`. Then check that the slicing column of laws, regulations and treaties shows the jurisdiction's own slicer, not `whole` or `page`. If a document is sliced badly, first fix the slicer following spec §4.9. If it cannot be fixed, carry on as usual and record it in the session log (spec §4.3).
4. **Replaced clauses** (spec §4.3, §4.2): read every protocol and every MLI modification for "cancelled, replaced, deleted", and register each one as a row in `superseded.csv`; then build again. Where the synthesised text does not merge the protocols, register one row for the original treaty and one for the synthesised text. Where a later protocol cancels an article of an earlier protocol, register a row for that too. The bracketed "[REPLACED by …] [original text]" passages in synthesised texts are registered as well.
5. **Copy parameters** (spec §4.4): find the clause with `python database/tools/find.py <words> --jur <jur>`; it gives the cite_id and the whole sentence, which can be used directly as the quote. Write `param.csv` following the examples, one number per row. Lists get one row per country (spec §4.4). For pairs with an MLI synthesised text, treaty parameters cite the synthesised text. Singapore's treaty PDFs list the MLI amendments in Annex A: the PPT cites `#annexA.<item>`, and that PDF goes into both doc_id and mli_doc_id. Where the MLI applies but there is no synthesised text, cite the article of the MLI convention (such as `intl.oecd.mli.en#7.1`). A threshold in a third country's currency (such as US$10 million) has unit `text`.
6. **Absence records** (spec §2, §4.4): when a category has no document, or the law says nothing for a slot of a subject, write a row in `decision.csv`. One fact may need two rows, one for the category and one for the slot: "no CFC" means both that category 3 has no document and that the cfc slot has no rule.
7. **Treaty rows** (spec §3, §4.5): write one row in `treaty.csv` for each pair this jurisdiction owns. Where there is no treaty, leave doc_id empty and write "No treaty" in the note. Do not register pairs you do not own.
8. **Acceptance** (spec §5): run `python database/tools/build.py --jur <jur>` and fix every error and gap line of the output until it prints `PASSED`.
9. **Session log**: add a section at the end of `database/session_log.md`; the format is in part 4. Any of the seven cases of spec §4.8 goes under Handoff to a person; solve every other problem yourself following the spec, without handing it over.
10. **Upload** (spec §4.5): first look at the plan with `python database/tools/upload.py --dry-run`, then upload without `--dry-run`. The upload replaces the whole remote with the data of the locally accepted jurisdictions: when several people share the work, merge the folders first and let one person upload. Without remote credentials, pack the whole `database/` folder and send it back.

## 2. Command examples

```bash
# Fetch a law
python database/tools/fetch.py --id cn.law.eit --jur cn --type law --category "1;3;4" --title "中华人民共和国企业所得税法" --url http://www.npc.gov.cn/zgrdw/npc/xinwen/2019-01/07/content_2070260.htm --lang zh --effective 2008-01-01

# Fetch an announcement and its attachments (the State Taxation Administration's site needs the curl engine)
python database/tools/fetch.py --id cn.sta.2019-35 --jur cn --type guidance --category "5;7" --title "国家税务总局关于发布《非居民纳税人享受协定待遇管理办法》的公告" --url https://fgk.chinatax.gov.cn/zcfgk/c100012/c5194891/content.html --lang zh --with-attachments --engine curl

# Fetch a treaty: --jur is the pair, in alphabetical order; treaties need no --category
python database/tools/fetch.py --id treaty.cn-hk.2006.zh --jur cn-hk --type treaty --title "内地和香港特别行政区关于对所得避免双重征税和防止偷漏税的安排" --url https://www.chinatax.gov.cn/chinatax/n810341/n810770/c1153751/5131982/files/11537511.pdf --lang zh

# Only an archived copy could be had: --url is the original official address, --note the source of the copy
python database/tools/fetch.py --register-file <path of the local copy> --id id.uu36-2008 --jur id --type law --category "1" --title "UU No. 36 Tahun 2008" --url https://jdih.kemenkeu.go.id/fulltext/2008/36TAHUN2008UU.htm --lang id --note "Internet Archive copy, timestamp <timestamp>"

# Every method was tried and the download still fails
python database/tools/fetch.py --blocked --id in.ita2025 --jur in --title "Income-tax Act, 2025" --url https://www.incometaxindia.gov.in/ --reason "HTTP 403" --alt-tried "<methods tried, separated by semicolons>"

# Korean legal database: write OC=<OC> in the url; the id goes into LAW_GO_KR_OC in .env (spec §4.7)
python database/tools/fetch.py --id kr.cita --jur kr --type law --category "1;3;4" --title "법인세법" --url "https://www.law.go.kr/DRF/lawService.do?OC=<OC>&target=law&type=XML&LM=법인세법" --lang ko

# Find a clause and its sentence
python database/tools/find.py 减按10% --jur cn

# Upload: the whole remote is replaced by the locally accepted jurisdictions
python database/tools/upload.py --dry-run
python database/tools/upload.py

# Before and after changing database/tools/ (spec §4.9)
python database/tools/clause_diff.py --save
python database/samples/slicers-2026-10-23/run_slicers.py
python database/tools/build.py
python database/tools/clause_diff.py

# Browse the library: on the map, jurisdictions are nodes, treaties and one-way lists are edges; click to see documents, parameters and clauses (read-only, reads the csv files on every load)
python database/viewer/server.py      # then open http://127.0.0.1:8770

# Build the whole library; accept one jurisdiction
python database/tools/build.py
python database/tools/build.py --jur cn
```

`doc.csv` is written by fetch.py; do not fill it by hand. Only when a category is wrong, edit its category column directly.

## 3. Example csv rows

Every row below is a real row of the library, built with zero errors. Follow the format; do not copy the content.

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

**decision.csv** (absence records: fill either category, or subject and slot)

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

A pair with no treaty is written like the hk-sg row: doc_id empty, a note that starts with `No treaty` and says which list pages were checked; the codes in alphabetical order.

**superseded.csv**

```csv
doc_id,clause,by,since,note,phrase
treaty.cn-hk.2006.zh,13.5,treaty.cn-hk.2006.p2.zh#5,2008-06-11,"Replaced by the Second Protocol, in force 2008-06-11.",
treaty.cn-hk.2006.zh,2.3@2-4,treaty.cn-hk.2006.p2.zh#1,2008-06-11,"Item (1) (Mainland taxes) replaced by the Second Protocol, in force 2008-06-11.",
treaty.hk-jp.2010.mli.en,26@3-8,treaty.hk-jp.2010.mli.en#26.mli7,2023-04-01,The bracketed former Article 26 text. Replaced by MLI Article 7(1) (principal purpose test); the MLI has effect in Hong Kong from 2023-04-01 for taxes withheld at source and from years of assessment beginning on or after 2024-04-01 for other taxes.,
treaty.sg-th.2015.en,annexB*,treaty.sg-th.2015.en#27.3,2017-01-01,The 1975 Convention printed in Annex B ceased to have effect once this Agreement took effect (Article 27(3)).,
```

## 4. Session log format

At the end of every session, add to the end of `database/session_log.md`:

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

Write `none` for an empty item; do not delete the line. When Tool changes has content, say which file was changed, why, which documents it was checked on, and the results of the six checks of spec §4.9. When Handoff to a person has content, put each item on its own line, starting with its code from spec §4.8, and say what was tried and what the person needs to do:

```markdown
- Handoff to a person:
  - H1 in.itr2026: <official page url>; tried requests, curl and the Internet Archive; HTTP 403 every time. Download it in a browser and register it (§4.7).
  - H2 kr.law.cit: the law.go.kr API needs an OC id and .env has none. Apply for one (§4.7).
```

## 5. When you see these errors

| Error in the output | What to do |
|---|---|
| `doc …: file missing` | The original is not under raw/: fetch it again with fetch.py; do not edit the file column of doc.csv by hand |
| `doc …: sha256 differs` | The original was changed: fetch it again with `--force` |
| `doc …: no text (scanned_or_empty)` | A scan without a text layer: find a version with text; if there is none, hand it to a person (H3) |
| `doc …: category empty` or `category … not in` | Fix the category column of that row of doc.csv |
| `doc …: id may only hold ASCII letters` or fetch reports `--id may only hold ASCII` | Use only English letters, digits, dot, underscore and hyphen in ids |
| fetch reports `HTTP 202` (Singapore Statutes Online) | This is the site's bot check: fetch again after a few minutes to an hour, do not retry in a row; if it never works, hand it to a person (spec §4.8, H1) |
| `the url needs the OC id of law.go.kr` | Put `LAW_GO_KR_OC=<your id>` in .env; without an id yet, hand it to a person (H2), who applies following spec §4.7 |
| `doc …: lang empty` | Add the language code to that row of doc.csv; in future pass `--lang` to fetch |
| `doc …: id must start with …` or `decision …: id must start with …` | Change the id as shown; a doc id must be registered again with `--force` |
| `doc …: Arabic text layer garbled` | The text of this Arabic PDF is garbled: register the page of uaelegislation.gov.ae instead |
| `… must be a date written YYYY-MM-DD` | Write the date like `2026-01-01` |
| `doc …: a treaty document's jur must be its pair` | Register it again with `--force` and the pair as `--jur` |
| `doc …: url … is not on an official host` | Change the url to the official website's address; the source of a copy goes into the note. If it really is a government site missing from the list, add it to `OFFICIAL` in fetch.py following spec §4.9 |
| `param …: cite_id not found` | Find the right cite_id with `find.py <a few words of the quote>` |
| `param …: quote not found verbatim` | Take the sentence again with `find.py`, or read the whole clause with `find.py --cite <cite_id>` and copy it without changing a character |
| `param …: param_id must be …` | Change it to `<scope>.<slot>.<name>` as shown |
| `param …: value … must be a plain number` | Write only the number in value; the unit goes in the unit column |
| `param …: unit … not in` | Change it to `%`, `days`, `months`, `years`, `count`, `bool`, `text` or a currency code |
| `decision …: … must cite the clause` | Add the cite_id and the verbatim quote of the clause that sets the scope of the tax |
| `decision …: an absence record needs jur and either category, or subject and slot` | jur is required; fill either category or subject + slot, not both |
| `treaty …: write the pair in alphabetical order` | Write the pair in alphabetical order, such as `cn-hk` |
| `treaty …: doc_id … not in doc` | Register the treaty with fetch.py first |
| `superseded.csv: phrase not found` | The phrase must match the clause character for character |
| upload reports `upload of … failed: HTTP 400` (403 or row-level security) | The rule on bucket `database` that lets the publishable key read and write it is gone: hand it to a person (H7), or put a secret key in .env (spec §4.5) |
| clause_diff reports `… cites …, which no longer exists` | A tool change altered clause ids: find the new id with `find.py`, fix the citation, and run the checks again |
| fetch, build or upload reports a `Traceback`, or an error not in this table | Fix the tool following spec §4.9 and finish the six checks; if the table columns or the check rules need changing, hand it to a person (H7) |
| `gap: category …` | Add a document for this category, or write an absence record |
| `gap: slot … without a parameter` | Add a parameter for this slot, or write an absence record |
| `gap: pair … without a treaty row` | Add a row to treaty.csv |
| `gap: download not resolved` | Collect it by hand following spec §4.7 and register it under the same id; if you cannot use a browser, hand it to a person (H1); if it is not needed after all, delete the row from blocked.csv and give the reason in the session log |

## 6. Do not

- Do not change `database/tools/` without the six checks of spec §4.9; do not loosen checks, and do not change the table columns or the acceptance rules (hand those to a person, H7).
- Do not edit `clause.csv`, `files.csv`, `text/`, `database.sqlite` or `STATUS.md` by hand; every build rewrites them.
- Do not make up numbers: every parameter needs a quote copied verbatim from the clause.
- Do not use third-party websites as sources; an archived copy can only be registered with `--register-file`, with `--url` set to the original official address.
- Do not bypass captchas, bot checks or login walls.
- Do not delete or change rows registered by others; hand errors you find in them to a person (H7).
- Do not stop the rest of the work because one item was handed over; problems outside the seven cases of spec §4.8 are not handed over.
