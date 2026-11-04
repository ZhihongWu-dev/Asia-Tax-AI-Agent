# Session log

One section per session, appended at the end (format: 采集任务单.md, part 4).

## 2026-10-23 cn (pilot run of the whole procedure)
- Registered: 19 domestic documents and 3 attachments (EIT Law and Regulations, IIT Law and Regulations, foreign tax credit notices 2009-125 and 2017-84, IIT foreign income 2020-03, special tax adjustments 2009-02, GAAR Order 32, beneficial owner 2018-09, residence 2009-82 / 2014-09 / 2019-34, treaty benefits 2019-35 with its form, residence certificate 2025-04 with its forms, indirect transfers 2015-07, withholding 2017-37, STA treaty list, treaty dividend rate table 2008-112); 36 treaty files for the 9 pairs cn owns (English treaty, protocols, memoranda, exchanges of notes and MLI synthesised texts from the STA treaty pages; Hong Kong in Chinese only).
- Download failures: none (all with --engine curl).
- Parameters added: 47 (22 domestic covering the 12 slot cells, 25 treaty).
- Absence records added: 1 (page_deadlines).
- Slicing problems: none for laws, regulations, treaties and synthesised texts; short protocols, memoranda and exchanges of notes slice by page (they have no Article headings).
- Rate-table mismatches: not checked against cn.sta.2008-112 (registered as page_rates only).
- Gaps found: CFC white list Guoshuihan [2009] No. 37 not found on official hosts; the exemption of foreign individuals' dividends from foreign-invested enterprises (Caishuizi [1994] No. 20) not collected; superseded.csv not filled for the Hong Kong protocols (only Article 10 was checked: the Fourth Protocol adds a main-purpose test, it does not replace the rates).
- Questions: MLI applicability for cn-in (the STA page has no synthesised text; the OECD MLI matching database was not consulted).
- Acceptance: PASSED (errors=0 gaps=0).

## 2026-10-23 cn (open items of the pilot)
- Registered: cn.gsh.2009-37 (CFC white list, page label 全文有效), cn.cs.2026-27 (foreign individuals' dividends from foreign-invested enterprises, from 2026-09-01; Ministry of Finance page), intl.mli.positions.cn.en (China's final MLI reservations and notifications, STA MLI page).
- Not registered: Caishuizi [1994] No. 20. Its only in-scope item, 2(8), is repealed from 2026-09-01 by cn.cs.2026-27 item 3; the fgk page carries no validity label.
- Parameters added: 15 (12 CFC white-list countries, cn-in principal purpose test, 20% for foreign individuals' FIE dividends in outbound_wht and final). Changed: cn-hk.anti_abuse.ppt_applies now cites Fifth Protocol Article 6 (Article 24 (附)); the Fourth Protocol's Article 4 it cited was cancelled from 2020-01-01.
- superseded.csv: 56 rows. cn-hk 15 (Second to Fifth Protocols; dates from the footnotes of the IRD consolidated text), cn-in 10 (2018 Protocol; STA announcement 2019 No. 28), cn-kr 9 (Second Protocol 2006, Guoshuifa [2006] No. 100; the 2007 Memorandum replaces the 1994 one), cn-sg 16 (Second Protocol 2009 and Third Protocol 2010, STA notices; MLI replacements of 9.2, 10.6, 11.8, 12.7), cn-id 4 and cn-jp 2 (MLI replacements of 4.3 and 9.2). Rows for protocols are made in both the treaty and the synthesised text: the STA synthesised texts merge the MLI only, not the bilateral protocols (cn-sg still reads '6 months' and '10 per cent').
- MLI: not applicable to cn-in and cn-hk; neither is in China's Article 2 notification list. The other 7 treaty notes now give the effect dates from the synthesised texts (2023-01-01 for withholding; cn-vn 2024-01-01).
- Slicing problems: treaty.cn-in.1994.p2.en was cut into 3 articles because lines such as "Article 5 (Permanent Establishment) of the Agreement shall be replaced" were taken as headings; fixed in build.py, now 13 articles. treaty.cn-hk.2006.p3.zh has only 2 articles and slices by page (cited as #p1).
- build.py fixes: a '24*' row matched '24x' articles as well (a '1*' row would have dropped Articles 10-19); removed paragraphs and lines now also leave the article text; an MLI box header broken before '4 of the MLI' is now cut as a box (treaty.cn-jp.1983.mli.en#4.mli4).
- Questions: none.
- Acceptance: PASSED (errors=0 gaps=0).

## 2026-10-23 hk
- Registered: Inland Revenue Ordinance (Cap. 112, e-Legislation RTF, English only: both language texts are authentic); IRD Certificate of Resident Status page and FAQ; forms IR1313A/B and IR1314A/B; DIPN 44 (beneficial ownership, paragraphs 81-83); IRD treaty list and treaty rate table; 7 treaty orders under s.49 (Indonesia, India, Japan, Korea, Malaysia, Thailand, Vietnam with its 2014 Second Protocol in Schedule 2); 6 IRD synthesised texts; notes with Japan (2012) and Thailand (2008); the MLI text (intl.oecd.mli.en) and Hong Kong's MLI Article 35(7)(b) notifications (OECD).
- Download failures: none.
- Parameters added: 41 (18 domestic, 23 treaty). Residence follows s50AAC(1) "resident for tax purposes"; foreign dividends follow the FSIE rules (s15I, s15K, s15M, s15N; from 2023-01-01 per Schedule 55).
- Absence records added: 8 (no dividend withholding, no CFC, individuals not taxed on dividends at home or from abroad, no treaty claim procedure for dividends, no withholding deadline page).
- superseded.csv: 11 rows (MLI principal purpose test replacing the treaties' own anti-abuse paragraphs for Indonesia, Japan and Korea; the Vietnam Second Protocol replacing Article 25).
- Slicing problems: the protocol paragraphs in Part 2 of the orders were counted as paragraphs of the last article, and Schedule 2 (the Vietnam Second Protocol) was dropped; build.py now cuts them as <doc>#protocol.N and <doc>#sch2.N. The MLI text sliced by page; it now slices by article (intl.oecd.mli.en#7.1). treaty.hk-th.2005.notes.en is a scan with an imperfect OCR layer (not cited).
- Rate-table mismatches: not checked.
- Handoff to a person: none.
- Acceptance: PASSED (errors=0 gaps=0).

## 2026-10-24 sg
- Registered: Income Tax Act 1947 (Singapore Statutes Online, whole Act with its 36 lazily loaded parts filled in by fetch.py; English only, the authentic text); IRAS pages on company residence and the Certificate of Residence, the withholding tax rate table and the DTA list; treaties with Thailand (2015, with MLI Annex A and the 1975 Convention in Annex B) and Vietnam (1994, with MLI Annex A and the 2012 Second Protocol in Annex B) as IRAS PDFs.
- Download failures: Singapore Statutes Online answers a client without a browser with an AWS WAF challenge (HTTP 202) after about three requests; the challenge was not bypassed. fetch.py now waits 4 minutes after each challenge and asks for the same part again; the whole Act took about 70 minutes.
- Parameters added: 21 (12 domestic, 9 treaty). Dividends of Singapore companies are exempt for every recipient (s13(1)(za)); foreign dividends are exempt under s13(8) if subject to tax at a headline rate of at least 15% (s13(9)).
- Absence records added: 5 (no CFC as slot and category, no beneficial ownership guidance, no treaty claim procedure for dividends, no withholding deadline page).
- superseded.csv: 13 rows (Vietnam Second Protocol and MLI amendments, the 1975 Thailand Convention).
- Slicing problems: none for the Act (358 sections). Annex A (MLI amendments as numbered items) and Annex B (Roman-numeral protocol articles) were glued to the last article; build.py now cuts them as <doc>#annexA.N and <doc>#annexB.N. The IRAS DTA list loads its rows by script, so the saved page holds no rows; treaty dates come from the PDFs.
- Rate-table mismatches: not checked.
- Handoff to a person: none for collection. Upload: H2, supabase_key in .env is a publishable key and cannot write to the private bucket; a secret key is needed.
- Acceptance: PASSED (errors=0 gaps=0).

## 2026-10-26 jp
- Registered: Corporation Tax Act and its Cabinet Order, Income Tax Act, Special Taxation Measures Act and the Reconstruction Funding Act (e-Gov law API XML, current versions, Japanese only: the authentic text); NTA basic circular on ITA s2 (domicile); NTA Tax Answers No.2888 (treaty claims), No.9210 (certificate of residence), No.2505 (withholding deadlines) and No.2884 (withholding rates for non-residents); treaty Form 1 page; the MoF treaty list; MoF synthesised texts for Korea, Malaysia, Singapore, Thailand and Viet Nam; the 2010 Singapore Protocol; the 2014 Viet Nam exchange of notes.
- Not registered: the scanned original treaty PDFs on the MoF site (no text layer; the synthesised texts carry the same articles with text), and the JLT English translation of the Corporation Tax Act (last updated for Act No. 23 of 2008, so out of date).
- Download failures: none. Tax Answer No.2879 was registered by mistake (it covers land purchases from non-residents) and replaced by No.2884.
- Parameters added: 53 (31 domestic, 22 treaty). Withholding 20% (ITA s213(1)) plus the 2.1% reconstruction surtax, 15% for listed shares (STMA s9-3); foreign dividends 95% exempt at 25% for 6 months (CTA s23-2, Order s22-4); CFC at 10% with 20% / 27% tax burden thresholds (STMA s66-6, s40-4); no GAAR, only the family-company rules (CTA s132, ITA s157).
- Absence records added: 1 (no beneficial ownership guidance).
- superseded.csv: none. The MoF synthesised texts merge the amending protocols (Malaysia 2010, Singapore 2010) and contain no "[REPLACED" brackets.
- Slicing problems: none (e-Gov XML cut as #<article>.<paragraph>, e.g. jp.cta#23-2.1).
- Rate-table mismatches: none; NTA No.2884 shows 20.42% and 15.315%, which is 20% and 15% with the 2.1% surtax.
- Handoff to a person: none.
- Acceptance: PASSED (errors=0 gaps=0).

## 2026-10-26 th
- Registered: Revenue Code Chapter 3 Sections 38-64 and 65-76 and the income tax rate schedule (RD pages, Thai authentic text) with the RD English translations of both section ranges; Royal Decree No. 442 (B.E. 2548, Thai) and the RD English translation of the consolidated Royal Decree No. 10; RD pages on certificates of residence (individual, company), the guide for foreign companies and the DTA list; Thailand's and Viet Nam's MLI positions; the Thailand-Viet Nam agreement as six RD HTML pages (Articles 1-5 ... 26-28).
- Download failures: the RD PDF of the Thailand-Viet Nam agreement (vietnam_e.pdf) timed out twice and, once complete (4.4 MB, 39 pages), proved to be a scan with no text layer; the RD HTML pages of the same agreement were registered instead. The English rate schedule page (english/37771.html) answered HTTP 500; the Thai schedule (5938.html) is the authentic text and was registered. RD_10.pdf needed --engine curl after requests timed out.
- Parameters added: 19 (17 domestic, 2 treaty). Dividends to foreign companies 10% (s70 with rate schedule item (2)(c)); to individuals 10% (s50(2)(e)); foreign dividends exempt at 25% of voting shares for 6 months if taxed at 15% or more (Royal Decree No. 10 s5 vicies, inserted by No. 442); CIT 20%; individuals resident at 180 days (s41).
- Absence records added: 7 (no CFC as slot and category, no GAAR as slot and category, no beneficial ownership guidance, no residence guidance beyond the Code, no treaty claim procedure).
- superseded.csv: none.
- Slicing problems: none; the RD article pages slice by "ARTICLE N" and the page navigation is not part of any clause.
- Rate-table mismatches: none; th.rd.foreign-company shows dividends 10%.
- Handoff to a person: none.
- Acceptance: PASSED (errors=0 gaps=0).

## 2026-10-31 cn jp th (parameters added by the rule-layer side)
- Added 16 parameters without new documents, quotes verbatim from clauses already in the library: cn beneficial-owner factors and safe harbours (STA 2018 No. 9 items 2-5: pass-on share 50 and months 12, parent holding 100, holding months 12, safe harbours for government / listed company / individual / 100%-owned applicant), cn withholding deadline 7 days from the day the obligation arises (STA 2017 No. 37 item 7), cn certificate of resident status of the current or previous year accepted (STA 2019 No. 35 art. 7); jp affiliated-company threshold one third (CTA 23(4), stored 33.33), non-controlling 5% (23(6)), small-company capital JPY 100m (66(2)), related-company 50% (SMA 66-6(2)), withholding payment by the 10th of the next month (ITA 212(1)); th remittance within 7 days after month end (s70).
- Reason: the rule layer needed these as parameters so that execution steps (deadlines, materials, safe harbours) cite clauses instead of being written by hand.
- Acceptance: cn PASSED, jp PASSED, th PASSED; full build params=212 errors=0. Not uploaded to the remote.

## 2026-10-31 cn hk sg jp th (penalty slot, bracket tables, categories 10 / 11, audit columns)
- Spec changes (owner side, 数据库规范.md §2, §3, §4.4, §5): new slot `penalty`; new document categories 10 (penalty provisions, counted in coverage) and 11 (interpretive sources, optional, never a parameter source: build error when param.cite_id points into a category-11-only document); bracket-table convention `<table>_bracket_<n>_rate` / `_upper`; two new param columns `changed_on`, `superseded_by` (empty for all existing rows). tools/build.py and tools/fetch.py updated accordingly (TABLES, SLOTS, CATEGORIES, COVERED_CATEGORIES, check_params).
- Registered: cn.law.tca (税收征收管理法, STA policy library, category 10), jp.gta (国税通則法, e-Gov API XML, category 10), th.rc2.th (Revenue Code Title 2 Chapter 2 ss14-27, RD page 5943, category 10). hk.cap112 and sg.ita1947 gained category 10 (s71 / s82A; s87 / s95 / s96 already in the text).
- Parameters added: 51. Penalty: cn art. 32 (0.05% per day), art. 69 (50%-300% fine on the withholding agent), art. 63 (50%-500%, reference); hk s71(5) 5%, s71(5A) 10% (reference), s82A 300%; sg s87 5% + 1% per month capped 12%, s95(1) 100%, s95(2) 200% and s96 300% (reference); jp s60(2) 14.6% / 7.3% first two months (reference) and 2 months, s67(1) 10%, s67(2) 5% and s68(3) 35% (reference); th s27 1.5% per month capped at the tax, s22 100%, s26 200% (reference), s54 joint liability (bool). Bracket tables: jp ITA s89 (7 brackets, 13 rows), th rate schedule (1) as amended by Act No. 44 B.E. 2560 (7 brackets, 13 rows).
- Checked all 26 treaty texts for most-favoured-nation and limitation-on-benefits clauses: no MFN clause; LOB only in hk-kr Article 26 (Korea not collected); the other pairs rely on the MLI PPT or a protocol PPT (cn-in Article 27A), already parameterised.
- Slicing problems: none (fgk page, e-Gov XML and RD page cut with the existing slicers).
- Acceptance: cn, hk, sg, jp, th all PASSED; full build docs=136 params=263 errors=0. Not uploaded to the remote.

## 2026-10-31 jp hk th + intl (penalty round 2, interpretive sources)
- Registered: jp.nta.9205 (Tax Answer No.9205, delinquent-tax rates by period under STMA s94; category 10) and jp.nta.entai_wariai (the rate table page; registered but its table is not captured by the slicer, so quotes come from No.9205). Category 11 (interpretive sources, no coverage requirement): intl.oecd.mtc2017.full (OECD Model Tax Convention 2017 full version PDF, 14 MB, direct content/dam link; the condensed-version page answers 403 to automated requests and was not retried; generic paragraph slicing gives 217 coarse clauses), cn.sta.2018-09.interp (STA interpretation of Announcement 2018 No. 9 as republished by the Jiangsu Tax Service), sg.iras.etax.dta (IRAS e-Tax Guide on DTAs, 4th edition), hk.ird.ar72 (Advance Ruling Case No. 72), th.rd.ruling.0811-6620 (RD ruling on the s27 surcharge).
- Parameters added: 7 (jp special delinquent-tax rates 2021 / 2022-2025 / 2026 after two months, the first-two-months rates for 2022-2025 and 2026 as reference, hk 6-month period of s71(5A), th 0.75% extended-deadline surcharge as reference). jp.penalty.late_interest_pct_per_year note updated.
- Acceptance: jp, hk, th PASSED; full build docs=143 params=270 errors=0. Not uploaded.
- Handoff: the OECD PDF would need a commentary-aware slicer (article / paragraph numbers) before decisions can cite specific paragraphs; the NTA rate-table page needs table extraction in the nta slicer.

## 2026-10-31 cn jp th (exchange-rate rules)
- Registered: jp.nta.tsutatsu.cta.13-2-1 (CTA basic circular chapter 13-2 section 1: yen conversion at the TTM of the transaction day, main bank, nearest earlier day when none; category 1), th.rc1.th (Revenue Code Title 1 ss5-13, for s9: rate announced by the Ministry of Finance; category 1), th.rd.p132-2548 (departmental order Por. 132/2548 applying the 2005 announcement to withholding under s70: commercial bank selling rate of the day or BoT reference average selling rate, chosen once; category 1). cn: EIT Reg. art. 129, IIT Law art. 16, IIT Reg. art. 32 and STA 2017 No. 37 item 4 were already in the library.
- Parameters added: 16 text parameters `<jur>.<slot>.fx_rate_*` (kind / day / bank / fallback / consistency) for cn (outbound_wht, inbound company and individual), jp (inbound company) and th (outbound_wht, inbound company). They are read by optimization/tools/fx.py --jur. Singapore and Hong Kong prescribe no rate (no parameter; noted in the tool).
- Acceptance: cn, jp, th PASSED; full build errors=0. Not uploaded.
- Not collected: the 2005 Ministry of Finance announcement itself (cited through s9 and Por. 132/2548), the Income Tax basic circular 57-3-2 for Japanese individuals.

## 2026-10-31 cn hk sg jp th (restructure slot: share-transfer taxes)
- Spec change (owner side): new slot `restructure` (8 slots); category 9 widened to the tax burden of share transfers (income tax on gains, stamp duty on share transfers, valuation of unlisted shares); deed tax and other stamp duties stay out.
- Registered: cn.sta.2014-67 (IIT equity-transfer measures: net-asset assessment), cn.law.stamp (Stamp Tax Law, Guangdong Tax Service text; its rate table is missing from the HTML) + cn.law.stamp.a01 (PDF with the rate table, Shanghai DRC, sh.gov.cn), hk.cap117 (Stamp Duty Ordinance, e-Legislation), sg.iras.stamp.shares (IRAS share duty page), th.rc6.stamp.th (stamp duty schedule), jp.nta.tsutatsu.cta.9-1-3 (valuation of unlisted shares 9-1-13 / 9-1-14). Blocked: sg.sda1929 (Stamp Duties Act; sso.agc.gov.sg refused / hung; not retried with disguised requests) — the 0.2% duty is recorded from the IRAS page without a rule until the Act is registered. The ssf.gov.cn PDF of the Stamp Tax Law failed TLS verification (replaced by the Shanghai PDF).
- Parameters added: 54 (domestic: cn 13, hk 2, sg 6, jp 6, th 6; treaty Article 13: cn-hk 4, cn-sg 3, cn-jp 1, cn-th 1, hk-jp 2, hk-th 2, sg-th 3, jp-sg 4, jp-th 1). Absence records: hk company / individual and sg company / individual restructure (no capital gains tax).
- Acceptance: cn, hk, sg, jp, th PASSED; full build docs=153 params=340 absence=26 errors=0; slot gaps 96 = 6 uncollected jurisdictions × 8 slots × 2. Not uploaded.
- Handoff: the Singapore Stamp Duties Act (blocked.csv); the Japanese Income Tax Act Cabinet Order art. 281 (individuals' 25% / 5% test) and the Thai Ministry of Finance exchange-rate announcement of 2005 are cited through other documents only.

## 2026-10-31 sg (foreign-sourced income guide)
- Registered: sg.iras.etax.fsi — IRAS e-Tax Guide "Tax Exemption for Foreign-Sourced Income", fifth edition (30 Jan 2026; the URL keeps the third-edition file name), category 1. Para 8.2 settles how the s13(8) "subject to tax" condition is read for income routed through a no-tax jurisdiction (not met) and what counts as underlying tax; cited by rule-layer decision D-sg-3 on sg.inbound.exemption.
- Acceptance: sg PASSED; full build docs=154 errors=0. Not uploaded.

## 2026-10-31 round 6: two documents cited only indirectly, one blocked source retried
- Registered: jp.ita.order (所得税法施行令, e-Gov XML; category 9; art. 281(1)(iv)(b) and (6): the 25% / 5% test for non-resident individuals' gains on shares of a Japanese company), th.mof.fx.2548 (Ministry of Finance announcement of 8 Feb 2548 under s9 of the Revenue Code as amended by No. 2 of 2563; category 1; Revenue Department page 25611).
- Parameters: jp.restructure.taxable_holding_pct_min.individual, taxable_holding_years.individual, taxable_transferred_pct_min.individual (art. 281(6)); th.outbound_wht.fx_rate_option_bank, fx_rate_option_bot, fx_rate_scope (announcement clauses 2(1), 2(2), 3(1)); th.outbound_wht.fx_rate_consistency now cites the announcement (clause 2 second paragraph) instead of Por. 132/2548. The selling-rate readings (fx_rate_kind, fx_rate_kind.bot) stay with Por. 132/2548 because the announcement itself does not say buying or selling.
- Blocked: sg.sda1929 retried once with a plain request (no disguise); it hung and was stopped. blocked.csv has the second row. The IRAS page remains the source of the 0.2% share-transfer duty.

## 2026-11-02 cn (treaty dividend holding period)
- Registered: cn.sta.2009-81 — STA Circular 2009 No. 81 on the dividend articles of tax treaties (fgk.chinatax.gov.cn, marked 全文有效 on the page fetched 2026-11-02), category 1, sliced cn_item into 6 items.
- Parameter: cn.outbound_wht.holding_months_min = 12 months (item 3(3): the direct holding ratio of a treaty's reduced rate met at all times within the 12 consecutive months before the dividend). Cited by rule-layer decision D-cn-8 on cn-hk / cn-kr / cn-sg 5% and cn-th 15%.
- Found missing while reviewing a report: the 5% rate had no holding period, so a holder that took the stake over just before the dividend was given 5%.
- Acceptance: full build docs=157 params=364 errors=0. Not uploaded.

## 2026-11-04 cn, hk, sg, jp, th (company exit)
- Scope change by the user's decision of 2026-11-04 (goals §6, relocating the paying company): the exit slot now covers a company moving its registration or place of effective management out, besides an individual leaving. Spec: 数据库规范.md / database_spec.en.md §3 slot list, the slot table and the coverage count; category 9 names the deemed liquidation of a company that leaves.
- Registered: cn.cs.2009-59 (Caishui [2009] No. 59 on enterprise restructuring, fgk.chinatax.gov.cn; category 9; cn_item, 13 items), cn.cs.2009-60 (Caishui [2009] No. 60 on enterprise liquidation, www.chinatax.gov.cn; category 9; cn_item, 6 items).
- Download failures: none
- Parameters added: 5 (cn.exit.deemed_liquidation from No. 59 item 4(1); cn.exit.gain_base from No. 60 item 4; cn.exit.rate from the EIT Law art. 4; cn.exit.shareholder_dividend_base and cn.exit.shareholder_gain_base from No. 60 item 5)
- Absence records added: 4 (hk, sg, jp, th: company exit; hk s14(1), sg s10(1), jp CTA art. 2(iii), th Revenue Code s65)
- Slicing problems: the two new pages and six earlier STA pages (cn.cs.2009-125, cn.gsf.2009-82, cn.gsh.2009-37, cn.sta.2008-112, cn.sta.2009-81, cn.sta.2014-09) carried the site footer (【打印】, 网站纠错 …) in their last item; fixed, see Tool changes.
- Rate-table mismatches: none
- Open check: STA Announcement 2026 No. 13 (restructuring administration, 2026-07-08) was read in summary only, not registered; by its summaries it concerns special tax treatment of mergers and divisions, not the change of registration in No. 59 item 4(1).
- Handoff to a person: none
- Tool changes: build.py (1) INDIVIDUAL_ONLY emptied: the company exit slot now counts for coverage — a change of the coverage rule, made at the user's instruction (the user is the person of H7 here); (2) html_text cuts the STA sites' page chrome (PAGE_CHROME: 【打印】, 网站纠错, 纠错或建议) at its first line in the second half of the page. Checks of §4.9: (1) clause_diff --save before; (2) run_slicers: same output with and without the change (the India 1961 paragraph count 2,163 against 2,162 in the README and the NTA circular counts differ from the README table already without it); (3) full build errors=0; (4) clause_diff: 8 documents changed, cited ids lost 0; the six earlier pages lost only the ~480-character footer, no item marker in the cut text; (5) acceptance: cn, hk, jp, th PASSED; sg NOT PASSED only on the download sg.sda1929 blocked since 2026-10-31; (6) no new format.
- Acceptance: cn PASSED, hk PASSED, jp PASSED, th PASSED; sg NOT PASSED (gap: download not resolved sg.sda1929, unchanged). Full build docs=159 params=369 absence_records=34 errors=0. Not uploaded.
