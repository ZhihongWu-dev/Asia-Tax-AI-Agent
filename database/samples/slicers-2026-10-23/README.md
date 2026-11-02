# Slicer samples, 2026-10-23

For whoever maintains `database/tools/build.py`, which since 2026-10-24 are the collectors (数据库规范.md §4.9): when a
document is sliced badly, the collector fixes the slicer with the method below and runs the six checks of §4.9. Only a
document that cannot be sliced (a scan, no recognisable numbering) is cited by page or as a whole (§4.3).

The originals used to write and check the slicers. They are **not registered** in the library: some are copies from
non-official hosts, the Korean file is incomplete. Register each country's documents with `database/tools/fetch.py` from
the official host before any parameter cites them.

| File | Document | Source | State |
|---|---|---|---|
| `id.uu36-2008.htm` | UU No. 36 Tahun 2008 (fourth amendment of the Income Tax Law, UU 7/1983) | Internet Archive copy (2024) of https://jdih.kemenkeu.go.id/fulltext/2008/36TAHUN2008UU.htm | complete; archive copy |
| `jp.cta.xml` | 法人税法 (昭和40年法律第34号), law id 340AC0000000034 | https://laws.e-gov.go.jp/api/1/lawdata/340AC0000000034 (official e-Gov API) | complete |
| `kr.cita.xml` | 법인세법 (법령ID 001563, 공포 2025-12-23 제21217호) | https://www.law.go.kr/DRF/lawService.do?OC=test&target=law&LM=법인세법&type=XML (official DRF API) | **truncated** at 823 KB (~1.4 KB/s, cut after 580 s); all 213 조문 present, 부칙 cut |
| `in.ita1961.pdf` | Income-tax Act 1961 (India Code consolidated PDF) | Internet Archive capture 2023-10-31 of https://www.indiacode.nic.in/bitstream/123456789/2435/1/a1961-43.pdf | complete; replaced by the Income-tax Act 2025 from 2026-04-01, same typesetting |
| `in.ita2025.pdf` | Income-tax Act 2025 (No. 30 of 2025) as amended by the Finance Act 2026 | Internet Archive capture 2026-06-12 of https://www.incometaxindia.gov.in/documents/d/guest/income_tax_act_2025_as_amended_by_fa_act_2026-pdf (the site answers 403 from here) | complete, 686 pages |
| `vn.cit2025.html` | Luật Thuế thu nhập doanh nghiệp 67/2025/QH15 | https://ketoananpha.vn/luat-thue-thu-nhap-doanh-nghiep-2025 (third-party page; thuvienso.quochoi.vn returned 403) | complete text, table of contents first |
| `my.ita1967.pdf` | Income Tax Act 1967 (Act 53), LOM reprint as at 1 January 2019 | https://repositori.mypolycc.edu.my/bitstream/123456789/5389/1/Act_53_20190101.pdf (academic repository copy of the official reprint) | complete, 644 pages |
| `th.rc.th.5937.html`, `th.rc.th.5939.html` | ประมวลรัษฎากร หมวด 3 ภาษีเงินได้, sections 38-64 and 65-76 สัตต (Thai, authoritative) | https://www.rd.go.th/5937.html and 5939.html (official) | complete |
| `th.rc.37749.html`, `th.rc.37764.html` | Revenue Code, Chapter 3 Income Tax, sections 38-64 and 65-76 ter (English translation) | https://www.rd.go.th/english/37749.html and 37764.html (official) | complete; lags the Thai text (76 จัตวา-สัตต missing) |
| `ae.ctl2022.pdf` | Federal Decree-Law No. 47 of 2022 on the Taxation of Corporations and Businesses (unofficial English translation) | https://mof.gov.ae/wp-content/uploads/2022/12/Federal-Decree-Law-No.-47-of-2022-EN.pdf (official) | complete, 56 pages |
| `ae.ctl2022.ar.html` | مرسوم بقانون اتحادي رقم (47) لسنة 2022 (Arabic, authoritative, consolidated) | Internet Archive capture 2025-06-18 of https://uaelegislation.gov.ae/ar/legislations/1582 (the portal answers 403 from here) | complete; the Arabic PDFs of mof.gov.ae and of the portal have a garbled text layer (ligatures reversed, letters lost) and are rejected by the build |

| `treaty.syn.jp-my.pdf`, `treaty.syn.jp-th.pdf` | Synthesised texts of the MLI and the Japan-Malaysia and Japan-Thailand agreements | https://www.mof.go.jp/tax_policy/summary/international/tax_convention/SynthesizedTextforJapan_Malaysia_EN.pdf and ..._Thailand_EN.pdf (official) | complete |
| `treaty.tr.in-jp.pdf`, `treaty.tr.id-jp.pdf` | Japan-India and Japan-Indonesia agreements, revised texts with MLI boxes | https://www.mof.go.jp/english/tax_policy/tax_conventions/india.text.rev.en.pdf.pdf and https://www.mof.go.jp/tax_policy/summary/international/tax_convention/200612indo_e.pdf (official) | complete |

| `jp.nta.tsutatsu.03_03_01.htm`, `jp.nta.tsutatsu.02_01_05.htm` | 法人税基本通達 第3章第3節 (dividends from foreign subsidiaries) and 第2章第1節第6款 | https://www.nta.go.jp/law/tsutatsu/kihon/hojin/03/03_03_01.htm and .../02/02_01_05.htm (official) | complete pages |
| `kr.nts.intltax-rule.xml` | 국제조세사무처리규정 (NTS administrative rule) | https://www.law.go.kr/DRF/lawService.do?OC=test&target=admrul&ID=2100000257616&type=XML (official API) | complete |
| `th.mr.21452.html` | Ministerial regulation amending กฎกระทรวง ฉบับที่ 126 (exemptions) | https://www.rd.go.th/21452.html (official) | complete |
| `in.itr2026.pdf` | Income-tax Rules, 2026 (G.S.R. 198(E), Hindi and English) | https://a2ztaxcorp.net/wp-content/uploads/2026/03/Income-tax-Rules-2026.pdf (third-party copy of the Gazette; the official host answers 403 here) | complete, 977 pages |

`run_slicers.py` runs the slicers on these files (all countries, or the codes given) and prints counts, first and last
ids, number gaps and sample clauses:

```bash
python database/samples/slicers-2026-10-23/run_slicers.py            # or: ... run_slicers.py vn my th ae
```

Results on 2026-10-23:

| Country | Slicer | Articles / sections | Paragraphs | Number gaps |
|---|---|---|---|---|
| Indonesia | `slice_id` | 25 (Pasal 2-35) | 122 | expected: an amending act holds only the articles it changes |
| Japan | `slice_jp` | 252 of 262 (10 `削除` dropped) | 876 | all `削除` |
| Korea | `slice_kr` | 181 of 213 (32 `삭제` dropped) | 642 | all `삭제` |
| India | `slice_in` | 688 (1-298) | 2,162 | sections omitted by amending Acts |
| India, 2025 Act | `slice_in` | 537 (1-536) | 2,270 | none |
| Vietnam | `slice_vn` | 20 (Điều 1-20) | 85 | none |
| Malaysia | `slice_act(..., "my")` | 249 (1-156) | 835 | none |
| Thailand, Thai | `slice_act(..., "th")` | 43 + 30 (38-64, 65-76 สัตต) | 85 + 60 | none |
| Thailand, English | `slice_act(..., "th")` | 44 + 24 (38-64, 65-76 ter) | 76 + 51 | none |
| Treaties (English, Japanese MoF) | `slice_en_treaty` | 28, 27, 29, 30 | 88, 88, 94, 85 | none; MLI boxes cut as `<art>.mli<N>` (9, 8, 11, 10 boxes; a header broken before "4 of the MLI" counts since 2026-10-23) |
| Japan, NTA circulars | `slice_jp_tsutatsu` | 6 and 20 items | - | none; captions kept with their item |
| Korea, administrative rule | `slice_kr` (AdmRulService) | 152 (1-128) | 180 | none |
| Thailand, ministerial regulation | `slice_act(..., "th")` falls back to ข้อ | 3 | 2 | none |
| India, Income-tax Rules 2026 | `slice_in` | 333 | 1,241 | none; the Hindi half is skipped |
| UAE, Arabic | `slice_act(..., "ae")` | 70 (1-70) | 263 | none |
| UAE, English | `slice_act(..., "ae")` | 70 (1-70) | 262 | none |

## How a slicer is written

A slicer is found on a real text, not designed up front. A family usually takes three to five rounds:

1. Read the text: open the text of one document, look at the first few hundred lines and one passage in the middle, and
   find the fixed form of an article heading (what starts the line, how the number is written, whether a title follows,
   whether sub-paragraphs are `(1)` or `1.`).
2. Write one regular expression that matches heading lines only, run it, print the line numbers and article numbers it hits.
3. Look for faults in the hits. Seen so far: the table of contents matches too (the numbering starts again); page numbers
   pass for article numbers; a PDF splits `第` and `十二条` over two lines; a list item `3. the Act` inside a paragraph
   passes for section 3; a repealed article is a one-line `[Repealed]` stub; a reference such as `Article 47 of this
   Decree-Law` starts a line after a line break (UAE); the page-foot amendment notes `1. Subs. by Act 4 of 1988` look like
   sections (India); a note mark `*` or the Symbol-font glyph U+F02A stands before the number (Malaysian reprint); a
   website spells `Quater` as `Quarter` and `Sexies` as `Sex`, and the Thai page puts `ทวิ` on the line after `มาตรา 49` (Thailand); an Arabic PDF reverses the lam ligatures (`املادة` for `المادة`) and loses letters (UAE); one style tried on another country's text finds
   false headings (a Malaysian line `section 154 ...` read as a Thai heading).
4. Add one rule per fault: numbers must not decrease, otherwise a new run starts, and the first run whose blocks hold real
   text (on average at least 150 characters) is taken; page numbers are removed first; split headings are joined; a line
   starting in lower case is not a heading; repeal stubs are listed apart; a UAE heading needs `(N)` or a dash; footnote
   lines are dropped by their wording; the note marks are allowed before the number; a suffix alone on a line is joined to its heading; a garbled Arabic text layer is an error, not a slicing problem; the 2025 Indian Act puts a tab after the section number and its title on the line before, so its headings are told from table rows by the tab (a line written with a space counts only when its number is the next one expected); numbering that falls back to anything but 1 inside a body is a stray number and is skipped, and the last section ends where the same numbering starts over; Latin suffixes are normalised and
   ordered by rank (bis < ter < quater ...); each country uses only its own style.
5. Run again and compare three things: the number of articles with the law's total, the first and last article numbers,
   and every gap in the numbering. A gap goes back to step 3 unless the article is repealed or deleted.
6. Record the result in the table above. Collectors cite clauses only after their country's slicer has passed this.

Two notes: the Japanese (e-Gov API) and Korean (law.go.kr DRF) legal databases deliver structured XML in which articles,
paragraphs and items are tags; slicing by structure is more reliable than by pattern, so those two slicers read the raw
XML, not the text. Indonesia has no official consolidated text: an amending act (such as UU 36/2008) quotes each replaced
article in full under Pasal I, so the same slicer yields the new wording, but only for the articles it amends; the
original law UU 7/1983 and every amending act have to be registered together.
