# Database specification (minimal set)

English copy of `数据库规范.md`. If the two differ, the Chinese version applies.

This specification is written in Chinese, for people to read. Text that an AI writes into files (statement, note, session_log.md) is in English. Originals, legal provisions, quotes and document titles stay in their original language and are not translated. When a law exists both as an authentic text in the local language and as an English translation, register both and cite the authentic text in parameters. When the English text is itself authentic (for example the laws of Hong Kong and Singapore), register only the English text. When only an English translation is available, write "unofficial translation" in the note.

2026-10-23. Goal: a minimal database supporting the "Asian cross-border dividend optimisation" workflow (recipients split into companies and individuals; 11 jurisdictions: Mainland China, Hong Kong, Singapore, Indonesia, Vietnam, Malaysia, Thailand, UAE, Japan, Korea, India).

English copies: `database/database_spec.en.md` (this specification), `database/collection_task_sheet.en.md` (the task sheet) and `database/database_mcp_spec.en.md` (the MCP spec). If they differ, the Chinese versions apply. When you change a Chinese version, change its English copy too.

Before you start, read the task sheet (`采集任务单.md`, English copy `collection_task_sheet.en.md`): it lists, in order, the commands to run for each jurisdiction and example rows for each csv. This specification is the full reference it points to.

**Change record**: one row for each change to the specification. Jurisdictions that have passed acceptance fill in the cells in the column "Cells to fill". `SPEC_VERSION` in `build.py` is the date of the last row; the upload writes it into the remote meta table (§3, §4.5).

| Date | What changed | Cells to fill |
|---|---|---|
| 2026-10-23 | first version | — |
| 2026-10-31 | new slot penalty, category 10 (penalties), category 11 (interpretive sources, not counted); param gains the columns changed_on and superseded_by | category 10 of every jurisdiction; penalty for companies and individuals |
| 2026-10-31 | new slot restructure; category 9 widened to the tax burden of share transfers | restructure for companies and individuals |
| 2026-11-02 to 11-04 | new exit slot for individuals (deemed transfer on departure) | exit for individuals |
| 2026-11-04 | exit widened to a company moving out (deemed liquidation) | exit for companies |
| 2026-11-07 | after merging the remote library: OCR of scans (§4.1); errors on law pages that are shells, warnings on whole-text citations of laws (§4.1, §4.3, §5); bilingual gazettes, several laws in one gazette issue (§4.2); slicing of Malaysian schedules, headings before the number, Korean law PDFs (§4.3); quotes taken from find.py, the subject suffix of parameter ids (§4.4); tools for merging and repointing, the owner of intl documents, the remote meta table, uploading superseded.csv and `ocr/` (§3, §4.5); §6 widening the income tax scope (draft, not in force) | no new cells |

## 1. Minimal workflow

```text
Official websites (tax authority / ministry of finance / legal database / gazette)
   │  for each jurisdiction, collect the 10 content categories + 3 page categories item by item; each item has 0, 1 or more documents; one complete treaty per jurisdiction pair (list in §2)
   │  how: see §4
   ▼
A  Originals
   raw/<jur>/<doc_id>.<ext> (saved as is)  +  text/<doc_id>.txt (plain text; scanned pages take the OCR text of ocr/<doc_id>.txt)
   ──▶ files (path, hash, bytes)
   ▼
B  Registration
   doc (one row per document: jurisdiction, type, category, title, source URL, file path, hash, language, validity period)
   decision absence records (one row when a jurisdiction has no document for a category, or the law has no rule for a subject's slot: jurisdiction, category or subject + slot, statement, quote)
   treaty (one row per jurisdiction pair: treaty doc_id; with no treaty, leave doc_id empty and say so)
   ▼
C  Slicing
   clause (one row per provision: cite_id = <doc_id>#<number>, text verbatim, unchanged)
   ▼
D  Extracting values
   param (one row per number or criterion: slot × subject × jurisdiction or pair → value, unit, verbatim quote, cite_id, validity period)
   ▼
E  Coverage check
   11 jurisdictions × 13 categories (10 content + 3 page categories; category 11, interpretive sources, is not counted): each cell has a document or an absence record
   11 jurisdictions × {company 9 slots, individual 9 slots}: each cell has a parameter or an absence record
   55 jurisdiction pairs: each pair has a treaty row or a "no treaty" row
```

## 2. What to collect for each jurisdiction (minimal scope)

Check each jurisdiction against the 10 content categories and 3 page categories below, and collect one complete treaty for each jurisdiction pair; category 11 (interpretive sources) is optional.

A category means content, not a number of files: one item may have 0, 1 or more documents, and one document may belong to several categories (categories 1, 3 and 4 are often in the same income tax law). Each document records in `doc.category` the categories it belongs to; values are `1`–`11`, `page_treaties`, `page_rates`, `page_deadlines`, separated by semicolons.

When a jurisdiction has no document for a category, register an absence record in the `decision` table: fill in `jur` and `category`, and say in `statement` what is missing and where you looked. Absence records for categories 1–4 and 9 must cite the provision that defines the scope of the tax, with a verbatim quote. For categories 5–8 and the pages, a citation may be left out when there is no provision to cite.

**10 content categories per jurisdiction (category 11 optional)**

1. Four parts of the income tax law: withholding tax on outbound dividends (rates, exemptions); taxation of foreign dividends received and the conditions for exemption (including the conditions of a foreign income exemption regime, such as a minimum tax rate at source); corporate residence; the method and limit of the foreign tax credit.
2. Three parts of the individual income tax law: tax rate on individuals' dividends or exemption; individual residence; foreign tax credit for individuals.
3. CFC provisions and their attached lists (white lists, low-tax lists, exemption conditions).
4. Anti-abuse provisions: GAAR, and domestic limits on treaty benefits (provisions implementing a PPT).
5. Documents on the factors for determining the beneficial owner (announcements / guidance).
6. Guidance on residence (place of effective management standard, counting an individual's days of residence); needed only when the law refers to guidance.
7. Documents and forms for the procedure to claim or file for treaty benefits (who files, when, what).
8. Procedure for the certificate of residence (conditions of issue, how to apply).
9. Tax provisions on share transfers and on a company moving out, only for the one-off cost of setting up a structure: the deemed liquidation of a company that leaves (such as Mainland Caishui [2009] No. 59 item 4 and No. 60); income tax on transfer gains (including deemed disposals and indirect transfers by non-residents), stamp duty on share transfers (rate, base) and the valuation rules for unlisted shares (net assets, appraisal). Other stamp duties and deed tax are not collected: deed tax concerns immovable property only.
10. Penalty provisions: surcharge or interest on tax paid or remitted late (rate, start, cap), fine multiples for tax underpaid or not withheld (minimum, maximum), additional taxes. Collect only the provisions that carry the figures; they feed the "exposure if a benefit is denied" computation. Usually in the tax administration act, the general rules act or the penalty chapter of the income tax act.
11. Interpretive sources (optional): court decisions, the OECD Model commentary, rulings on individual cases. They may be cited only by rule-layer decisions to explain a reading; **never as the source of a parameter**: the build reports an error when `param.cite_id` points into a document that belongs to category 11 only. The coverage check ignores this category.

**3 page categories per jurisdiction**: the treaty list page (`page_treaties`, dates of entry into force), the withholding tax rate table (`page_rates`, for cross-checking, not a source to cite), and the page on withholding tax filing deadlines (`page_deadlines`).

**Each jurisdiction pair**: the complete treaty + protocols + MLI synthesised text, using Articles 1–4 (scope, residence, tie-breaker rules), Article 10 and the definition of "beneficial owner", the article on eliminating double taxation, and limitation on benefits / PPT. Register the whole text, and extract parameters only from the provisions needed. Pairs with no treaty also get a "no treaty" row. For the MLI, see §4.2.

If any item is missed, the corresponding rate, condition, certificate or timeline has no source.

## 3. Minimal database structure

```text
                 ┌──────────────┐
                 │ jurisdiction │ 11 rows, prefilled
                 └──────┬───────┘
                        │ 1:n
   ┌──────────┐   ┌─────▼─────┐        ┌────────┐
   │  files   │◀──│    doc    │───────▶│ treaty │ 55 rows, one per jurisdiction pair
   │ in bucket│   │ a document│ 1:0..1 │        │
   └──────────┘   └─────┬─────┘        └────────┘
                        │ 1:n
                  ┌─────▼─────┐
                  │  clause   │ one provision, text verbatim
                  └─────┬─────┘
                        │ 1:n
                  ┌─────▼─────┐
                  │   param   │ one number, with a verbatim quote
                  └───────────┘

   decision: absence records; one row = a jurisdiction has no document for a category, or the law has no rule for a subject's slot (cites a clause)
```

| Table | Columns | Index |
|---|---|---|
| `jurisdiction` | code (two lower-case letters; a pair is written in alphabetical order as `cn-hk`), name, currency, company_in_scope, individual_in_scope (prefilled) | — |
| `files` | path, sha256, bytes | path |
| `doc` | id, jur (jurisdiction code; treaties and protocols take the pair, such as `cn-hk`; multilateral documents such as the MLI take `intl`), type, category (the categories of §2, several allowed, separated by semicolons), title, url, file, sha256, lang (required; the document's language code, such as zh, en, th, ar), effective_from, effective_to, note | id |
| `treaty` | pair, doc_id (empty = no treaty), in_force_from, mli_doc_id, note | pair |
| `clause` | cite_id, doc_id, label, text | cite_id, doc_id |
| `param` | param_id, scope (jurisdiction or pair), subject (company / individual / all), slot (outbound_wht / inbound / final / residence / cfc / anti_abuse / penalty / restructure / exit), name, value, unit, cite_id, quote, effective_from, effective_to, note, changed_on, superseded_by | param_id |
| `decision` | id, jur, category, subject, slot, statement, cite_id, quote (each row is an absence record: fill in either category, or subject and slot; see §2 and §4.4) | id |

**What each table and column means** (all examples are real rows of the library)

`jurisdiction`: the jurisdictions covered, one row each, prefilled; do not change.
- code: jurisdiction code, two lower-case letters, such as `cn` (Mainland China) and `hk` (Hong Kong). Two jurisdictions forming a "pair" are joined in alphabetical order, such as `cn-hk`; pairs are used for treaties and treaty parameters.
- name: name of the jurisdiction.
- currency: code of the local currency, such as `HKD`; parameter units may use it.
- company_in_scope, individual_in_scope: whether rules for companies and for individuals are collected for this jurisdiction (yes / no). The coverage check uses them to decide whether to check the 9 slots of that subject.

`doc`: one original document in the library: a law, an announcement, a web page, or a treaty or protocol.
- id: document id, such as `cn.law.eit` (Enterprise Income Tax Law) and `treaty.cn-hk.2006.zh` (Chinese text of the Mainland–Hong Kong Arrangement). It starts with the jurisdiction code, `treaty.<pair>.` or `intl.`.
- jur: the jurisdiction the document belongs to. Treaty documents take the pair; multilateral documents such as the MLI take `intl`.
- type: kind of document: law, regulation, guidance (announcements, guidance), treaty (treaty documents), form, page (web page).
- category: which categories of §2 it belongs to, such as `1;3;4`.
- title: original title, not translated.
- url: official source address.
- file: local path of the original, such as `raw/cn/cn.law.eit.html`.
- sha256: fingerprint of the original. If the original is changed, the build reports an error.
- lang: language of the original, such as zh, en.
- effective_from, effective_to: dates the document takes and ceases to have effect; fill in only when known.
- note: additional information, such as how it was fetched, validity labels, the source of a copy.

`files`: one row for each original (`raw/`), each OCR text of a scan (`ocr/`) and each plain text extracted (`text/`); generated by the build.
- path: file path, which is also its name in the remote storage bucket.
- sha256, bytes: fingerprint and size of the file.

`clause`: one provision sliced from a document (an article, a paragraph, a section or a page), text verbatim; generated by the build.
- cite_id: provision id, that is the document id + `#` + the number, such as `cn.law.eit#26` (Article 26), `hk.cap112#s26` (section 26), `treaty.cn-hk.2006.zh#10.2` (Article 10, paragraph 2). Parameters and absence records use it to point to their source.
- doc_id: the document the provision is in.
- label: the number for people to read, such as "第26条" or "Article 10(2)".
- text: original text of the provision, unchanged.

`treaty`: whether two jurisdictions have a tax treaty; one row per jurisdiction pair (55 pairs in all).
- pair: the pair, such as `cn-sg`.
- doc_id: the treaty document; empty means the two have no treaty.
- in_force_from: date the treaty entered into force.
- mli_doc_id: the MLI synthesised text, that is the treaty as modified by the MLI; empty if there is none.
- note: whether the MLI applies, from which date, and the source of the dates.

`param`: one number or criterion extracted from a provision; the core content of the library.
- param_id: parameter id, that is scope.slot.name, with a suffix when needed, such as `cn.outbound_wht.dividend_wht_rate` (Mainland China's withholding tax rate on dividends paid abroad).
- scope: where it applies. Domestic law takes the jurisdiction code (such as `cn`); treaties take the pair (such as `cn-hk`).
- subject: whom it applies to: company (the recipient is a company), individual (the recipient is an individual), all (both).
- slot: which stage of the tax burden on dividends:
  - outbound_wht: withholding tax when a local company pays dividends abroad;
  - inbound: how foreign dividends received by a resident are taxed, exempted and credited;
  - final: the final tax rate once dividends are part of taxable income, or the exemption of domestic dividends;
  - residence: what makes a person a local resident;
  - cfc: controlled foreign company rules;
  - anti_abuse: general anti-avoidance rules, and limits on treaty benefits (PPT);
  - penalty: surcharge / interest on late payment, fine multiples for tax underpaid or not withheld; subject is normally `all`;
  - exit: the tax on leaving the jurisdiction: for an individual, the income tax on the assets deemed transferred on departure (thresholds, years of residence, rate, base); for a company that moves its registration or its place of effective management out, the deemed liquidation or disposal (whether it is deemed, the base of the liquidation income, the rate, the shareholder's dividend and gain). The company part was added by the user's decision of 2026-11-04;
  - restructure: the one-off tax on transferring shares of a company of this jurisdiction: income tax on the gain (rate, base, indirect transfers, safe harbours, treaty Article 13), stamp duty on the transfer, valuation rules for unlisted shares. subject is the transferor's type.
- name: what the number is, such as dividend_rate (tax rate on dividends) and holding_pct_min (minimum shareholding).
- value, unit: value and unit, such as `10` and `%`, `12` and `months`, `yes` and `bool`.
- cite_id, quote: the source provision and a verbatim quote. The build checks that the quote really appears in that provision.
- effective_from, effective_to: from which date and until which date the number applies.
- note: explanation, such as conditions, exceptions, the source of the dates.

`decision`: absence records, stating "this does not exist", to tell it apart from "not collected yet". Each row fills in either category, meaning the jurisdiction has no document of that category (for example, Hong Kong has no CFC rules), or subject and slot, meaning the law has no rule for that stage (for example, Hong Kong levies no withholding tax on dividends).
- id: id, such as `hk.absent.cfc`.
- jur, category, subject, slot: which jurisdiction's category, or which subject's stage, is missing.
- statement: what is missing, why, and where you looked.
- cite_id, quote: the provision defining the scope of the tax and a verbatim quote, showing that the rule really does not exist.

**Remote**: after upload, the seven tables are in the schema `database` of the remote Postgres, next to the archived library's schema `official`; the files listed in the `files` table are in the storage bucket `database`. They are real tables that can be queried directly, not a snapshot, but they change only on upload: each upload replaces them entirely with the local data that passed acceptance, and no earlier versions are kept. The same schema holds a table `meta` (key, value) with the upload's specification version (`spec_version`, that is `SPEC_VERSION`), the sha256 of build.py and upload.py, the git commit of the tools, the uploader, the time and the acceptance result of each jurisdiction; it shows which version of the specification and tools wrote the remote, and upload.py uses it to refuse overwriting newer data with older tools (§4.5).

**Local file convention**: locally, each table is a csv of the same name, kept with `raw/`, `ocr/` and `text/` under `database/` (`ocr/` holds the OCR texts of scans, made by tools/ocr.py; it is an input of the build and is delivered with the data, §4.1). The five csv files `jurisdiction / treaty / doc / param / decision` are filled by an AI or by hand (`jurisdiction.csv` is prefilled; `doc.csv` is written through fetch.py); `files.csv` and `clause.csv` are generated by the build and not filled by an AI or by hand. fetch.py also writes `blocked.csv`, and the session record is kept in `session_log.md`. Text that an AI writes into the csv files (statement, note, etc.) and the session record are in English; quotes and titles stay in the original. There is also an auxiliary csv, `superseded.csv` (doc_id, clause, by, since, note, phrase), filled by an AI or by hand, which records provisions replaced by protocols or the MLI. It is not a library table; the build uses it only to leave those provisions out of `clause`; it is uploaded to the bucket with the data, so that the same clause layer can be rebuilt from the remote (§4.5).

**Build**: run `python database/tools/build.py`. It converts the originals into `text/`, slices them, generates `clause.csv` and `files.csv`, runs all checks, and writes `database.sqlite` and `STATUS.md`. With `--jur <jurisdiction code>` it checks only that jurisdiction and writes nothing (§5). On errors the exit code is 1; coverage gaps are only listed in `STATUS.md` and do not count as errors.

**Environment**: Python 3.11; dependencies and the install command are in `database/requirements.txt`. Originals in .doc / .rtf / .xls / .ppt also need LibreOffice, whose path is set in `SOFFICE` at the top of build.py.

## 4. How to collect the data

Collectors first finish everything locally following the local file convention of §3, then deliver it as a whole (§4.5). Each step corresponds to A–D of §1.

### 4.1 Choosing sources

- Official domains only: tax authority, ministry of finance, legal databases, gazettes. Third-party reproductions, law firm summaries and wikis are not accepted; rate table pages are only for cross-checking. The build reports an error for a document whose url is not in the official domain list (`OFFICIAL` in fetch.py). When a government domain is missing from the list, add it to `OFFICIAL` under §4.9 and note it in the session record; do not switch to a third-party address.
- Prefer the current consolidated version. Where there is none, collect the original law plus each amendment, and say in the note which provisions have been amended.
- For treaties, prefer the English text (in most treaties the English text is one of the equally authentic texts); without one, take the Chinese text; with neither, take the text in an official language of one party and say so in the session record (such a text can only be sliced by page or as a whole).
- Record one alternative address for each document. fetch.py retries twice automatically. If it still fails, try the methods below in order; only when all fail, write the document into blocked.csv with `fetch.py --blocked` (id, url, reason; `--alt-tried` lists what was tried) and turn to manual collection under §4.7. Do not leave a placeholder pretending the document exists.

**When a download fails, try in turn**:

1. Change the engine: some sites (such as the State Taxation Administration) first return a script that sets a cookie; add `--engine curl`, which sends the cookie and requests again. For sites with a broken certificate setup, add `--insecure`. Singapore Statutes Online (sso.agc.gov.sg) answers HTTP 202 when requests come too fast; this is its bot check (AWS WAF). Do not bypass it: try again after a few minutes up to an hour.
2. Use the official interface: when a legal database offers a data interface, fetch the structured file it returns, which is more stable than the web page. The build has dedicated slicers for these two XML formats:
   - Japan e-Gov: `https://laws.e-gov.go.jp/api/1/lawdata/<law ID>`
   - Korea law.go.kr: `https://www.law.go.kr/DRF/lawService.do?OC=<OC>&target=law&type=XML&LM=<law name>`; write `<OC>` as is. fetch.py takes the id from `LAW_GO_KR_OC` in .env when downloading, and doc.csv keeps `<OC>` (how to apply: §4.7)
3. Use another official site of the same government: the same document is often published by the tax authority, the ministry of finance, the legal database and the government gazette alike; any government domain counts as an official source.
4. Search first: use `site:<official domain> <document name or number>` to find the exact address of the file on an official site, then pass it to fetch.py.
5. Slow sites, large files: when the timeout of fetch.py is not enough, download by hand with curl with a longer timeout (`-m 600`), resuming with `-C -` after an interruption. After downloading, check that the file is complete (a PDF ends with `%%EOF`; XML closes its root element), then register it with `--register-file`.
6. Long pages in parts: a long page that times out in one load can be loaded in parts and joined into one file; register it with `--register-file` and say in `--note` which parts it was joined from. Singapore Statutes Online's whole-Act page (`?WholeDoc=1`) first gives only the first parts; fetch.py fills in the remaining parts one by one (the note records how many), so there is no need to join them by hand. The site lets requests without a browser through only a few times before answering 202; fetch.py then waits 4 minutes each time and continues with the same part. The whole Income Tax Act takes about an hour; run it in the background.
7. Internet Archive: when the official site cannot be reached, first list all archived copies of the address:
   `http://web.archive.org/cdx/search/cdx?url=<original url>&fl=timestamp,statuscode,length`
   Pick a copy with status 200 and the most complete size, and download it with `https://web.archive.org/web/<timestamp>id_/<original url>`; `id_` makes the archive return the original bytes without inserting its own toolbar. Register it with `--register-file`, writing "Internet Archive 存档 <timestamp>" in `--note`. When the original site is back, replace it with the original file using `--force`.
8. Try again later: record what cannot be reached in blocked.csv and fetch it in the next session.

When registering with `--register-file`, `--url` is always the original official address; how the copy was obtained goes into `--note`.

Not done: bypassing bot checks, captchas or login walls. For such pages, change site or record the document in blocked.csv.

When the content of a list page is loaded by a script and only an empty shell is downloaded (such as the treaty list of the Singapore tax authority), register the page anyway and say so in the note; take treaty dates of entry into force from the head of the treaty document or from the announcement of entry into force, and give the source in the note of the treaty row. Laws and regulations cannot be registered this way: the build reports an error when a web page of type law or regulation yields fewer than 300 characters of text (the law pages of Korea's law.go.kr, for example, are only a page shell); register the official PDF or the XML of a data interface instead (step 2 above). Pages saved under a server-side extension such as `.do` or `.aspx` are recognised as HTML by their content.

**Scans**: when some pages of a PDF have no text layer (fewer than 50 characters) and no official version with text is found by steps 3 and 4 above, use OCR:

```bash
python database/tools/ocr.py <doc_id> [<doc_id> ...]     # or --scans: every PDF with at least half of its pages scanned
```

It uses the local Qwen3-VL (`agent/tools/doc_parse.py`, page by page, greedy decoding, so the same page always gives the same text; no Baidu components), reads only the pages without a text layer and writes `ocr/<doc_id>.txt`, whose first line records the sha256 of the original, the model and the date; an interrupted run resumes. The build gives these pages their OCR text and the other pages their text layer, and the text column of STATUS.md says `ocr`. When the original changes (its sha256 changes), the OCR text no longer counts and is made again. OCR text is a reading of the scan, not the original itself: quotes are copied from it as usual (§4.4), and parameters citing it say "OCR text, to be checked against the original" in their note. Pages OCR cannot read either (handwriting, heavy blur) go to a person (§4.8 H3).

### 4.2 Download and registration (steps A, B)

One call per document:

```bash
python database/tools/fetch.py --id <doc_id> --jur <jur> --type <law|regulation|guidance|treaty|form|page> --category <1–9 / page_treaties / page_rates / page_deadlines, several separated by semicolons> --title "..." --url https://... [--effective YYYY-MM-DD] [--effective-to YYYY-MM-DD] [--lang en] [--note "..."] [--with-attachments] [--engine curl]
python database/tools/fetch.py --register-file <local copy> --id ... --jur ... --type ... --category ... --title "..." --url <original official address> --note "<source of the copy>"
python database/tools/fetch.py --blocked --id ... --jur ... --title "..." --url ... --reason "..." [--alt-tried "..."]
```

- Naming `doc_id`: laws `<jur>.<short name>` (such as `my.ita1967`, `id.pph`), announcements `<jur>.<authority>.<year-number>`, treaties `treaty.<a>-<b>.<year>.<language>`, web pages `<jur>.<authority>.<page name>`, multilateral documents `intl.<short name>`. An id must start with `<jur>.`, `treaty.<pair>.` or `intl.`; fetch.py and the build both check this.
- When the same law is registered in two languages (the authentic local text and an English translation), add the language code at the end of the id, such as `th.rc.th` and `th.rc.en`; `--lang` is required.
- A file printing two languages (such as a Malaysian P.U.(A), Malay first, then English, each numbered from 1) is registered once as it is, with `--lang` the language the doc takes; the slicer gives the half in that language the plain ids and the other half a language prefix (such as `<doc>#ms.s4(1)`, §4.3). Parameters cite the authentic half; when both languages are official texts, they cite the `--lang` half and give the basis in the note.
- When a gazette issue prints several laws, only one of them is used: the title names that law with its number (such as `Luật Thuế thu nhập cá nhân số 109/2025/QH15`), and the Vietnamese slicer cuts only from `Luật số: 109/2025/QH15` to the next `Luật số:`. In other jurisdictions, cut the pages of the law first and register them with `--register-file`, with the page range in the note.
- Originals are stored byte for byte as `raw/<jur>/<doc_id>.<ext>`, without any conversion; plain text is extracted to `text/<doc_id>.txt` (HTML stripped of tags; PDF page by page; doc/xls converted through LibreOffice), and the sha256 is recorded. fetch.py writes the fetch time, the fetch method and any warning about a non-official domain into the note automatically.
- Attachments (rules or forms attached to an announcement) are downloaded together with the main document using `--with-attachments`; their ids start at `<main document id>.a01`, their type is attachment, and the note records `parent=<main document id>`.
- Fetching the same id again is skipped; to replace it, use `--force`, which replaces the old row and old file together. `--jur` accepts only codes in jurisdiction.csv, pairs, or intl.
- When the file cannot be obtained from the original site and only a copy is available another way (such as an Internet Archive copy), register it with `--register-file`, with the original site's address in `--url` and the source of the copy in `--note`.
- Give every document its `--category` per §2; treaty documents and documents of pairs or intl may leave it out. Attachments take the category of the main document by default; where that is wrong, change doc.csv directly.
- Registered rows go into doc.csv, with the columns of the `doc` table in §3. For treaties and protocols, `--jur` is the pair (such as `cn-hk`); MLI texts take `intl`. A treaty also gets a row in treaty; protocols and MLI texts are each registered as separate docs and referenced in the treaty row.
- **MLI**:
  1. First check whether the MLI applies to the pair: in the OECD MLI Matching Database, it applies only if both sides list the treaty as a covered agreement and the MLI is in force for both. Write the conclusion into the note of the treaty row: `MLI applies from YYYY-MM-DD` or `MLI not applicable`. When the matching database cannot be opened, look at the final MLI position document published by one side's tax authority (Reservations and Notifications; the notification under Article 2 lists that side's covered agreements): if one side has not listed the treaty, the MLI does not apply. Register the position document as `intl.mli.positions.<jurisdiction>.<language>`, with jur intl, and cite it in the note; when both sides have listed it, also check the other side's position document and the dates of entry into force on both sides. When one side has made a reservation under Article 35(7) of the MLI (such as Hong Kong), the MLI applies only after that side notifies completion of its internal procedures: the Article 35(7)(b) notification document published by the OECD lists the notification date for each agreement; register it as `intl.mli.notification-35-7b.<jurisdiction>.en`. When the list says a treaty is modified by the MLI but no synthesised text has been published yet, work out the start date from Article 35 of the MLI and both sides' dates of entry into force and notification, write it into the note, and mark it as computed.
  2. When the MLI applies, collect the synthesised text published by either side's tax authority, register it as `treaty.<pair>.<treaty year>.mli.<language>` with type treaty and the pair as jur, and fill it into mli_doc_id of the treaty row. The original treaty and protocols are registered as usual. Singapore implements the MLI through domestic orders, and its tax authority's treaty PDF lists the modifications in Annex A, with no boxed synthesised text: fill that PDF into both doc_id and mli_doc_id, and cite the items of Annex A for the PPT and other provisions (such as `treaty.sg-th.2015.en#annexA.2`).
  3. Where there is a synthesised text, all treaty parameters of the pair cite the synthesised text: provisions not modified are cited as they stand; provisions modified or added by the MLI are cited from the box, with cite_id `<doc>#<article>.mli<MLI article number>`, such as the prevention of treaty abuse `treaty.jp-my.1999.mli.en#26.mli7`. Whether the synthesised text includes bilateral protocols differs by issuer (the State Taxation Administration's texts include only the MLI, with protocols appended at the end; the Hong Kong Inland Revenue Department's texts include the protocols too); check the note at the start of the text. Where protocols are not included, cite provisions changed by a protocol from the protocol, and register one row each for the original treaty and the synthesised text in superseded.csv (§4.3); the "[REPLACED by …] [original text]" in square brackets in a synthesised text is also registered as replaced.
  4. When the MLI applies but neither side has published a synthesised text, register the text of the MLI convention (`intl.oecd.mli.en`, jur intl, registered only once for the whole library), cite the convention's articles in the affected parameters (such as `intl.oecd.mli.en#7.1`), explain the basis in the note, and record it in the session record.

### 4.3 Slicing (step C)

Slicing is done automatically by build.py; for a new format or a bad slicing, collectors fix the slicer under §4.9. The table below gives the cite_id form for each family; cite parameters in this form:

| Family | What headings look like | cite_id form | Status |
|---|---|---|---|
| Mainland regulations, Chinese treaties | `第X条`, `一、` | `<doc>#12`, `<doc>#12.1` | checked |
| Hong Kong ordinances (e-Legislation) | `12A.<Tab>title` | `<doc>#s12A` | checked |
| Singapore acts (SSO HTML) | page anchors `pr12A-` | `<doc>#s12A` | checked |
| English treaties, synthesised texts | `ARTICLE 10` + `1.`; MLI boxes start with "... of Article 7 of the MLI applies"; reference lines in amending protocols such as "Article 5 of the Agreement shall be replaced" are not taken as headings | `<doc>#10.1`; inside a box `<doc>#26.mli7` | checked (4 texts published by the Japanese Ministry of Finance, with MLI boxes; the 2018 China–India protocol, 13 articles; the MLI convention text, 39 articles) |
| Annexes and schedules after a treaty | headings such as `ANNEX A`, `Schedule 2` after the treaty's last article; an instrument that restarts at Article 1 (a protocol, an earlier convention; Roman numerals such as `ARTICLE IV` are counted as numbers) is sliced by article, anything else by numbered item | `<doc>#annexB.4`, `<doc>#annexA.2` (the MLI modifications in Singapore's Annex A), `<doc>#sch2.1` (Schedule 2 of a Hong Kong s.49 order); protocol paragraphs in Part 2 of Schedule 1 of a Hong Kong order `<doc>#protocol.3`; a protocol appended right after the treaty without a heading `<doc>#annex1.3` | checked (7 Hong Kong s.49 orders, 2 treaty PDFs of the Singapore tax authority, protocols appended to the State Taxation Administration's synthesised texts) |
| Malaysian acts and orders | `109B. title`, possibly with `*` before the section number; a marginal heading printed on the line before the number (`Exemption` / `4. (1) ...`) joins that section; after the last section the schedules `SCHEDULE 1` (followed within two lines by `[Section 6]`), `PART I`, paragraphs `2A.`; an order printing Malay and English (starting at `Nama dan permulaan kuat kuasa` and at `Citation and commencement`) is cut in both halves | `<doc>#s109B(1)`; schedules `<doc>#sch1`, `<doc>#sch1.partI`, `<doc>#sch1.partI.2A(1)`; the Malay half of a bilingual order `<doc>#ms.s4(1)` | checked (Income Tax Act 1967 reprint, 249 sections; schedules cut since 2026-11-07, the version as at 2026-01-01 has 14 schedules, 777 clauses; P.U.(A) 235/2022, 157/2024, 148/2025, 451/2024) |
| Thai Revenue Code | `มาตรา 70 ทวิ`, `Section 70 Bis` | `<doc>#s70bis(1)` | checked (Chapter 3: Thai authentic text 73 sections, English translation 68 sections) |
| UAE decree-laws | `المادة (45)`, `Article 45 – title` | `<doc>#a45(1)` | checked (Decree-Law No. 47 of 2022: Arabic authentic text and English translation, 70 articles each); the Arabic text must come from the web page of the legislation portal uaelegislation.gov.ae, because the PDF text layer is garbled, which the build reports as an error |
| Indonesian laws | `Pasal 26` on its own line; ayat `(1)`, `(1a)` | `<doc>#26(1)` | checked (UU 36/2008, 25 articles) |
| Vietnamese laws and decrees | `Điều 4. title`; clauses `1.`; in a gazette issue printing several laws, only the law whose number the title gives (§4.2) | `<doc>#4.1` | checked (67/2025/QH15, 20 articles; 109/2025/QH15 in gazette issue 37, 140 clauses) |
| Japanese laws (e-Gov XML) | sliced by the XML structure; `第四条の二` → `4-2` | `<doc>#4-2.2` | checked (Corporation Tax Act, 252 articles) |
| Korean laws (law.go.kr XML) | sliced by the XML structure; `제98조의2` → `98-2`, ① → `.1` | `<doc>#98-2.1` | checked (법인세법, 181 articles) |
| Korean laws (PDF printed from law.go.kr) | `제4조(소득의 구분)`, `제5조 삭제`; paragraphs from ①; the page header "법제처 N" and the law's name on the next line are left out, 부칙 is not cut | as the XML: `<doc>#98-2.1` | checked (소득세법, 법인세법 as at 2026-07-01); tables of the PDF have no text layer (such as the rate table of Article 55): register the XML when the figures of a table are needed |
| Indian laws | `195. Other sums.—(1)` (the 1961 Act); `393.<tab>(1)` (the 2025 Act, whose section title printed on the line before the number joins the section) | `<doc>#s195(1)` | checked (the 2025 Act as amended by the Finance Act 2026, 537 sections; the 1961 Act, 688 sections) |
| Guidance, web pages | numbered paragraphs `5.12` | `<doc>#para5.12` | checked |
| Fallback | by page / whole | `<doc>#p3` / `<doc>#all` | — |

**When slicing goes wrong**: after the build, look at the Documents table of `STATUS.md`. For laws, regulations and treaties, the slicing column should show the jurisdiction's own slicer (such as `cn_article`, `vn_article`, `my_section`). If it shows `whole` (the whole text as one clause) or `page` (by page), or the number of clauses is clearly wrong, the slicing has failed. First fix the slicer under §4.9. Where it cannot be fixed (for example no recognisable numbering; a scan first gets OCR under §4.1), cite `<doc>#all` or `<doc>#p3` in parameters as usual (the verbatim quote check is not affected), and write a line in the session record: "<doc_id> sliced as whole, N clauses" or "<doc_id> sliced as page, N clauses". When a parameter or absence record cites `#all` or `#p<n>` of a law, regulation or treaty without such a line in the session record, the build warns and lists it under Warnings in STATUS.md: such a citation means the slicer needs fixing.

**Provisions replaced by protocols or the MLI**: register them in `superseded.csv`; the build then leaves them out of clause, and parameters cite the protocol's provision instead. Read each protocol provision by provision for "cancelled and replaced by", "deleted" and "replaced", one row per place; when a later protocol cancels a provision of an earlier protocol, register a row too (doc_id is the earlier protocol). A deleted paragraph or line is also removed from the text of the article it belongs to, so write the smallest paragraph or lines. When a protocol changes only one item or a few words, delete the lines of that item and say in the note what it was changed to. One row per entry:

| Column | How to write it |
|---|---|
| doc_id | the document containing the replaced provision |
| clause | the part of the cite_id after `#`, such as `2.3`; for a whole article replaced with all its paragraphs write `24*` (matches only Article 24 and 24.x, not Article 240); for a whole document replaced write `*`; to delete only some lines of a provision write `13.5@4-` (line 4 to the end), `13.5@4-6` (lines 4 to 6) or `13.5@2` (line 2); to delete a sentence write the provision it is in, or `all` to search the whole document |
| by | cite_id of the provision that replaces it |
| since | date from which the replacement applies on this side, YYYY-MM-DD; when a protocol's date of entry into force and date of application differ, write the date of entry into force in the note |
| note | explanation |
| phrase | when only one sentence is deleted, write that sentence here verbatim; otherwise leave empty |

### 4.4 Extracting values (step D)

Read the sliced provisions and write one row per number or criterion into `param.csv`:

| Column | How to write it |
|---|---|
| param_id | `<scope>.<slot>.<name>`, such as `cn.outbound_wht.dividend_wht_rate`; when the same id needs several rows (different subjects, different periods), add a suffix, such as `cn.final.dividend_tax_rate.2026`; for one row per subject the suffixes are `.company` and `.individual` (such as `vn.final.dividend_tax_rate.individual`), never the subject in the middle of the id |
| scope | domestic law takes the local jurisdiction code, such as `cn`; treaties take the pair, such as `cn-hk` |
| subject | `company`, `individual` or `all` (both) |
| slot | see the table below |
| name | lower-case letters, digits, underscores; prefer the names in the table below |
| value | for units `%`, `days`, `months`, `years`, `count` or a currency, write only the number: 5% is `5`, not `0.05` and not `5%`; for unit `bool` write `yes` or `no`; for unit `text` write the provision's own words |
| unit | `%`, `days`, `months`, `years`, `count` (number of items, tiers), `bool`, `text`, or a currency code in jurisdiction.csv (such as `CNY`) |
| cite_id | cite_id of the provision containing the number; forms in §4.3 |
| quote | copied verbatim from the provision, the whole sentence containing the number or criterion; copy it from the output of `find.py` (the provisions as the build cleaned them of page numbers and headers, see "Finding provisions and sentences" below), never straight from a PDF reader or a web page, which brings page numbers along; the build checks that it appears verbatim in the provision the cite_id points to, and when it does not, the error gives the find.py command to use |
| effective_from, effective_to | the law's date of effect, the treaty's start date of application, YYYY-MM-DD; the source goes in the note |
| changed_on, superseded_by | normally empty. When a value is amended, do not edit the old row: give it effective_to and superseded_by (the new row's param_id), and give the new row effective_from and changed_on (date of registration), so that every change stays in the table |
| note | the result of cross-checking against the rate table page, the source of the validity period; when the page and the provision disagree, do not change the value: write it here and in the session record |

| slot | company: the recipient is a company | individual: the recipient is an individual | Suggested names |
|---|---|---|---|
| `outbound_wht` | withholding tax rate and reliefs when a local company pays dividends to a non-resident company | withholding tax rate on dividends paid to a non-resident individual | `dividend_wht_rate`, `holding_pct_min`, `holding_months_min` |
| `inbound` | a resident company receives foreign dividends: whether taxed, exemption conditions, foreign tax credit | a resident individual receives foreign dividends: whether taxed, taxed only when remitted, foreign tax credit | `foreign_dividend_taxable`, `exemption_holding_pct_min`, `source_tax_rate_min`, `ftc_method` |
| `final` | corporate income tax rate when dividends are part of taxable income, or exemption of domestic dividends | individual tax rate on dividends or exemption | `cit_rate`, `domestic_dividend_exempt`, `dividend_tax_rate` |
| `residence` | test of corporate residence | individual residence (days etc.) | `residence_test`, `residence_days_min` |
| `cfc` | whether CFC rules apply, low-tax threshold, control threshold | CFC rules for individual shareholders | `cfc_applies`, `low_tax_rate_max`, `control_pct_min` |
| `anti_abuse` | GAAR, domestic limits on treaty benefits (PPT) | same | `gaar_applies`, `ppt_applies` |
| `restructure` | rate and base of income tax on a non-resident company's gain from transferring shares of a local company, indirect-transfer rules and safe harbours, rate for a resident company, stamp duty rate and base on share transfers, valuation of unlisted shares | rates for non-resident / resident individuals, otherwise the same | `gain_tax_rate`, `gain_base` (text), `indirect_transfer_applies`, `group_safe_harbour_pct_min`, `taxable_holding_pct_min`, `taxable_transferred_pct_min`, `stamp_rate`, `stamp_base` (text), `valuation_basis` (text); pairs: `taxable_holding_pct_min`, `property_rich_pct_min`, `listed_exempt` |
| `exit` | whether a company that moves out is deemed liquidated or to have disposed of its assets, the base of the liquidation income, the rate, the shareholder's dividend and gain (`deemed_liquidation`, `gain_base` (text), `rate`, `shareholder_dividend_base` (text), `shareholder_gain_base` (text)) | the threshold, years of residence, rate and base of the deemed transfer on departure | `assets_value_min`, `resident_years_max`, `rate`, `surtax_rate`, `gain_base` (text) |
| `penalty` | late-payment surcharge / interest, fine multiples (subject `all`) | same | `late_interest_pct_per_day` / `_per_month` / `_per_year` (the period is in the name), `late_surcharge_pct_initial` (one-off), `late_interest_cap_pct`, `fine_pct` (fixed), `fine_pct_min`, `fine_pct_max`; harsher cases (evasion, concealment) get a suffix and their own row, the rule layer uses the ordinary case only |

**Third-country currencies**: when a treaty threshold uses a currency not in jurisdiction.csv (such as `US$10 million`), the unit is `text` and the value is the original wording.

**Bracket tables** (progressive rates): two rows per bracket, name `<table>_bracket_<n>_rate` (rate, `%`) and `<table>_bracket_<n>_upper` (upper bound of the bracket, unit the local currency; the top bracket has no upper row), n consecutive from 1; the quote is the line of the table for that bracket. Example: `jp.final.progressive_bracket_1_rate`, `jp.final.progressive_bracket_1_upper`. The rule layer reads the whole table by its name.

**Lists** (such as CFC white lists and low-tax country lists): write one parameter row for each country or region on the list, with name `<list name>_<ISO two-letter code in lower case>`, such as `cfc_whitelist_us`; value `yes`, unit `bool`, and the quote is the line of the list that names this country.

**Finding provisions and sentences**: `python database/tools/find.py <word> [<word> ...] [--jur <jur>]` lists the cite_ids of provisions containing these words and the whole sentence each word is in, which can be used directly as the quote; `python database/tools/find.py --cite <cite_id>` prints the full text of one provision.

Every slot of every subject of every jurisdiction must be accounted for (9 for companies and 9 for individuals, exit included; the company exit counts from 2026-11-04): at least one parameter with the jurisdiction's code as scope, or an absence record (decision with jur, subject and slot filled in, category empty, citing the provision that defines the scope of the tax with a verbatim quote). When the law has no rule for a slot (for example, no withholding tax on dividends), register an absence record; do not write a parameter with an empty or "none" value.

### 4.5 Delivery

After a jurisdiction passes the acceptance of §5, upload it with upload.py. The upload replaces the whole remote with the data of the jurisdictions in the local folder that passed acceptance:

```bash
python database/tools/upload.py --dry-run   # first see which jurisdictions, how many rows and files would be uploaded; writes nothing
python database/tools/upload.py
```

It first runs a full build, then the acceptance of each jurisdiction. Jurisdictions that do not pass are not uploaded (those with gaps but no errors are uploaded too with `--partial`; say so in the session record); `--jur <jurisdiction code>` uploads only the named jurisdictions. Before writing, it reads the remote meta table: a remote written under a newer specification (`spec_version` later than the local `SPEC_VERSION`) is not overwritten; bring the tools to that version first. `--dry-run` prints the remote meta too. The upload overwrites directly: originals, OCR texts, plain texts and `superseded.csv` (the rows of these jurisdictions' documents) are written to the storage bucket (files with the same name are overwritten), then the old files left over in the bucket are deleted; then, in one transaction, the remote schema is dropped and rebuilt with the seven tables, the meta table and all rows, and if this fails halfway the old tables stay as they were. Apart from the specification version, the upload makes no comparison and no check afterwards. Credentials come from .env: `database_url`, `supabase_url`, `supabase_key` (the storage bucket `database` has a standing rule that lets the publishable key (starting `sb_publishable_`) read and write the bucket, so the publishable key is enough to upload; a secret key or the old service_role key also works. This rule lets anyone who has the publishable key read, change and delete the files in the bucket, which the project lead has accepted; deleted files are restored by uploading again from the local folder). Without credentials, the delivery is the whole `database/` folder (packed and sent back). What is uploaded is the data (the seven tables and meta, `raw/`, `ocr/`, `text/`, `superseded.csv`), plus the Chinese and English versions of the specification and the task sheet, which are `docs/spec.zh.md`, `docs/spec.en.md`, `docs/task_sheet.zh.md` and `docs/task_sheet.en.md` in the storage bucket; tools and samples are not uploaded: a git branch is their source, and meta records the commit of the tools at upload (§4.9).

When several people share the work, it is split by jurisdiction, and each jurisdiction has a single person in charge. A jurisdiction pair belongs to the jurisdiction that comes first in alphabetical order: that side registers its treaty documents, treaty row and treaty parameters (for example `cn-hk` is registered by cn, `ae-cn` by ae). intl documents (MLI texts, positions and the like) are registered by the first jurisdiction that cites them, which names itself in the note; check doc.csv before registering (the same convention is not registered twice). Because an upload replaces the whole remote, merge the folders first when several people share the work, and let one person upload from the merged folder; uploading from your own folder only would delete from the remote the data others have uploaded.

Merge in this order:

1. Merge the tools first. A git branch is the source of the tools, and everyone uses the same version; with different tools, the two sides cut different provisions and the citations do not match (in the merge of 2026-11-07, 154 citations pointed at `#all` anchors only the other side's slicer made).
2. Merge the data: `python database/tools/merge.py <the other database folder> [--take ae,id] --report <csv>`. Rows belong to their owning jurisdiction (a pair to its alphabetically first side); the jurisdictions of `--take` (by default those only the other folder has) come in with their originals, OCR texts and the intl documents they cite; for the other jurisdictions the local rows stay, rows the other folder has differently are listed as conflicts and not taken; columns the other folder lacks (`TABLES`) are filled empty.
3. Full build: `python database/tools/build.py`.
4. Repoint citations: `python database/tools/recite.py --jur <the jurisdictions taken> --ids --report <csv>`. When the cited provision does not exist or does not hold the quote, the citation points to the smallest provision of the same document that holds it; a quote that differs only by page-number lines is matched without them; `--ids` brings parameter ids to the form of §4.4. Values, units, dates and the words of the law are never touched; rows that still do not match are listed as unresolved and go to a person under §4.8.
5. Build again, run the acceptance of each jurisdiction, and write the merge and its conflicts into the session record.

### 4.6 Records

- `blocked.csv`: documents that failed to download, written by `fetch.py --blocked`.
- `session_log.md`: the session record. At the end of each session, append a section (in English) in the format given in the task sheet. Things a person needs to do go under its `Handoff to a person` item (§4.8), and tool changes under its `Tool changes` item (§4.9).

### 4.7 Manual collection

When all the methods of §4.1 have been tried and a document still cannot be fetched, a person gets the original in a browser and then registers it with fetch.py. Four common situations:

| Situation | Examples | What the person does |
|---|---|---|
| The site refuses access from this machine: 403, no connection, a bot check page | Indian tax department, Indonesian Ministry of Finance legal database | Open it in an ordinary browser; if that fails, download from another network (home broadband, a local colleague's computer) |
| The site is too slow and the download breaks off | Korean legal database, India Code | Use curl with a longer timeout and resume (§4.1, step 5), or download in a browser |
| A dynamic search system with no direct link to the file | Malaysian legal database, Vietnamese legal database | Search for the document's page on the site and download from that page |
| The interface requires your own credentials | the OC id of the Korean legal database interface | A person applies: register an account at open.law.go.kr, apply in the Open API menu, tick the interfaces needed (at least "法令"), and register the public IP of the caller; once approved, the OC is the part of the registered e-mail address before @. Write it into `LAW_GO_KR_OC` in .env, and write `OC=<OC>` in the url |

Requirements for getting the original:

- Download the original file the site offers (PDF, XML, Word, etc.); save web pages with the browser's "Save as → Web page, HTML only". Do not print to PDF, do not copy and paste the text, do not take screenshots.
- After downloading, check that it is complete: the PDF opens to its last page, and the file size matches what the site shows.
- Record the address of the page the file is on (the browser's address bar); when the download link is generated on the fly, record that page address.

Registration:

```bash
python database/tools/fetch.py --register-file <downloaded file> --id <doc_id> --jur <jur> --type <type> --category "<categories>" --title "<original title>" --url <official page url> --note "Downloaded manually in a browser on YYYY-MM-DD from <page>; fetch failed: <reason>"
```

When the same id has an entry in blocked.csv, it counts as resolved once registered.

Division of work: when the collector's AI cannot use a browser, it hands the task to a person under §4.8 (H1), and the person downloads and registers it.

### 4.8 Handing over to a person

The collector's AI first resolves things itself under this specification; only the seven situations in the table below go to a person. Handing over does not mean stopping: the remaining documents and parameters are finished as usual, and only the cells waiting for a person are left open; the acceptance result is reported as it is, and the gaps left are exactly the cells waiting for a person.

Each item goes into `Handoff to a person` in the session record, one per line (in English): the code, the document id or cell (such as `cn|individual|cfc`), what has been tried, and what the person needs to do.

| Code | Situation | What the AI does first | What the person does |
|---|---|---|---|
| H1 | The original cannot be obtained: 403, no connection, timeout, bot check page | Tried steps 1–7 of §4.1, including other official sites of the same government and archived copies; recorded it with `--blocked` (step 8 retries in the next session as usual; once fetched, remove it from the handover items) | Download in a browser or from another network, and register it under §4.7 |
| H2 | A person's identity is needed: account, login, captcha, payment, accepting terms, or interface credentials that require registering an identity or IP (such as the OC of the Korean legal database) | Did not bypass anything; confirmed there is no official version without login | Apply or log in and download; write the credentials into `.env` |
| H3 | No usable text: a scan or a garbled text layer, no official version with text can be found, and OCR cannot read it either | Looked for other formats of the same document, a web version and other official sites | Find another version, or decide not to collect this document |
| H4 | Official sources conflict: two official documents state the same number, date or condition differently, and no later document clearly replaces either | Compared them by "later over earlier, authentic text over translation, the issuer's original over reproductions" and still cannot decide; leaves this parameter out for now | Decide which one applies |
| H5 | Validity cannot be established: no validity label and no repealing or amending document found, but signs that it may have lapsed or been changed | Checked the legal database's validity label, the issuer's list of repealed documents and repeal clauses in later documents; registers it as usual, with `validity not confirmed` in the doc's note | Confirm whether it is current |
| H6 | Only unofficial sources: no version on any official domain, and none in archived copies | Searched as in §4.1; does not register it (the build rejects non-official addresses) | Decide whether to collect it and from where |
| H7 | Others' data and rule changes: finding an error in a row someone else registered; needing to change a part of §4.9 that collectors may not change (table columns, checks and acceptance rules, the acceptance gate before upload) to continue | Does not change others' rows, does not loosen checks; records the full command, the error and what needs changing | Change the data or the rules |

The following are not handed over; the AI does them itself (in the Mainland China pilot of 2026-10-23 the AI did all of them):

- Finding documents: searching official sites, reproductions on the sites of the issuer, a higher or a local authority, archived copies (§4.1).
- Establishing validity and dates: the legal database's validity label, repeal clauses in later documents, announcements or notices of entry into force, footnotes of official consolidated texts.
- Deciding whether the MLI applies: when the matching database cannot be opened, the position document of one side (§4.2).
- Finding which provisions protocols and the MLI changed: reading the originals provision by provision and registering them in superseded.csv (§4.3).
- Bad slicing, tool errors, special behaviour of a site: fixing the tools yourself under §4.9; a slicer that cannot be fixed is handled under §4.3 by citing `#all` or by page, and written under Slicing problems in the session record.
- Classification: decided by the definitions of §2; when unsure, give the reason in the note.
- Disagreement between the authentic local text and the English translation: parameters cite the authentic text.

### 4.9 Maintaining the tools

`database/tools/` is maintained by the collectors. For a new format, bad slicing, special behaviour of a site or a tool error, change the code yourself; afterwards, run the checks below to confirm nothing else, in other documents or jurisdictions, was broken. For how to write a new slicer, see the "How a slicer is written" section of the README under `samples/`.

**May be changed**
- Slicers: the `slice_*` functions of build.py and `slice_doc`, which dispatches by jurisdiction and type (new formats, bad slicing, numbering styles). The slicer's docstring states which documents it was checked on and how many clauses each gave.
- Fetching: site-specific handling in fetch.py (cookies, loading in parts, waiting and retry intervals); adding missing government or official domains to the official domain list `OFFICIAL`.
- Upload: the connection, credentials and storage interface of upload.py.
- New helper scripts (such as ocr.py, merge.py, recite.py).

**May not be changed** (to change these, hand over to a person, §4.8 H7)
- The columns of the seven tables (`TABLES` in build.py), the checks on ids, dates, units, verbatim quotes and the like, and the coverage and acceptance decisions: loosening a check means letting wrong data pass acceptance.
- The acceptance gate of upload.py (jurisdictions that do not pass acceptance are not uploaded) and its check of the specification version (a remote written under a newer specification is not overwritten), and what the meta table records.
- Data rows registered by others.

**Checks after a change** (a change is not finished until all are done)
1. Before the change, save the current clause ids: `python database/tools/clause_diff.py --save`.
2. Run the samples: `python database/samples/slicers-2026-10-23/run_slicers.py`; the results must match the results table of the samples README; for intended changes, update that table and give the reason.
3. Full build: `python database/tools/build.py`, with zero errors.
4. `python database/tools/clause_diff.py`: it lists the documents whose clause ids changed, and reports an error when an id still cited by parameters, absence records or superseded.csv has disappeared; fix those citations in the same change.
5. Re-run `python database/tools/build.py --jur <jurisdiction>` for each jurisdiction that had passed acceptance; each must still show `PASSED`.
6. New formats: put the original into a folder under `samples/`, add an entry to run_slicers.py, add a row to the results table of the samples README, and add a row or change the status in the table of §4.3.

**Records and delivery**: write a `Tool changes` item in the session record: which file was changed, why, which documents it was checked on, and the results of the checks above. A git branch is the only source of the tools: whoever changed them commits `tools/` and `samples/` to that branch, and the upload records the commit in meta; when several people changed the same tool, re-run the acceptance of every jurisdiction after merging. A change to the specification also changes `SPEC_VERSION` and adds a row to the change record at the head.

### 4.10 MCP server `tax-db`

See `database/数据库MCP规范.md` (English copy `database/database_mcp_spec.en.md`; 2026-11-01, minimal set, read-only; maintained by the collectors under 4.9).

## 5. Acceptance (by collectors, per jurisdiction)

After finishing a jurisdiction, run:

```bash
python database/tools/build.py --jur <jurisdiction code>
```

It checks only this jurisdiction's data and writes nothing. With zero errors and zero gaps it prints `PASSED` (exit code 0), meaning the jurisdiction passes acceptance; otherwise it lists each error and gap.

Data checked: the jurisdiction's documents and absence records; the parameters, treaty documents and treaty rows of the jurisdiction and its pairs; and the intl documents.

**Errors**:
- A file is missing, its hash does not match, no text can be extracted (a scan without OCR), the Arabic text layer is garbled, the web page of a law or regulation is only a shell (fewer than 300 characters), the url is not on an official domain, the type or category is invalid, lang is empty, the id prefix is wrong, or a treaty document's jur is not a pair;
- A parameter's cite_id does not exist, its quote is not verbatim, its scope, subject, slot, name or unit is invalid, its param_id is not `<scope>.<slot>.<name>`, or its value does not fit its unit;
- An absence record has no jur, or does not fill exactly one of category and subject + slot, or an absence record for categories 1–4, 9 or a slot does not cite the provision on the scope of the tax;
- A treaty row's pair is written wrongly, or the document it references does not exist;
- A date is not YYYY-MM-DD (dates of effect of documents and parameters, the date of entry into force of a treaty row, since in superseded.csv).

**Warnings** (they do not affect passing; listed in STATUS.md): a law, regulation or treaty cited as a whole (`#all`) or by page (`#p<n>`) without a "sliced as whole/page" line in the session record (§4.3). Documents using OCR text say `ocr` in the text column of the Documents table of STATUS.md.

**Gaps**:
- Any of the 13 categories (10 content + 3 page categories; category 11 not counted) with neither a document nor an absence record;
- Any of the 9 slots for companies or the 9 for individuals with neither a parameter of the jurisdiction nor an absence record;
- Any pair the jurisdiction is in charge of (it comes first in alphabetical order) without a treaty row; for a pair with no treaty, doc_id is empty and the note says "no treaty";
- Downloads in blocked.csv for the jurisdiction that are not yet in doc.csv; if confirmed not needed, delete the row and give the reason in the session record.

## 6. Widening the income tax scope (drafted 2026-11-07)

This section sets what is collected after the widening, how it is registered and how it is accepted. Until the tools of 6.7 are changed, the build and acceptance follow §1–§5; the tool changes touch the part of §4.9 that may not be changed, and the project lead carries them out under this section.

### 6.1 Scope

From "cross-border dividends" to the kinds of cross-border income that appear along a planned route. Still income tax only; the jurisdictions and subjects stay (11 jurisdictions; companies and individuals).

| Income type (income) | Content |
|---|---|
| dividend | dividends (the present content) |
| interest | interest |
| royalty | royalties (scope by each law's and treaty's definition, such as equipment rentals) |
| service | service, technical and management fees (including the fees for technical services articles of some treaties) |
| gain | gains on transferring shares (the present content of the restructure slot) |
| business | business profits: how a non-resident's permanent establishment and its profits are taxed, the profit tax of the operating company itself |
| all | rules that do not depend on the income type: residence, CFC, anti-abuse, penalties, exit, general rates |

Not collected: VAT, stamp duty (except the stamp duty on share transfers already collected), customs, social security. Rulings on individual cases stay category 11 interpretive sources only.

### 6.2 What to collect for each jurisdiction (in addition to §2)

Categories 1 and 2 gain content per income type:

- Category 1 (corporate income tax law) adds: withholding tax on interest, royalties and service fees paid to non-residents (rates, exemptions, reliefs); the taxation, exemption and credit when a resident company receives foreign interest, royalties or service fees; the domestic rules on when a non-resident company has a permanent establishment and which profits are attributed to it.
- Category 2 (individual income tax law) adds: the rate or exemption on individuals' interest, royalties and income from services; how such foreign income is taxed (for example only when remitted) and credited.

Three new content categories:

12. Limits on the payer's deduction: thin capitalisation (debt-to-equity ratio), interest limitation (such as a share of EBITDA), conditions for deducting royalties and service fees paid to related parties abroad (including rules that make withholding a condition of the deduction). Transfer pricing stays in category 4.
13. Permanent establishments and non-residents' business profits: the domestic definition of a permanent establishment and its guidance (days for a service PE, agents), branch profits remittance tax.
14. Statutory preferential regimes: only preferential rates directly tied to the income types above whose conditions are written in a law or regulation (such as IP regimes, regional headquarters or treasury centre rates); regimes granted case by case are not collected.

Each jurisdiction pair: the treaties are registered in full already; extract in addition Article 5 (permanent establishment), Article 7 (business profits), Article 11 (interest), Article 12 (royalties), the fees for technical services article where there is one, and the changes of MLI Articles 12–15 to permanent establishments. Article 13 is collected under restructure already.

The page categories stay; the cross-check against `page_rates` extends to the rates of every income type.

### 6.3 Table structure

Two tables change, by one column each; the other five stay as they are.

| Table | New column | Values |
|---|---|---|
| param | income (after slot) | dividend / interest / royalty / service / gain / business / all |
| decision | income (after slot) | the same; empty for absence records registered by category (those that fill category) |

The param_id rule stays (`<scope>.<slot>.<name>`). For rows with income interest, royalty, service or business, the name starts with that income type (`interest_wht_rate`, `royalty_wht_rate`, `business_service_pe_days_min`), and the build checks that they agree; rows with dividend, gain or all keep the present naming. New ids therefore never collide with old ones, and no old id changes.

### 6.4 Slots

The 9 existing slots stay, their meaning widened to the income types; 2 are new.

| slot | Income types it applies to | company (the payee or taxpayer is a company) | individual | Suggested names |
|---|---|---|---|---|
| outbound_wht | dividend, interest, royalty, service | withholding tax and reliefs on payments to a non-resident company | withholding tax on payments to a non-resident individual | `interest_wht_rate`, `royalty_wht_rate`, `service_wht_rate`, `interest_exempt_<case>` |
| inbound | dividend, interest, royalty, service | a resident company receives such foreign income: whether taxed, exemption conditions, credit | a resident individual: whether taxed, whether only when remitted, credit | `interest_foreign_taxable`, `royalty_ftc_method` |
| final | dividend, interest, royalty, service | the rate once the income is part of taxable income (the general cit_rate takes all) | the individual's rate or exemption on such income | `interest_tax_rate`, `royalty_tax_rate` |
| deduction (new) | interest, royalty, service | limits on the payer's deduction (category 12) | not checked | `interest_debt_equity_ratio_max`, `interest_ebitda_pct_max`, `royalty_deduction_requires_wht` |
| pe (new) | business | the threshold at which a non-resident company has a permanent establishment here, the rate on its profits, branch profits remittance tax (category 13) | the threshold at which a non-resident individual doing business or providing services here has a permanent establishment or fixed base | `business_service_pe_days_min`, `business_pe_profit_rate`, `business_branch_profits_tax_rate` |
| residence, cfc, anti_abuse, penalty, exit | all | unchanged | unchanged | unchanged |
| restructure | gain | unchanged | unchanged | unchanged |

Parameters of a jurisdiction pair (scope `a-b`) use the same slots: treaty Articles 11 and 12 and the fees for technical services article go under outbound_wht, Articles 5 and 7 under pe, Article 23 (elimination of double taxation) under inbound. Preferential rates of category 14 go under final, with their conditions in the note.

### 6.5 Coverage and acceptance

A coverage cell is jurisdiction × subject × slot × income type, checked only for the combinations listed under "Income types it applies to" in 6.4; individuals are not checked for deduction. A cell is accounted for when there is a parameter of the jurisdiction whose income equals that income type or all, or an absence record with jur, subject, slot and income filled in, citing the provision that defines the scope of the tax. Example: Hong Kong levies no withholding tax on interest: register `hk.absent.company.outbound_wht.interest`.

Absence record ids are `<jur>.absent.<subject>.<slot>.<income>`; when income is all, the last part is left out, as in the existing records.

Switching on step by step: the build has a list of the income types switched on (6.7). The cells of a type not yet switched on are listed in STATUS.md as "extension cells", are not gaps and do not affect acceptance; the project lead switches the types on one by one as collection proceeds and writes the date into session_log. That way the jurisdictions that have passed do not all fail at once during the widening.

Number of cells (for planning): per jurisdiction 13 new cells for companies (3 new types each under outbound_wht, inbound and final, 3 under deduction, 1 under pe) and 10 for individuals (the same without deduction), 253 for the 11 jurisdictions. Each pair also has Articles 5, 7, 11 and 12 to extract; these are not coverage cells, and STATUS.md lists the ones not yet extracted.

### 6.6 Migrating the existing rows

When the tools are changed, a program fills income into the existing rows once; no hand edits:

- rows with slot residence, cfc, anti_abuse, penalty or exit → all;
- rows with slot restructure → gain;
- rows with slot outbound_wht or inbound: names starting with interest or royalty → interest or royalty (the ae pairs merged on 2026-11-07 already hold 35 rows of treaty rates on interest and royalties, such as `ae-cn.outbound_wht.interest_rate`); the others → dividend (holding percentages and holding periods included); names that mention another kind of income (such as `ae.inbound.foreign_income_taxable_if_related_to_uae_business`) go on the list to confirm;
- rows with slot final: names containing dividend → dividend; the others (such as cit_rate and the individual progressive tables `progressive_bracket_*`) are proposed as all and listed for the project lead to confirm one by one;
- absence records by the same rules; absence records registered by category stay empty.

A full build follows the migration, and the migration list goes into session_log. No param_id changes; the rule layer reads by id and is not affected.

### 6.7 Tool changes (by the project lead, with the checks of §4.9)

- build.py: income in `TABLES` for param and decision; new constants `INCOMES` and the switch-on list; deduction and pe in `SLOTS`; 12, 13, 14 in `CATEGORIES`; checks on the values of income, on income agreeing with the start of the name and on valid slot and income combinations; `coverage_slots` counts the cells of 6.5; an "extension cells" table in STATUS.md.
- upload.py: the tables are created from `TABLES`, so the new columns come along; before uploading, the remote meta is read (§4.5).
- fetch.py: `--category` accepts 12, 13, 14.
- MCP server `tax-db`: an income filter on param, params_for and absent; `数据库MCP规范.md` and its English copy change with it.
- Task sheet (`采集任务单.md` and its English copy): example rows for the new slots and categories.
- The rule and optimization layers are outside this specification; when they start using the new income types, they widen under their own specifications.

### 6.8 Order of work

1. Change the tools and migrate the existing rows (6.6, 6.7); a full build with zero errors, and the jurisdictions that passed still pass.
2. Extract first from the whole laws and treaties already in the library: treaty Articles 5, 7, 11 and 12, and the provisions of each income tax law on withholding, deductions and permanent establishments. This step needs no download.
3. Then collect the missing documents of categories 12–14 under §4.
4. When a jurisdiction has finished one income type, the project lead switches that type on (6.5) and runs the `--jur` acceptance.
5. Suggested order of switching on: interest, royalty, service (the payments planning uses most often in place of dividends), then business (the relocation of the operating company, goals §6). gain is already in restructure.
