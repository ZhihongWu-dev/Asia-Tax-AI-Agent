# Database specification (minimal set)

English copy of `数据库规范.md`. If the two differ, the Chinese version applies.

This specification is written in Chinese, for people to read. Text that an AI writes into files (statement, note, session_log.md) is in English. Originals, legal provisions, quotes and document titles stay in their original language and are not translated. When a law exists both as an authentic text in the local language and as an English translation, register both and cite the authentic text in parameters. When the English text is itself authentic (for example the laws of Hong Kong and Singapore), register only the English text. When only an English translation is available, write "unofficial translation" in the note.

2026-10-23. Goal: a minimal database supporting the "Asian cross-border dividend optimisation" workflow (recipients split into companies and individuals; 11 jurisdictions: Mainland China, Hong Kong, Singapore, Indonesia, Vietnam, Malaysia, Thailand, UAE, Japan, Korea, India).

English copies: `database/database_spec.en.md` (this specification) and `database/collection_task_sheet.en.md` (the task sheet). If they differ, the Chinese versions apply. When you change a Chinese version, change its English copy too.

Before you start, read the task sheet (`采集任务单.md`, English copy `collection_task_sheet.en.md`): it lists, in order, the commands to run for each jurisdiction and example rows for each csv. This specification is the full reference it points to.

## 1. Minimal workflow

```text
Official websites (tax authority / ministry of finance / legal database / gazette)
   │  for each jurisdiction, collect the 9 content categories + 3 page categories item by item; each item has 0, 1 or more documents; one complete treaty per jurisdiction pair (list in §2)
   │  how: see §4
   ▼
A  Originals
   raw/<jur>/<doc_id>.<ext> (saved as is)  +  text/<doc_id>.txt (plain text)
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
   11 jurisdictions × 12 categories (9 content + 3 page categories): each cell has a document or an absence record
   11 jurisdictions × {company, individual} × 6 slots: each cell has a parameter or an absence record
   55 jurisdiction pairs: each pair has a treaty row or a "no treaty" row
```

## 2. What to collect for each jurisdiction (minimal scope)

Check each jurisdiction against the 9 content categories and 3 page categories below, and collect one complete treaty for each jurisdiction pair.

A category means content, not a number of files: one item may have 0, 1 or more documents, and one document may belong to several categories (categories 1, 3 and 4 are often in the same income tax law). Each document records in `doc.category` the categories it belongs to; values are `1`–`9`, `page_treaties`, `page_rates`, `page_deadlines`, separated by semicolons.

When a jurisdiction has no document for a category, register an absence record in the `decision` table: fill in `jur` and `category`, and say in `statement` what is missing and where you looked. Absence records for categories 1–4 and 9 must cite the provision that defines the scope of the tax, with a verbatim quote. For categories 5–8 and the pages, a citation may be left out when there is no provision to cite.

**9 content categories per jurisdiction**

1. Four parts of the income tax law: withholding tax on outbound dividends (rates, exemptions); taxation of foreign dividends received and the conditions for exemption (including the conditions of a foreign income exemption regime, such as a minimum tax rate at source); corporate residence; the method and limit of the foreign tax credit.
2. Three parts of the individual income tax law: tax rate on individuals' dividends or exemption; individual residence; foreign tax credit for individuals.
3. CFC provisions and their attached lists (white lists, low-tax lists, exemption conditions).
4. Anti-abuse provisions: GAAR, and domestic limits on treaty benefits (provisions implementing a PPT).
5. Documents on the factors for determining the beneficial owner (announcements / guidance).
6. Guidance on residence (place of effective management standard, counting an individual's days of residence); needed only when the law refers to guidance.
7. Documents and forms for the procedure to claim or file for treaty benefits (who files, when, what).
8. Procedure for the certificate of residence (conditions of issue, how to apply).
9. Income tax provisions on share transfers (including deemed disposals and indirect transfers by non-residents); only for the one-off cost of setting up a structure.

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
| `param` | param_id, scope (jurisdiction or pair), subject (company / individual / all), slot (outbound_wht / inbound / final / residence / cfc / anti_abuse), name, value, unit, cite_id, quote, effective_from, effective_to, note | param_id |
| `decision` | id, jur, category, subject, slot, statement, cite_id, quote (each row is an absence record: fill in either category, or subject and slot; see §2 and §4.4) | id |

**What each table and column means** (all examples are real rows of the library)

`jurisdiction`: the jurisdictions covered, one row each, prefilled; do not change.
- code: jurisdiction code, two lower-case letters, such as `cn` (Mainland China) and `hk` (Hong Kong). Two jurisdictions forming a "pair" are joined in alphabetical order, such as `cn-hk`; pairs are used for treaties and treaty parameters.
- name: name of the jurisdiction.
- currency: code of the local currency, such as `HKD`; parameter units may use it.
- company_in_scope, individual_in_scope: whether rules for companies and for individuals are collected for this jurisdiction (yes / no). The coverage check uses them to decide whether to check the 6 slots of that subject.

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

`files`: one row for each original (`raw/`) and each plain text extracted from it (`text/`); generated by the build.
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
  - anti_abuse: general anti-avoidance rules, and limits on treaty benefits (PPT).
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

**Remote**: after upload, the seven tables are in the schema `database` of the remote Postgres, next to the archived library's schema `official`; the files listed in the `files` table are in the storage bucket `database`. They are real tables that can be queried directly, not a snapshot, but they change only on upload: each upload replaces them entirely with the local data that passed acceptance, and no earlier versions are kept.

**Local file convention**: locally, each table is a csv of the same name, kept with `raw/` and `text/` under `database/`. The five csv files `jurisdiction / treaty / doc / param / decision` are filled by an AI or by hand (`jurisdiction.csv` is prefilled; `doc.csv` is written through fetch.py); `files.csv` and `clause.csv` are generated by the build and not filled by an AI or by hand. fetch.py also writes `blocked.csv`, and the session record is kept in `session_log.md`. Text that an AI writes into the csv files (statement, note, etc.) and the session record are in English; quotes and titles stay in the original. There is also an auxiliary csv, `superseded.csv` (doc_id, clause, by, since, note, phrase), filled by an AI or by hand, which records provisions replaced by protocols or the MLI. It is not a library table; the build uses it only to leave those provisions out of `clause`.

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

When the content of a list page is loaded by a script and only an empty shell is downloaded (such as the treaty list of the Singapore tax authority), register the page anyway and say so in the note; take treaty dates of entry into force from the head of the treaty document or from the announcement of entry into force, and give the source in the note of the treaty row.

### 4.2 Download and registration (steps A, B)

One call per document:

```bash
python database/tools/fetch.py --id <doc_id> --jur <jur> --type <law|regulation|guidance|treaty|form|page> --category <1–9 / page_treaties / page_rates / page_deadlines, several separated by semicolons> --title "..." --url https://... [--effective YYYY-MM-DD] [--effective-to YYYY-MM-DD] [--lang en] [--note "..."] [--with-attachments] [--engine curl]
python database/tools/fetch.py --register-file <local copy> --id ... --jur ... --type ... --category ... --title "..." --url <original official address> --note "<source of the copy>"
python database/tools/fetch.py --blocked --id ... --jur ... --title "..." --url ... --reason "..." [--alt-tried "..."]
```

- Naming `doc_id`: laws `<jur>.<short name>` (such as `my.ita1967`, `id.pph`), announcements `<jur>.<authority>.<year-number>`, treaties `treaty.<a>-<b>.<year>.<language>`, web pages `<jur>.<authority>.<page name>`, multilateral documents `intl.<short name>`. An id must start with `<jur>.`, `treaty.<pair>.` or `intl.`; fetch.py and the build both check this.
- When the same law is registered in two languages (the authentic local text and an English translation), add the language code at the end of the id, such as `th.rc.th` and `th.rc.en`; `--lang` is required.
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
| Malaysian acts | `109B. title`, possibly with `*` before the section number | `<doc>#s109B(1)` | checked (Income Tax Act 1967 reprint, 249 sections) |
| Thai Revenue Code | `มาตรา 70 ทวิ`, `Section 70 Bis` | `<doc>#s70bis(1)` | checked (Chapter 3: Thai authentic text 73 sections, English translation 68 sections) |
| UAE decree-laws | `المادة (45)`, `Article 45 – title` | `<doc>#a45(1)` | checked (Decree-Law No. 47 of 2022: Arabic authentic text and English translation, 70 articles each); the Arabic text must come from the web page of the legislation portal uaelegislation.gov.ae, because the PDF text layer is garbled, which the build reports as an error |
| Indonesian laws | `Pasal 26` on its own line; ayat `(1)`, `(1a)` | `<doc>#26(1)` | checked (UU 36/2008, 25 articles) |
| Vietnamese laws and decrees | `Điều 4. title`; clauses `1.` | `<doc>#4.1` | checked (67/2025/QH15, 20 articles) |
| Japanese laws (e-Gov XML) | sliced by the XML structure; `第四条の二` → `4-2` | `<doc>#4-2.2` | checked (Corporation Tax Act, 252 articles) |
| Korean laws (law.go.kr XML) | sliced by the XML structure; `제98조의2` → `98-2`, ① → `.1` | `<doc>#98-2.1` | checked (법인세법, 181 articles) |
| Indian laws | `195. Other sums.—(1)` (the 1961 Act); `393.<tab>(1)` (the 2025 Act) | `<doc>#s195(1)` | checked (the 2025 Act as amended by the Finance Act 2026, 537 sections; the 1961 Act, 688 sections) |
| Guidance, web pages | numbered paragraphs `5.12` | `<doc>#para5.12` | checked |
| Fallback | by page / whole | `<doc>#p3` / `<doc>#all` | — |

**When slicing goes wrong**: after the build, look at the Documents table of `STATUS.md`. For laws, regulations and treaties, the slicing column should show the jurisdiction's own slicer (such as `cn_article`, `vn_article`, `my_section`). If it shows `whole` (the whole text as one clause) or `page` (by page), or the number of clauses is clearly wrong, the slicing has failed. First fix the slicer under §4.9. Where it cannot be fixed (for example only a scan, or no recognisable numbering), cite `<doc>#all` or `<doc>#p3` in parameters as usual (the verbatim quote check is not affected), and write a line in the session record: "<doc_id> sliced as whole/page, N clauses".

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
| param_id | `<scope>.<slot>.<name>`, such as `cn.outbound_wht.dividend_wht_rate`; when the same id needs several rows (different subjects, different periods), add a suffix, such as `cn.final.dividend_tax_rate.2026` |
| scope | domestic law takes the local jurisdiction code, such as `cn`; treaties take the pair, such as `cn-hk` |
| subject | `company`, `individual` or `all` (both) |
| slot | see the table below |
| name | lower-case letters, digits, underscores; prefer the names in the table below |
| value | for units `%`, `days`, `months`, `years`, `count` or a currency, write only the number: 5% is `5`, not `0.05` and not `5%`; for unit `bool` write `yes` or `no`; for unit `text` write the provision's own words |
| unit | `%`, `days`, `months`, `years`, `count` (number of items, tiers), `bool`, `text`, or a currency code in jurisdiction.csv (such as `CNY`) |
| cite_id | cite_id of the provision containing the number; forms in §4.3 |
| quote | copied verbatim from the provision, the whole sentence containing the number or criterion; the build checks that it appears verbatim in the provision the cite_id points to |
| effective_from, effective_to | the law's date of effect, the treaty's start date of application, YYYY-MM-DD; the source goes in the note |
| note | the result of cross-checking against the rate table page, the source of the validity period; when the page and the provision disagree, do not change the value: write it here and in the session record |

| slot | company: the recipient is a company | individual: the recipient is an individual | Suggested names |
|---|---|---|---|
| `outbound_wht` | withholding tax rate and reliefs when a local company pays dividends to a non-resident company | withholding tax rate on dividends paid to a non-resident individual | `dividend_wht_rate`, `holding_pct_min`, `holding_months_min` |
| `inbound` | a resident company receives foreign dividends: whether taxed, exemption conditions, foreign tax credit | a resident individual receives foreign dividends: whether taxed, taxed only when remitted, foreign tax credit | `foreign_dividend_taxable`, `exemption_holding_pct_min`, `source_tax_rate_min`, `ftc_method` |
| `final` | corporate income tax rate when dividends are part of taxable income, or exemption of domestic dividends | individual tax rate on dividends or exemption | `cit_rate`, `domestic_dividend_exempt`, `dividend_tax_rate` |
| `residence` | test of corporate residence | individual residence (days etc.) | `residence_test`, `residence_days_min` |
| `cfc` | whether CFC rules apply, low-tax threshold, control threshold | CFC rules for individual shareholders | `cfc_applies`, `low_tax_rate_max`, `control_pct_min` |
| `anti_abuse` | GAAR, domestic limits on treaty benefits (PPT) | same | `gaar_applies`, `ppt_applies` |

**Third-country currencies**: when a treaty threshold uses a currency not in jurisdiction.csv (such as `US$10 million`), the unit is `text` and the value is the original wording.

**Lists** (such as CFC white lists and low-tax country lists): write one parameter row for each country or region on the list, with name `<list name>_<ISO two-letter code in lower case>`, such as `cfc_whitelist_us`; value `yes`, unit `bool`, and the quote is the line of the list that names this country.

**Finding provisions and sentences**: `python database/tools/find.py <word> [<word> ...] [--jur <jur>]` lists the cite_ids of provisions containing these words and the whole sentence each word is in, which can be used directly as the quote; `python database/tools/find.py --cite <cite_id>` prints the full text of one provision.

Every slot of every subject of every jurisdiction must be accounted for: at least one parameter with the jurisdiction's code as scope, or an absence record (decision with jur, subject and slot filled in, category empty, citing the provision that defines the scope of the tax with a verbatim quote). When the law has no rule for a slot (for example, no withholding tax on dividends), register an absence record; do not write a parameter with an empty or "none" value.

### 4.5 Delivery

After a jurisdiction passes the acceptance of §5, upload it with upload.py. The upload replaces the whole remote with the data of the jurisdictions in the local folder that passed acceptance:

```bash
python database/tools/upload.py --dry-run   # first see which jurisdictions, how many rows and files would be uploaded; writes nothing
python database/tools/upload.py
```

It first runs a full build, then the acceptance of each jurisdiction. Jurisdictions that do not pass are not uploaded (those with gaps but no errors are uploaded too with `--partial`; say so in the session record); `--jur <jurisdiction code>` uploads only the named jurisdictions. The upload overwrites directly: originals and plain texts are written to the storage bucket (files with the same name are overwritten), then the old files left over in the bucket are deleted; then, in one transaction, the remote schema is dropped and rebuilt with the seven tables and all rows, and if this fails halfway the old tables stay as they were. The upload makes no comparison and no check afterwards. Credentials come from .env: `database_url`, `supabase_url`, `supabase_key` (the storage bucket `database` has a standing rule that lets the publishable key (starting `sb_publishable_`) read and write the bucket, so the publishable key is enough to upload; a secret key or the old service_role key also works. This rule lets anyone who has the publishable key read, change and delete the files in the bucket, which the project lead has accepted; deleted files are restored by uploading again from the local folder). Without credentials, the delivery is the whole `database/` folder (packed and sent back). What is uploaded is the data (the seven tables, `raw/`, `text/`), plus the Chinese and English versions of the specification and the task sheet, which are `docs/spec.zh.md`, `docs/spec.en.md`, `docs/task_sheet.zh.md` and `docs/task_sheet.en.md` in the storage bucket; tools and samples are not uploaded.

When several people share the work, it is split by jurisdiction, and each jurisdiction has a single person in charge. A jurisdiction pair belongs to the jurisdiction that comes first in alphabetical order: that side registers its treaty documents, treaty row and treaty parameters (for example `cn-hk` is registered by cn, `ae-cn` by ae). When several folders are merged, the csv files are merged by row and `raw/` by file; all ids carry a jurisdiction prefix, so they do not clash. Because an upload replaces the whole remote, merge the folders first when several people share the work, and let one person upload from the merged folder; uploading from your own folder only would delete from the remote the data others have uploaded.

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
| H3 | No usable text: a scan or a garbled text layer, and no official version with text can be found | Looked for other formats of the same document, a web version and other official sites | Find another version, or decide not to collect this document |
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
- New helper scripts.

**May not be changed** (to change these, hand over to a person, §4.8 H7)
- The columns of the seven tables (`TABLES` in build.py), the checks on ids, dates, units, verbatim quotes and the like, and the coverage and acceptance decisions: loosening a check means letting wrong data pass acceptance.
- The acceptance gate of upload.py: jurisdictions that do not pass acceptance are not uploaded.
- Data rows registered by others.

**Checks after a change** (a change is not finished until all are done)
1. Before the change, save the current clause ids: `python database/tools/clause_diff.py --save`.
2. Run the samples: `python database/samples/slicers-2026-10-23/run_slicers.py`; the results must match the results table of the samples README; for intended changes, update that table and give the reason.
3. Full build: `python database/tools/build.py`, with zero errors.
4. `python database/tools/clause_diff.py`: it lists the documents whose clause ids changed, and reports an error when an id still cited by parameters, absence records or superseded.csv has disappeared; fix those citations in the same change.
5. Re-run `python database/tools/build.py --jur <jurisdiction>` for each jurisdiction that had passed acceptance; each must still show `PASSED`.
6. New formats: put the original into a folder under `samples/`, add an entry to run_slicers.py, add a row to the results table of the samples README, and add a row or change the status in the table of §4.3.

**Records and delivery**: write a `Tool changes` item in the session record: which file was changed, why, which documents it was checked on, and the results of the checks above. upload.py uploads only data, not tools, so whoever changed the tools sends back `tools/` and `samples/` together with the data; when several people changed the same tool, re-run the acceptance of every jurisdiction after merging.

## 5. Acceptance (by collectors, per jurisdiction)

After finishing a jurisdiction, run:

```bash
python database/tools/build.py --jur <jurisdiction code>
```

It checks only this jurisdiction's data and writes nothing. With zero errors and zero gaps it prints `PASSED` (exit code 0), meaning the jurisdiction passes acceptance; otherwise it lists each error and gap.

Data checked: the jurisdiction's documents and absence records; the parameters, treaty documents and treaty rows of the jurisdiction and its pairs; and the intl documents.

**Errors**:
- A file is missing, its hash does not match, no text can be extracted, the Arabic text layer is garbled, the url is not on an official domain, the type or category is invalid, lang is empty, the id prefix is wrong, or a treaty document's jur is not a pair;
- A parameter's cite_id does not exist, its quote is not verbatim, its scope, subject, slot, name or unit is invalid, its param_id is not `<scope>.<slot>.<name>`, or its value does not fit its unit;
- An absence record has no jur, or does not fill exactly one of category and subject + slot, or an absence record for categories 1–4, 9 or a slot does not cite the provision on the scope of the tax;
- A treaty row's pair is written wrongly, or the document it references does not exist;
- A date is not YYYY-MM-DD (dates of effect of documents and parameters, the date of entry into force of a treaty row, since in superseded.csv).

**Gaps**:
- Any of the 12 categories (9 content + 3 page categories) with neither a document nor an absence record;
- Any of the 6 slots for companies and for individuals with neither a parameter of the jurisdiction nor an absence record;
- Any pair the jurisdiction is in charge of (it comes first in alphabetical order) without a treaty row; for a pair with no treaty, doc_id is empty and the note says "no treaty";
- Downloads in blocked.csv for the jurisdiction that are not yet in doc.csv; if confirmed not needed, delete the row and give the reason in the session record.
