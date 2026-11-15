# Library gaps after adding ae, id, in, kr, my, vn (updated 2026-11-11)

For the collectors of `database/`. On 2026-11-10 the library gained 153 parameters, 1 absence record and 19 corrected
values, and was uploaded; with them every jurisdiction but Korea covers the six dividend slots; Korea's CFC followed later that day (section 1). What is still open:

## 1. Blocks a jurisdiction from the optimizer's search

None since 2026-11-10. The Korean CFC cells (H2 below) were closed the same day: the Act was registered as `kr.itca` (the law.go.kr page; the build's new `slice_kr_lawpage` keeps the formula's alt text, database_spec §4.3), with the parameters `kr.cfc.low_tax_top_rate_share_max`, `kr.cfc.control_pct_min`, `kr.cfc.related_holding_pct_min` and `kr.cfc.de_minimis_income_max`, and the rules of D-kr-14.

## 2. Values that are upper bounds or approximations until a document is added

- **ae**: residence by days (Cabinet Decision 85/2022, Ministerial Decision 27/2023 not registered): a UAE individual without a business is never resident; Ministerial Decision 116/2023 (participation exemption details); Qualifying Free Zone rates.
- **id**: PMK 107/PMK.03/2017 (CFC timing and base); PMK 18/PMK.03/2021 (reinvestment period and instruments); the Government Regulation fixing the art. 17(2c) dividend rate (the 10 % maximum is used); the start of the Law 7/2021 bands.
- **in**: surcharge (banded by income) and the 4 % cess (Finance Act 2026 ss. 1-3 are not sliced into clauses); the Income-tax Act 1961 (nothing before 2026-04-01); the in-kr treaty text (`treaty.in-kr.2015.law` holds only navigation); the entry into force of the 2007 India-UAE Protocol.
- **kr**: CIT and ITA Enforcement Decrees (18-4 holding period: the foreign-dividend exclusion is read on the holding threshold only); the Local Tax Act (the 10 % local income tax cites CIT 98-7(1)(ii) / ITA 156-8(1)(ii)); the addenda with start dates (18-4 from 2023-01-01 is inferred); CIT / ITA before 2026-07-01; art. 17(3) gross-up and art. 62 comparison for individuals above KRW 20m. CFC (D-kr-14): the inclusion of passive income under ITCA arts. 29(2) and 30(2) for a company that art. 28(ii) excludes is not modelled, so its floor may be too low; the three-year averages of Enforcement Decree arts. 61-62 and the indirect and related persons' holdings of art. 27(2) are left to the caller's facts; the de minimis cites the English translation of the Decree (the Korean Decree is not registered).
- **my**: P.U.(A)234/2022; the English para 4(2)-(3) of P.U.(A)235/2022 (dropped by `superseded.csv`); a document on how a non-resident claims treaty relief; commencement of the Sch 1 tables (no start dates); Sch 6 para 12B before 2025.
- **sg**: when the GAAR denies an exemption (reading `sg.anti_abuse.gaar`), an individual's dividend is charged at the Second Schedule (2026-11-11, D-sg-4): the figure is the tax if the Comptroller only denies the exemption (s33(2) leaves the adjustment to the Comptroller); the 50 % surcharge of s33A is not in it; Table 2 of the Second Schedule (YA 2017-2023, income of 2016-2022) is not entered, so an individual's schedule starts 2023-01-01; a non-resident individual's flat rate (s43) is not entered.
- **vn**: the Vietnamese original of CIT Law 67/2025 (only an unofficial English single clause); the PIT and CIT decrees; CIT Law 14/2008 (no vn company rules before 2025); PIT Law 04/2007 registered 2026-11-11 (individual rules before 2026-07-01; a resident's 5 % only from 2015-01-01); Law on Tax Administration 108/2025 and Decree 255/2026.
- **MLI positions** of the UAE, Indonesia, India, Korea and Singapore: without them there is no PPT parameter for ae-th, ae-vn, ae-my, id-vn, in-vn, my-sg, and the kr-th date is computed.

## 3. Library values reported, not changed

- Shared pair parameters carry one state's date where the two states apply the treaty from different dates: `hk-id`, `hk-my`, `hk-vn` (Hong Kong's 1 April), `in-jp` (India's dates; Japan 2006-07-01 and PPT 2020-01-01), `in-my` (Malaysia 2013-01-01, India 2013-04-01), `id-jp`, `id-kr`'s other rows, `id-my` (MLI date instead of the treaty date). The library has one date per parameter; a convention for two dates is a spec question.
- `vn.law.cit2025.en` is in force from 2025-10-01 while the vn CIT parameters start 2025-01-01: `trace.py` fails vn company cells dated before 2025-10-01.
- `ae.law.corporate-tax.legislation1582.en` arts. 44-47 are mis-sliced; `ae.mof.top-up-tax` and `ae.fta.withholding-faq` hold only page chrome; `treaty.ae-jp` row note says the convention is not registered although it is.
- `treaty.id-vn.*.mli.en` contains no MLI provisions and its heading names Cambodia; the `id-th` treaty row has no in-force date.
- `in.law.finance2026.gazette.en#s161(4)` holds the whole First Schedule; `treaty.in-sg.1994.en` lacks Articles 18-30; `treaty.hk-kr.2014.en#26` holds only paragraph 2.
- `vn.anti_abuse.related_party_non_arm_length_reassessment` is a transfer-pricing statement, not a dividend anti-abuse rule (no rule uses it).
- Old rows duplicated by the new bracket rows: `kr.final.*_marginal_rate_band*`, `my.final.individual_marginal_band_*`, `my.final.company_small_business_marginal_band_*`, `ae.final.individual_business_turnover_condition` (text); they could be marked `superseded_by`.
- New warnings: parameters citing page-sliced documents (`id.tax-law-compilation-2022`, `treaty.kr-vn.2019.protocol.mofa.text`, `vn.law.cit2025.en`), recorded in `database/session_log.md`.

## 4. Existing rule rows a reviewer should look at (not changed)

- `jp-kr.outbound_wht.cap_5` / `cap_15` start 1999-11-22; Article 29(2)(b)(i) gives 2000-01-01 on the Japan side.
- `jp-hk.anti_abuse.ppt` and `th-hk.anti_abuse.ppt` use Hong Kong's 2023-04-01; Japan and Thailand may apply the PPT to withholding only from 2024-01-01 (reasoning of D-id-10).

## Appendix: the writers' document lists (official sources, what each would give)

### ae


The URLs give the official publisher. The exact file addresses were not looked up or checked, because this round
fetches nothing.

| # | Document | Official source | What it would give |
|---|---|---|---|
| 1 | Cabinet Decision No. 85 of 2022 on the Determination of Tax Residency | UAE Ministry of Finance, mof.gov.ae (Legislation, Cabinet Decisions); FTA, tax.gov.ae (Legislation) | Art. 4 tests for natural persons: (1) usual or primary place of residence and centre of financial and personal interests; (2) 183 days in a 12-month period; (3) 90 days plus UAE/GCC nationality or a Residence Permit, plus a Permanent Place of Residence or UAE employment or business. Art. 3 for juridical persons. In force from 2023-03-01. With it, the existing `ae.residence.residence_days_min` and `ae.residence.conditional_residence_days_min` can be re-cited to the Decision (today they cite only the FTA guide TPGTR1) and `ae.residence.individual` rules can be written. Today a UAE individual without a business is never resident, so no source state gives that person a treaty rate (D-ae-2). |
| 2 | Ministerial Decision No. 27 of 2023 on the Determination of Tax Residency (implements no. 1) | mof.gov.ae | How days are counted (any part of a day counts; exceptional circumstances are left out) and the definition of a Permanent Place of Residence (arts. 3-5, cited by the FTA guide TPGTR1 at p. 37-38). Needed for the variables of the 90-day test. |
| 3 | Ministerial Decision No. 116 of 2023 on the Participation Exemption | mof.gov.ae | The conditions the Minister prescribes under Decree-Law arts. 23(2)(e) and 23(11): how the 9% subject-to-tax test is applied, the asset test, the 12-month counting, and the acquisition-cost alternative to the 5% holding (reported as AED 4,000,000; to be checked against the text). Would confirm reading (2) of D-ae-4 and allow an `exemption_acquisition_cost_min` parameter. |
| 4 | United Arab Emirates: MLI list of reservations and notifications (deposited 2019-05-29; MLI in force for the UAE from 2019-09-01 per `intl.oecd.mli.parties.20260915.en#p6`) | OECD depositary, oecd.org (BEPS MLI positions) | Whether the UAE lists Thailand as a Covered Tax Agreement. Thailand lists the UAE agreement (`intl.mli.positions.th.en#p9`, no. 54). If the UAE lists Thailand too, `ae-th.anti_abuse.ppt_applies` = yes would cite `intl.oecd.mli.en#7.1`. It would apply from 2023-01-01 for taxes withheld at source: MLI art. 35(1)(a), counted from Thailand's entry into force on 2022-07-01, the later of the two. The th-ae PPT rule is drafted in the report. The same document settles ae-vn (Vietnam lists the UAE, `intl.mli.positions.vn.en#p12`, no. 71) and ae-my (Malaysia lists the UAE, `intl.mli.positions.my.2022.en#p18`, no. 68). |
| 5 | Cabinet Decision No. 100 of 2023 (Qualifying Income) and Ministerial Decision No. 265 of 2023 (Qualifying Activities) | mof.gov.ae | The 0% rate of a Qualifying Free Zone Person on Qualifying Income (Decree-Law art. 3(2)), which includes holding shares. This is the free-zone holding-company route, which is not modelled today. Optional. |
| 6 | Readable replacements for two shells: the MoF top-up tax page (`ae.mof.top-up-tax`) and the FTA withholding-tax FAQ (`ae.fta.withholding-faq`, ae's only category-7 document) | mof.gov.ae; tax.gov.ae | Today both hold only page navigation. The first is the source of the "no CFC regime" statement in `ae.absent.cfc`. |

### id


Not fetched. URLs are the official portals; the collector locates the exact file there.

| Document | Official source | What it would give |
|---|---|---|
| PMK 107/PMK.03/2017, Penetapan Saat Diperolehnya Dividen dan Dasar Penghitungannya oleh Wajib Pajak Dalam Negeri atas Penyertaan Modal pada Badan Usaha di Luar Negeri Selain Badan Usaha yang Menjual Sahamnya di Bursa Efek | JDIH Kementerian Keuangan, https://jdih.kemenkeu.go.id | Timing (deemed receipt date) and base (share of profit after tax) of the art. 18(2) deemed dividend; whether indirect holdings count; credit of tax on a later actual dividend. Sharpens `id.cfc.include` (D-id-12). |
| PMK 18/PMK.03/2021 (implementing the Job Creation Law income tax changes) | JDIH Kementerian Keuangan, https://jdih.kemenkeu.go.id | The "certain period of time" and the investment instruments of art. 4(3)(f) (dividend reinvestment, `dividend_reinvested`, `cfc_profit_reinvested`); the foreign-expert regime of art. 4(1a); the art. 2(4)(c) tests for Indonesian citizens abroad. |
| The Government Regulation under art. 17(2d) fixing the final rate on dividends to resident individuals (PP 19/2009 and any later replacement, e.g. in the income tax regulation implementing Law 7/2021; the collector to confirm which is current) | JDIH / https://peraturan.go.id | The rate itself; today `id.final.dividend_tax_rate` records the statutory maximum of art. 17(2c) ("maximally 10%"). |
| Law 7/2021 (Harmonisasi Peraturan Perpajakan), closing provisions on the start of the new art. 17(1)(a) bands | https://peraturan.go.id or https://pajak.go.id | The start date of the five-band schedule (`id.final.progressive_bracket_*` have no effective_from; letter b states fiscal year 2022). |
| Indonesia's MLI position (reservations and notifications, incl. art. 35(2) and the list of covered agreements) | OECD MLI depositary page, https://www.oecd.org/tax/treaties/ (beps-mli-position-indonesia.pdf) | Confirms D-id-10 (Indonesia counts by calendar year, so the hk-id PPT applies to Indonesian withholding from 2024-01-01) and whether Vietnam is a covered agreement (`id-vn.anti_abuse.ppt_applies`). |
| Indonesia-Vietnam agreement as modified by the MLI, a file that contains the MLI provisions | DGT, https://www.pajak.go.id/en/tax-treaty | The registered file `treaty.id-vn.1997.mli.en` has no MLI text at all (no art. 7 box), although the DGT index says the MLI applies from 2024-01-01; Vietnam lists Indonesia as covered agreement 25 (`intl.mli.positions.vn.en#p5`). Needed for `id-vn.anti_abuse.ppt_applies`. |
| Indonesia-Thailand agreement: entry-into-force record (DGT treaty index entry for Thailand, or the ratification notice) | DGT, https://www.pajak.go.id/en/tax-treaty | The start date of `id-th.outbound_wht.*` (now blank; treaty.csv has no in_force_from; the text says signed 15 June 2001 while the doc id says 2012). The registered index page `id.dgt.treaty-index` lists only part of the treaties. |

### in


| Document | Official source | What it would give |
|---|---|---|
| India–Korea Agreement for the Avoidance of Double Taxation (2015), full text | Korean National Law Information Center, the treaty body or its English attachment: https://www.law.go.kr/trtyInfoP.do?trtySeq=12259 (the registered `treaty.in-kr.2015.law` holds only the page navigation, 107 characters); or India's DTAA page https://www.incometaxindia.gov.in/en/dtaa | Article 10 (dividend caps and holding conditions), the entry-into-force article, and whether a PPT applies (`in-kr.outbound_wht.*`, `in-kr.anti_abuse.ppt_applies`), so that `in-kr.*` and `kr-in.*` caps can be written |
| Entry into force of the First Protocol (2007) to the India–UAE Agreement: the CBDT notification or the UAE Ministry of Finance treaty record | India's DTAA page https://www.incometaxindia.gov.in/en/dtaa (UAE entry, protocol notification); UAE MoF treaty dashboard https://mof.gov.ae | The start date of `ae-in.outbound_wht.dividend_rate` (10%) and `ae-in.anti_abuse.main_purpose_test_applies`, both left without `effective_from`; and a `superseded.csv` row for the replaced Article 10(2) (`treaty.ae-in.1992.mli.en#10.2`, 5% / 15%), which is still sliced as current |
| Finance Act 2026, sections 1 to 3 as clauses (re-slicing of the registered `in.law.finance2026.gazette.en`, not a new document) | Already in `raw/in/`; the text is in `text/in.law.finance2026.gazette.en.txt` (lines about 49-1000 and 3080-3095) but `clause.csv` starts at section 4 | Section 3(15)-(16): the 4% Health and Education Cess on income-tax and surcharge (a plain `surtax` parameter for the outbound and final cells); section 3(4)(b): the surcharge table for income under section 207 (non-residents' dividends) |
| India's MLI position (list of covered agreements, reservations and notifications, including any Article 35(2) choice of "taxable period") | OECD MLI depositary page of India's position; by the pattern of the registered Viet Nam position (`intl.mli.positions.vn.en`): https://www.oecd.org/content/dam/oecd/en/topics/policy-sub-issues/beps-mli/beps-mli-position-india.pdf (URL not checked) | Whether India lists Viet Nam, Korea and the UAE as covered agreements (PPT parameters for `in-vn`, `in-kr`, `ae-in`), and the Indian start dates of the PPT (read in D-in-11 as the first tax year beginning after the later entry into force) |
| Income-tax Act 1961 (as in force to 31 March 2026) and the Finance Act 2025 | https://www.incometaxindia.gov.in | Rules for evaluation dates before 2026-04-01 (s115A/195 dividend withholding, s80M, s115BAA, Chapter X-A GAAR); today India has no rules before that date |

### kr


Nothing was fetched or registered; `database/` is unchanged.

#### Handoff to a person (database_spec §4.8)

- **H2 `kr.itca` (국제조세조정에 관한 법률, Act No. 21215, in force 2026-01-02), cells `kr|company|cfc` and `kr|individual|cfc`. Closed 2026-11-10:** registered from the page below with a slicer that keeps the alt texts (option (c)); kept here as the record of what was tried.
  - What it would give: Article 27(1)(i), the low-tax test "실제부담세액이 … 「법인세법」 제55조에 따른 세율 중 최고세율의 70퍼센트 이하" (actual tax burden at or below 70% of the top CIT rate). Article 27(2), the 10% holding ("발행주식의 총수 또는 출자총액의 10퍼센트 이상을 직접 또는 간접으로 보유한 자"). The Article 28 exclusions and the Article 29 passive-income rules. The CFC include rules (rate, schedule, credit) need these.
  - What was tried:
    - The law.go.kr page `https://www.law.go.kr/법령/국제조세조정에관한법률` is a frame shell. It points to `lsiSeq=280389`, efYd 20260102.
    - The body `https://www.law.go.kr/LSW/lsInfoR.do?lsiSeq=280389&chrClsCd=010202&urlMode=lsInfoP&efYd=20260102&ancYnChk=0` downloads with a plain GET (477 KB HTML). It is not usable as it stands:
      - The 70% figure exists only as the alt text of a formula image (`@@LATEX@@외국법인의실제발생소득 \times 「법인세법」제55조에따른세율중최고세율의70퍼센트@@/LATEX@@`). `html_text` in `database/tools/build.py` drops it.
      - The build has no Korean HTML slicer, so the Act would be one `#all` clause.
    - `lsPdfPrint.do?lsiSeq=280389` and `lsRtfPrint.do?lsiSeq=280389` return the site's error page to a plain GET. I did not script around it with cookies.
    - The law.go.kr English pages found (`engLsInfoR.do?lsiSeq=280815/261557/257977`) are other acts. KLRI `elaw.klri.re.kr/eng_service/lawTwoView.do?hseq=18138` is a 2010 version. KLRI English translations state that they have no legal authority.
  - What the person does, any one of:
    - (a) Apply for the law.go.kr Open API OC (§4.7) and fetch `https://www.law.go.kr/DRF/lawService.do?OC=<OC>&target=law&type=XML&LM=국제조세조정에 관한 법률`. Check that the XML gives the Article 27 formula as text; if not, OCR the formula image.
    - (b) Export the PDF in a browser as was done for 법인세법 / 소득세법 (`slice_kr_pdf`), then `ocr.py --images` for the formula.
    - (c) Approve a §4.9 tool change: keep `@@LATEX@@…@@/LATEX@@` alt texts in `html_text` and route law.go.kr `lsInfoR.do` HTML to `slice_kr_pdf`. Then the GET above can be registered with `fetch.py`.
  - Afterwards, collect these parameters:
    - `kr.cfc.low_tax_top_rate_share_max` = 70 (%).
    - `kr.cfc.control_pct_min` = 10 (%).
    - `kr.cfc.de_minimis_income_max` = 200000000 (KRW). This one is already in `kr.itca.enforcement-decree#p53`, Article 64(1).
    - The derived low-tax variable needs the top CIT rate. `kr.final.cit_bracket_4_rate` (25) is staged.

#### Documents for other gaps (fetch on instruction only)

| Document | Official source | What it would give |
|---|---|---|
| 법인세법 시행령 (CIT Enforcement Decree) | law.go.kr | Art. 18-4 requirements for a foreign subsidiary (holding period); the holding-ratio method of art. 18-2(3); the art. 60-2(1)(i) criteria behind `specified_small_corporation`; the art. 57(4)-(5) indirect credit computation |
| 소득세법 시행령 (ITA Enforcement Decree) | law.go.kr | Art. 1-2(2) domicile and residence-period rules (D-kr-2) |
| 지방세법 (Local Tax Act), arts. 103-18, 103-52 | law.go.kr | The local income tax on withheld tax. The staged surtax parameters cite CIT 98-7(1)(ii) and ITA 156-8(1)(ii), which state the 10%. Also the local income tax on corporate and global income, which is not modelled |
| Addenda (부칙) of Act 21217 (법인세법) and of the ITA amendments | in the registered PDFs, but `slice_kr_pdf` does not cut 부칙 | The start dates of the CIT 55 rates, CIT 18-4 (inferred 2023-01-01 in the staged rows) and the ITA 55 bands; slicing the addenda would make them citable |
| Korea's MLI position (`intl.mli.positions.kr.en`) | oecd.org | Whether the MLI covers kr-vn (Viet Nam lists it) and confirmation for kr-th (Thailand lists it; the date is computed) |
| 법인세법 / 소득세법 before 2026-07-01 | law.go.kr | `trace.py` fails kr cells dated before 2026-07-01 |
| in-kr treaty text | law.go.kr treaty service or incometaxindia.gov.in | `treaty.in-kr.2015.law` holds only portal navigation, so no in-kr parameters |
| Re-slice `treaty.hk-kr.2014.en#26` (no new document) | — | The original Art. 26(1) main-purpose test (Korea 2017-04-01 to 2023-12-31) is missing from the clause |

### my


Nothing here was fetched. Each item says what the document would give the library and the rule layer.

#### 1. P.U.(A) 234/2022, Income Tax (Exemption) (No. 5) Order 2022

- Official sources: the Federal Legislation portal of the Attorney General's Chambers, https://lom.agc.gov.my/ (search "P.U. (A) 234/2022"). Also the Parliament statutory papers page that holds P.U.(A)235/2022 (`my.pua235.2022.foreign-dividends`, https://www.parlimen.gov.my/ipms/eps/2023-02-15/ST.184.2022%20-%20ST%20184.2022.pdf). Order 234 is probably a neighbouring statutory paper on that page; check the number.
- The library's note on `my.inbound.individual_nonpartnership_fsi_exemption.2022_2026` says the Parliament link failed.
- What it gives: the order's own text (para 1(2) period, exemption and conditions) for the resident-individual exemption of foreign income. The rules `my.inbound.fsi_exemption.individual*` could then cite the order instead of the HASiL guideline plus ITA s127(3).

#### 2. The English text of P.U.(A)235/2022 para 4(2) and 4(3) (original 2022 wording)

- This is not a missing document. `my.pua235.2022.foreign-dividends` holds the paragraphs (see `text/my.pua235.2022.foreign-dividends.txt`), but `superseded.csv` drops `s4(2)` and `s4(3)` from the clause table, because P.U.(A)157/2024 replaced them from 2024-01-01.
- The 2022-2023 parameters I added therefore cite the Malay text `#ms.s4(2)`, which `superseded.csv` does not drop.
- What a fix would give: a dated way to cite superseded wording (or a separate clause id for the pre-2024 English text), so the 2022-2023 rows can cite the English authentic text.
- Caution: if `ms.s4(2)` is later superseded too, `my.inbound.participation_route_headline_rate_min.2022_2023` loses its clause.

#### 3. How a non-resident claims treaty relief in Malaysia (category 7, inbound direction)

- Official source: HASiL, https://www.hasil.gov.my. Candidates: the Form M (non-resident individual) explanatory notes for YA2025, which should cover Part XXII dividends; HASiL's guidance on claiming DTA relief by non-residents.
- What it gives: the `procedure` item for the Malaysian-source treaty rules (`my-*.outbound_wht.*`, `my-*.anti_abuse.ppt`). Today they point to ITA s77(1), the duty to file a return. The only category-7 document in the library, `my.hasil.e-residence`, is the certificate of residence for Malaysian residents.

#### 4. Singapore's MLI position (covered tax agreements, art. 7, art. 35)

- Official sources: the OECD MLI depositary page with Singapore's list of reservations and notifications, https://www.oecd.org/tax/treaties/ (MLI positions), or IRAS's page of Singapore DTAs modified by the MLI, https://www.iras.gov.sg.
- What it gives: whether Singapore lists the Malaysia-Singapore agreement. Malaysia lists it (`intl.mli.positions.my.2022.en#p15`, No. 56).
- Only if both list it can `my-sg.anti_abuse.ppt_applies` be written, and with it the rule `my-sg.anti_abuse.ppt`. If both list it, the date would be 2022-01-01 for taxes withheld at source: the MLI entered into force for Malaysia on 2021-06-01 and for Singapore on 2019-04-01 (`intl.oecd.mli.parties.20260915.en`).

#### 5. Commencement of the current Schedule 1 rate tables

- Official source: the Finance Act(s) that set the current Part I para 1 individual table, the para 2A small-company bands (15/17/24) and the para 2B(d) foreign-ownership test, on https://lom.agc.gov.my/.
- What it gives: `effective_from` for `my.final.progressive_bracket_*`, `my.final.cit_sme_bracket_*` and `my.final.sme_*`. They are taken from the updated text as at 1 January 2026, like the existing `individual_marginal_band_*` rows, and have no dates, so the rules apply them at every date.

#### 6. Schedule 6 para 12B before YA2025 (from round 1)

- Official source: an ITA 1967 updated text before 2025 (HASiL / AGC). Finance Act 2024 s17 shows the change, but not the old wording as a quotable whole.
- What it gives: the single-tier exemption for all recipients before 2025. With it, `my.final.domestic_exempt` and the individual exemptions could be extended to earlier dates.

### vn


Exact file URLs are not given where I could not confirm them from the library; the portals are official.

| # | Document | Where (official) | What it would give |
|---|---|---|---|
| 1 | Luật Thuế thu nhập doanh nghiệp số 67/2025/QH15, Vietnamese authentic text | Official Gazette https://congbao.chinhphu.vn/ ; national legal database https://vbpl.vn/ | Article-level clauses (arts. 2(2), 3(2)(m), 3(4), 4(7), 10, 18(3)(a), 19) in place of the single unofficial English clause `vn.law.cit2025.en#all`; art. 19(1) states both dates (effect 2025-10-01, applies from the 2025 tax period), which would settle the doc / parameter date mismatch (trace fails vn company cells dated 2025-01-01..2025-09-30) |
| 2 | Government decree detailing Law 67/2025/QH15 (Nghị định quy định chi tiết Luật Thuế TNDN; number to be confirmed) and its MoF circular | congbao.chinhphu.vn, vbpl.vn | Whether the domestic art. 3(4) credit covers the foreign investee's own CIT (underlying credit) and whether the dividend is grossed up (`vn.inbound.underlying_gross_up`); conditions of the art. 4(7) exemption; the 15 % / 17 % revenue tests (art. 10(2), (3)) |
| 3 | Government decree detailing PIT Law 109/2025/QH15 (number to be confirmed) | congbao.chinhphu.vn, vbpl.vn | Art. 2(4): how the 183 days are counted and which leases make a "regular place of residence"; art. 4(22): scope of the sole-owner exemption of art. 4(21); art. 6: withholding on dividends and the credit of foreign tax for a resident individual (today only the treaties give one) |
| 4 | Nghị định 65/2013/NĐ-CP and Thông tư 111/2013/TT-BTC (the Law itself, 04/2007/QH12, is registered since 2026-11-11 as `vn.law.pit.consolidation103.2025.vi`, consolidated text 103/VBHN-VPQH) | vbpl.vn, congbao.chinhphu.vn | The credit of foreign tax for a resident individual before 2026-07-01 (the Law has none; only the treaties give one today); whether the profit of a single-member company owned by an individual is outside taxable capital-investment income (until it is known, a sole owner's dividend before 2026-07-01 is taxed at 5%, which may overstate); the text of art. 23 before 2015-01-01 (a resident's dividend of 2009-2014 is not covered) |
| 5 | Luật Thuế thu nhập doanh nghiệp số 14/2008/QH12, latest consolidated text, with Decree 218/2013/NĐ-CP and Circular 78/2014/TT-BTC | vbpl.vn | Company rules before the 2025 tax period |
| 6 | Luật Quản lý thuế số 108/2025/QH15 and Nghị định 255/2026/NĐ-CP (related-party transactions), both cited by `vn.gov.related-party-tax-avoidance#h4` | congbao.chinhphu.vn, vbpl.vn | Confirms or overturns the staged absence record `vn.absent.company.anti_abuse` (no domestic rule denying a dividend benefit); a law clause for `vn.anti_abuse.related_party_non_arm_length_reassessment`, which now cites only a news page |
| 7 | MLI positions of India, Indonesia and the United Arab Emirates (and Korea) | OECD MLI page; the registered Viet Nam position is `https://www.oecd.org/content/dam/oecd/en/topics/policy-sub-issues/beps-mli/beps-mli-position-viet-nam.pdf`, the others presumably follow the same pattern (verify) | Whether the partner lists its agreement with Viet Nam as covered, its Article 7 choices and any Article 35(7) reservation: `in-vn`, `id-vn`, `ae-vn` `.anti_abuse.ppt_applies` and their dates (Viet Nam lists all three); for kr-vn, whether MLI art. 7(1) replaces the 2019 Protocol's art. 28(1) |
| 8 | Indonesia–Viet Nam agreement as modified by the MLI (DGT synthesised text) | DGT treaty page https://www.pajak.go.id/en/tax-treaty | The registered `treaty.id-vn.1997.mli.en` has no MLI provision and its heading names Cambodia instead of Viet Nam; the registered index `id.dgt.treaty-index` lists only 15 countries, not Viet Nam |
| 9 | India–Viet Nam amending instrument, signed 2016-09-03, in force 2017-02-21 (listed in Viet Nam's MLI position, agreement 24) | Viet Nam MOFA treaty database (`vn.mofa.treaty-index`) | Whether it changes Article 10 (the staged `in-vn.outbound_wht.dividend_rate` = 10 is from the 1994 text) or adds an anti-abuse clause |
