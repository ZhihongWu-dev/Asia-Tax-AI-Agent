## 2026-10-25 all — extension baseline
- Registered: none
- Download failures: none
- Parameters added: 0
- Absence records added: 0
- Slicing problems: not assessed; the matching build tool is absent. Existing clause.csv and text/ were preserved.
- Rate-table mismatches: none assessed
- Handoff to a person: Provide the source package matching docs/spec.zh.md, including tools/, samples/slicers-2026-10-23/, superseded.csv and any existing blocked.csv/session_log.md. All 11 visible branches of ZhihongWu-dev/Asia-Tax-AI-Agent were checked; none contains the prescribed database/ tool package. The Storage snapshot intentionally excludes these source artifacts. The original superseded.csv cannot be inferred safely from the surviving clause rows alone.
- Tool changes: Added ../audit_download.py for supplementary read-only integrity and coverage inspection; it does not implement or replace build.py acceptance. Reports are in ../_extension_audit/. Verified 190 indexed file sizes and SHA-256 hashes, all 95 document hashes and existing citation targets. Fifty quotes differ from clause text only in whitespace; whether the original validator permits its own whitespace normalization cannot be determined without that validator. No original tools were changed.
- Acceptance: NOT RUN. `python database/tools/build.py --jur cn` exited 2 because the file is missing. No PASSED result is claimed. Eight regions lack domestic category/slot coverage; 36 of the expected 55 treaty pairs have no row. No business CSV rows, originals, generated files or remote records were changed.

## 2026-10-25 tool reconstruction and vn
- Registered: vn.law.cit2025.en
- Download failures: none
- Parameters added: 0
- Absence records added: 0
- Slicing problems: vn.law.cit2025.en currently uses the documented conservative `#all` fallback. It has no source-format fixture yet.
- Rate-table mismatches: none assessed
- Handoff to a person: none
- Tool changes: Added database/tools/common.py, build.py, fetch.py, find.py, clause_diff.py and upload.py; added the superseded.csv schema and a slicer-fixture gate. `build.py` validates source hashes, identifiers, categories, dates, treaty references, citation targets, normalized-whitespace quote matching and coverage; it materializes database.sqlite and STATUS.md on a full build. It preserves existing reviewed clauses and only makes `#all` clauses for newly fetched documents. Test results: Python compilation passed; cn, hk and sg acceptance each returned PASSED; clause_diff found no changed identifiers; full build returned zero errors. A deduplication bug in the first materialization pass rewrote text/treaty.cn-kr.1994.mou1.en.txt; the original 2,505-byte object was restored from the database bucket and the duplicate index row was removed before final validation.
- Acceptance: NOT PASSED (0 errors, 225 gaps). vn has 9 category gaps and 12 slot gaps. The remaining uncovered regions and treaty pairs are listed in STATUS.md. No remote records were changed.

## 2026-10-25 my
- Registered: my.ita1967; my.hasil.foreign-income-2024
- Download failures: Initial direct download URLs returned 404; the working PDF URLs were resolved from the official HASiL Act and guidance index pages. No blocked.csv row was created because an official alternative succeeded.
- Parameters added: my.inbound.foreign_income_taxable; my.inbound.ftc_method
- Absence records added: 0
- Slicing problems: Both newly registered PDFs currently use the conservative `#all` fallback because no matching source-format fixture exists.
- Rate-table mismatches: none assessed
- Handoff to a person: none
- Tool changes: none
- Acceptance: NOT PASSED (0 errors, 21 gaps). The two new parameter rows validate against their cited official text (line-wrap-only comparison warning). Remaining gaps are 8 categories, 10 company/individual slots and 3 treaty pairs. No remote records were changed.

## 2026-10-25 th
- Registered: th.rd.cit
- Download failures: none
- Parameters added: th.final.cit_rate; th.final.cit_return_days; th.outbound_wht.dividend_wht_rate; th.outbound_wht.foreign_company_return_days
- Absence records added: 0
- Slicing problems: th.rd.cit currently uses the conservative `#all` fallback because no matching source-format fixture exists.
- Rate-table mismatches: none assessed
- Handoff to a person: none
- Tool changes: none
- Acceptance: NOT PASSED (0 errors, 12 gaps). The first run caught one non-verbatim full-stop error in th.final.cit_rate; it was corrected and the rerun had zero errors. Remaining gaps are 1 category, 10 company/individual slots and 1 treaty pair. No remote records were changed.

## 2026-10-25 id
- Registered: id.dgt.ease-taxation; id.tax-law-compilation-2022
- Download failures: none
- Parameters added: id.final.cit_rate; id.inbound.foreign_dividend_exempt_if_invested
- Absence records added: 0
- Slicing problems: Both sources currently use the conservative `#all` fallback because no matching source-format fixture exists.
- Rate-table mismatches: The DGT overview page describes a 20% rate under Law Number 2 of 2020, while the later official tax-law compilation states 22% from fiscal year 2022. The parameter uses the later statutory compilation, with a note that a later official amendment would need separate verification.
- Handoff to a person: none
- Tool changes: Added pajak.go.id and www.pajak.go.id to the official-host allowlist after confirming they are the Directorate General of Taxes domain.
- Acceptance: NOT PASSED (0 errors, 22 gaps). Remaining gaps are 6 categories, 9 company/individual slots and 7 treaty pairs. The two added rows have only extraction line-wrap warnings, not quote-content errors. No remote records were changed.

## 2026-10-25 th — follow-up
- Registered: th.rd.pit; th.rd.dta-index
- Download failures: none
- Parameters added: th.residence.individual_days_threshold; th.inbound.foreign_income_taxable_on_remittance; th.final.individual_dividend_tax_credit_fraction; th.final.individual_return_deadline
- Absence records added: 0
- Slicing problems: Both newly registered pages currently use the conservative `#all` fallback because no matching source-format fixture exists.
- Rate-table mismatches: none assessed
- Handoff to a person: none
- Tool changes: none
- Acceptance: NOT PASSED (0 errors, 8 gaps). Category coverage is complete. Remaining gaps are 7 company/individual slots and the th-vn treaty pair. No remote records were changed.

## 2026-10-25 th-vn treaty
- Registered: treaty.th-vn.1992.en; treaty row th-vn
- Download failures: none
- Parameters added: 0
- Absence records added: 0
- Slicing problems: The official treaty PDF is an image-only scan and was collected through the conservative `#all` fallback after local English OCR. It must be re-sliced against a fixture before article-level treaty parameters are added.
- Rate-table mismatches: none assessed
- Handoff to a person: An official MLI text or synthesised text is still required before relying on provisions that may have been modified from 1 July 2022.
- Tool changes: build.py now uses a reproducible local OCR fallback only when a PDF has no directly extractable text. It renders at 200 dpi with pdftoppm and OCRs pages with the installed English Tesseract data, in four ordered workers. OCR text is then checked by the ordinary build process; the source PDF is not modified.
- Acceptance: NOT PASSED (0 errors, 7 gaps). The th-vn treaty-pair gap is resolved. Remaining gaps are seven domestic company/individual slots. No remote records were changed.

## 2026-10-25 my — follow-up
- Registered: none; used the already registered official Income Tax Act 1967 text
- Download failures: none
- Parameters added: my.final.cit_rate; my.residence.company_management_control; my.residence.individual_days_threshold
- Absence records added: 0
- Slicing problems: none beyond the documented conservative `#all` fallback for my.ita1967.
- Rate-table mismatches: none assessed
- Handoff to a person: none
- Tool changes: none
- Acceptance: NOT PASSED (0 errors, 18 gaps). Remaining gaps are 8 categories, 7 company/individual slots and 3 treaty pairs. The three added rows have only extraction line-wrap warnings, not quote-content errors. No remote records were changed.

## 2026-10-25 my — treaty and rates pages
- Registered: my.hasil.dta-index; my.hasil.wht-rates; my.hasil.wht
- Download failures: none
- Parameters added: 0
- Absence records added: 0
- Slicing problems: All three pages currently use the conservative `#all` fallback because no matching source-format fixture exists.
- Rate-table mismatches: none assessed; the rate table is retained as a cross-check source, not used as a parameter citation.
- Handoff to a person: none
- Tool changes: none
- Acceptance: NOT PASSED (0 errors, 15 gaps). All webpage categories are now covered. Remaining gaps are 5 legal-content categories, 7 company/individual slots and 3 treaty pairs. No remote records were changed.

## 2026-10-25 id — Article 23/26 and individual pages
- Registered: id.dgt.article23; id.dgt.individual-calculation; id.dgt.article26
- Download failures: none
- Parameters added: id.outbound_wht.default_nonresident_rate; id.outbound_wht.treaty_rate_available; id.outbound_wht.payment_deadline
- Absence records added: 0
- Slicing problems: All three sources currently use the conservative `#all` fallback because no matching source-format fixture exists.
- Rate-table mismatches: The individual-calculation overview is not used for a rate parameter because its displayed brackets require separate recency confirmation against the consolidated legislation.
- Handoff to a person: none
- Tool changes: none
- Acceptance: NOT PASSED (0 errors, 18 gaps). Remaining gaps are 4 categories, 7 company/individual slots and 7 treaty pairs. The new Article 26 rows validate against their cited official text. No remote records were changed.

## 2026-10-25 my — treaty pairs
- Registered: treaty.my-sg.2004.en; treaty.my-th.1982.en; treaty.my-vn.1995.en; treaty rows my-sg, my-th and my-vn
- Download failures: none
- Parameters added: 0
- Absence records added: 0
- Slicing problems: The three treaty PDFs currently use the conservative `#all` fallback. Article-level treaty parameters must wait for fixture-validated slicing.
- Rate-table mismatches: none assessed
- Handoff to a person: The Malaysia–Thailand 1995 protocol and any relevant MLI texts need collection before provisions potentially altered after the base agreements are used as parameters.
- Tool changes: none
- Acceptance: NOT PASSED (0 errors, 12 gaps). All Malaysia treaty-pair gaps are resolved. Remaining gaps are 5 legal-content categories and 7 company/individual slots. No remote records were changed.

## 2026-10-26 remote partial upload
- Registered: none
- Download failures: none
- Parameters added: 0
- Absence records added: 0
- Slicing problems: unchanged
- Rate-table mismatches: unchanged
- Handoff to a person: none
- Tool changes: Replaced the reconstructed upload-plan placeholder with a Supabase uploader that uses the configured connection, stages same-structure tables in a transaction, synchronises the `database` bucket, supports resuming an interrupted object upload, and provides read-only preflight/status/verification modes.
- Acceptance: Local build remains NOT PASSED (0 errors, 179 coverage gaps), but an explicitly authorised partial upload was completed. Remote verification passed: all 230 expected Storage objects exist and the row counts of jurisdiction (11), doc (113), files (226), clause (5,930), param (142), decision (14) and treaty (23) match local data.

## 2026-10-26 id — resident, CFC and anti-abuse follow-up
- Registered: none; used the already registered official tax-law compilation.
- Download failures: none
- Parameters added: id.residence.individual_days_threshold; id.residence.company_domicile; id.final.individual_top_rate; id.cfc.overseas_dividend_receipt_time; id.anti_abuse.substance_over_form
- Absence records added: 0
- Slicing problems: The CFC source sentence crosses a PDF page boundary; the parameter retains only its contiguous, verifiable text and notes the limitation. The document otherwise continues to use the conservative `#all` fallback.
- Rate-table mismatches: none assessed; the individual top-rate row is tied directly to the statutory table in the same official compilation.
- Handoff to a person: Official current treaty texts or a treaty index are still needed to resolve Indonesia's seven remaining treaty-pair gaps. Categories 5, 6 and 8 require a separately collected official source before absence or substantive coverage can be asserted.
- Tool changes: none
- Acceptance: NOT PASSED overall (0 errors, 172 coverage gaps). Indonesia-specific acceptance completed with 0 errors and 11 remaining gaps, down from 18: 4 source-category gaps and 7 treaty-pair gaps. Its company/individual parameter slots are now covered. Full local build regenerated `database.sqlite` and `STATUS.md`; it has 147 parameter rows. No remote records were changed in this round.

## 2026-10-26 my — rate, withholding and anti-abuse follow-up
- Registered: none; used the already registered official Income Tax Act 1967 text.
- Download failures: none
- Parameters added: my.final.individual_top_rate; my.outbound_wht.interest_royalty_withholding; my.anti_abuse.gaar_adjustment_power
- Absence records added: 0
- Slicing problems: none beyond the documented conservative `#all` fallback for my.ita1967.
- Rate-table mismatches: none assessed. The new 30% row is the general Schedule 1 Part I top marginal rate and retains its statutory-exceptions note.
- Handoff to a person: A properly scoped, current official CFC source is required before either remaining Malaysian CFC slot can be completed or marked absent. The term `controlled company` in the current Act was not treated as evidence of a CFC regime.
- Tool changes: none
- Acceptance: NOT PASSED (0 errors, 7 gaps). Malaysia-specific coverage now has 5 source-category gaps and 2 CFC-slot gaps; it had 12 gaps before this round. No remote records were changed in this round.

## 2026-10-26 th — individual withholding follow-up
- Registered: none; used the already registered official Personal Income Tax overview.
- Download failures: none
- Parameters added: th.outbound_wht.payer_withholding_required
- Absence records added: 0
- Slicing problems: none beyond the documented conservative `#all` fallback for th.rd.pit.
- Rate-table mismatches: none assessed. This row records the withholding obligation rather than a rate, because the source makes the rate depend on the stated income category.
- Handoff to a person: Current official Thai legal text or an official detailed guidance source is required for the remaining company residence/inbound and company/individual anti-abuse/CFC coverage; these claims are not inferred from high-level overview pages.
- Tool changes: none
- Acceptance: NOT PASSED (0 errors, 6 gaps). Thailand-specific coverage now has six domestic slot gaps and no category or treaty-pair gaps. Supabase synchronization is pending the full local build.

## 2026-10-26 vn — corporate scope, rate and foreign-tax-credit follow-up
- Registered: none; used the already registered official 2025 Corporate Income Tax Law.
- Download failures: none
- Parameters added: vn.final.cit_rate; vn.inbound.foreign_income_taxable; vn.inbound.foreign_tax_credit_cap; vn.residence.company_worldwide_tax_scope
- Absence records added: 0
- Slicing problems: none beyond the documented conservative `#all` fallback for vn.law.cit2025.en.
- Rate-table mismatches: none assessed. The standard 20% rate is recorded with the statutory exceptions and its 2025 corporate-tax-period effective date.
- Handoff to a person: Official current sources for Vietnamese individual income tax, non-resident withholding, CFC and anti-abuse rules are needed before the remaining slots can be filled. The corporate statute alone is not treated as evidence for those subjects or categories.
- Tool changes: none
- Acceptance: NOT PASSED (0 errors, 18 gaps). Vietnam-specific coverage has 9 source-category gaps and 9 domestic slot gaps, down from 21 gaps. Supabase synchronization is pending the full local build.

## 2026-10-26 in — official rates and resident-status sources
- Registered: in.itd.individual-rates-2026; in.itd.foreign-assets-2026; in.itd.nonresident-faq
- Download failures: none
- Parameters added: in.final.individual_top_rate_default_regime; in.residence.individual_days_threshold; in.residence.company_poem
- Absence records added: 0
- Slicing problems: All three sources use the documented conservative `#all` fallback. The foreign-assets brochure is an official PDF and was extracted into a local text copy by the ordinary build.
- Rate-table mismatches: The individual top rate is recorded only for the official page's default section 115BAC regime, with a note that the page also presents an old regime.
- Handoff to a person: Current official Indian primary legislation or targeted official guidance is still needed for company final/inbound/outbound rules, individual foreign-income and outbound rules, anti-abuse and CFC. Separate official treaty pages are required for the six unresolved India treaty pairs.
- Tool changes: Added the verified official `www.incometax.gov.in` host to the collection allowlist.
- Acceptance: NOT PASSED (0 errors, 24 gaps). India coverage now has 9 source-category gaps, 9 domestic slot gaps and 6 treaty-pair gaps, down from 36 gaps. Supabase synchronization is pending the full local build.

## 2026-10-26 remote synchronization — id, my, th, vn and in rounds
- Scope: The `database` Storage bucket and the PostgreSQL schema named `database` only.
- Result: The completed Indonesia/Malaysia, Thailand, Vietnam and India rounds were uploaded after their full local builds using the transactional staging-schema replacement. Existing objects were skipped in resumable runs; India's six new source/text objects were uploaded.
- Verification: Final remote verification passed against the current local snapshot: 236 objects; jurisdiction 11; doc 116; files 232; clause 5,933; param 158; decision 14; treaty 23. The current build has 0 data errors, 157 coverage gaps and 67 whitespace-only extraction warnings.
- Note: Coverage remains partial by design of the current source corpus. It was explicitly published as a partial-coverage snapshot; the verification proves equality with local data, not completeness of every required jurisdiction/category/rule.

## 2026-10-26 kr — current statutory-source registration
- Registered: kr.corporate-tax-act-2026; kr.income-tax-act-2026
- Download failures: kr.nts.individual-rates timed out during TLS read and was not registered or retained.
- Parameters added: 0
- Absence records added: 0
- Slicing problems: The National Law Information Center's static response contains the current-law metadata and client-side body-loading scaffolding, but not the statute body. The collector preserved the original response and used the documented `#all` fallback; no parameter was inferred from metadata or a search snippet.
- Rate-table mismatches: none assessed
- Handoff to a person: A reproducible official body-download endpoint or official downloadable consolidated text is required before Korean statutory rules can be parameterized. The National Tax Service rates page should be retried separately after the transient connection timeout.
- Tool changes: Added verified `www.nts.go.kr` to the collection allowlist.
- Acceptance: NOT PASSED (0 errors, 27 gaps). Korea source-category coverage improved from 12 to 6 gaps; domestic slots and four treaty-pair gaps remain. Supabase synchronization is pending this round's source publication.

## 2026-10-26 jp — current rates and non-resident withholding
- Registered: jp.nta.corporate-rate-2026; jp.nta.income-rate-2026; jp.nta.nonresident-withholding
- Download failures: none
- Parameters added: jp.final.cit_rate; jp.final.individual_top_rate; jp.outbound_wht.nonresident_payment_withholding
- Absence records added: 0
- Slicing problems: All three official NTA pages use the documented conservative `#all` fallback. In the corporate-rate table, the ordinary-corporation category and 23.20% cell are separated by table structure, so the quoted string is the directly extractable rate and the row's note preserves the category limitation.
- Rate-table mismatches: none assessed. The 23.2% rate is national corporate tax only and the 45% rate is the top national individual-income bracket; both have source notes for exclusions/surtaxes.
- Handoff to a person: Official Japanese sources are still needed for domestic/foreign-income scope, residence, CFC and anti-abuse rules; a current treaty index and the five missing pair texts are needed for Japan's treaty coverage.
- Tool changes: Added verified `www.nta.go.jp` to the collection allowlist.
- Acceptance: NOT PASSED (0 errors, 20 gaps). Japan coverage now has 7 source-category gaps, 8 domestic slot gaps and 5 treaty-pair gaps. Supabase synchronization is pending the full local build.

## 2026-10-26 ae — corporate-tax sources and business-person rules
- Registered: ae.fta.natural-persons-2023; ae.fta.withholding-faq; ae.fta.corporate-tax-faq
- Download failures: The UAE Legislation Corporate Tax Law download endpoint returned HTTP 403 on both ordinary and curl-engine collection attempts. No local source file was written from that endpoint.
- Parameters added: ae.final.individual_business_rate; ae.inbound.individual_uae_business_foreign_income; ae.residence.individual_uae_business; ae.outbound_wht.nonresident_state_source_rate; ae.residence.company_effective_management; ae.anti_abuse.company_transfer_pricing
- Absence records added: 0
- Slicing problems: The FTA sources use the documented conservative `#all` fallback. The individual-inbound quote intentionally ends before its next-page condition; its note preserves that the income must relate to the UAE business.
- Rate-table mismatches: none assessed. The individual 9% rule is subject to the AED 1 million turnover threshold and begins only above AED 375,000 taxable income; the 0% withholding rate is limited to the stated non-resident State Sourced Income situation.
- Handoff to a person: An accessible current UAE Legislation law text or FTA primary guidance is still needed for company standard rate, company inbound scope, CFC, and individual anti-abuse. A treaty index and all ten UAE treaty pairs remain to be collected.
- Tool changes: Added verified `tax.gov.ae` and `www.tax.gov.ae` to the collection allowlist.
- Acceptance: NOT PASSED (0 errors, 18 gaps). UAE coverage now has 3 source-category gaps, 5 domestic slot gaps and 10 treaty-pair gaps, down from 34 gaps.
- Supabase sync and remote acceptance: passed on 2026-10-26. The `database` storage bucket had 252 expected objects, and all seven `database` schema table row counts matched the local snapshot (jurisdiction 11; doc 124; files 248; clause 5,941; param 167; decision 14; treaty 23).

## 2026-10-26 ae — general corporate-tax and foreign-income coverage
- Registered: ae.fta.general-corporate-tax; ae.fta.foreign-source-income
- Download failures: none.
- Parameters added: ae.final.company_standard_rate; ae.inbound.company_worldwide_income
- Absence records added: 0
- Slicing problems: Both official PDFs were preserved as originals and materialised as conservative `#all` citations. The first draft used literal backslash-n sequences in quotes; jurisdiction acceptance rejected them before publication. The final quotes are continuous source strings.
- Rate-table mismatches: none assessed. The 9% company rate applies only to the taxable-income portion exceeding AED 375,000; the note preserves the 0% first portion and separate qualifying-Free-Zone rules.
- Handoff to a person: Official current evidence is still needed for UAE company and individual CFC treatment, individual anti-abuse, treaty index and the ten missing UAE treaty pairs. The statutory law download endpoint remains inaccessible from the collector.
- Acceptance: NOT PASSED (0 errors, 16 UAE gaps). This round removed the company `final` and `inbound` slot gaps.
- Supabase sync and remote acceptance: passed on 2026-10-26. The `database` storage bucket had 256 expected objects, and all seven `database` schema table row counts matched the local snapshot (jurisdiction 11; doc 126; files 252; clause 5,943; param 169; decision 14; treaty 23).

## 2026-10-26 ae — general anti-abuse rule
- Registered: none; the evidence was already in ae.fta.general-corporate-tax.
- Parameters added: ae.anti_abuse.general_gaar
- Absence records added: 0
- Evidence and scope: The guide calls this a general anti-abuse rule and states that the FTA can counteract or adjust Corporate Tax advantages obtained from abusive transactions or arrangements. The parameter uses subject `all`, so it supplies the individual anti-abuse slot without displacing the more specific company transfer-pricing parameter.
- Acceptance: NOT PASSED (0 errors, 15 UAE gaps). The individual anti-abuse slot was removed; the two CFC slots, three source categories and ten treaty pairs remain.
- Supabase sync and remote acceptance: passed on 2026-10-26. The `database` storage bucket had 256 expected objects, and all seven `database` schema table row counts matched the local snapshot (jurisdiction 11; doc 126; files 252; clause 5,943; param 170; decision 14; treaty 23).

## 2026-10-26 ae — official DTA index
- Registered: ae.mof.dta-index
- Download failures: none.
- Parameters added: 0
- Absence records added: 0
- Scope and limitation: The official Ministry of Finance index records partner jurisdictions and status dates, including all ten missing database partners. It is catalogued as `page_treaties`, but is not treated as a substitute for the underlying bilateral treaty text; no treaty row or rate was inferred from an index listing.
- Tool changes: Added the verified official `mof.gov.ae` host to the collection allowlist.
- Acceptance: NOT PASSED (0 errors, 14 UAE gaps). The `page_treaties` category gap was removed; the two CFC slot gaps, category 8, the deadlines page and ten underlying treaty-pair records remain.
- Supabase sync and remote acceptance: passed on 2026-10-26. The `database` storage bucket had 258 expected objects, and all seven `database` schema table row counts matched the local snapshot (jurisdiction 11; doc 127; files 254; clause 5,944; param 170; decision 14; treaty 23).

## 2026-10-26 ae — Corporate Tax registration page
- Registered: ae.fta.corporate-tax-registration
- Download failures: none.
- Parameters added: 0
- Absence records added: 0
- Scope and limitation: This official service page is catalogued as `page_deadlines` because it identifies the registration obligation and its timing reference. It is not used to invent a filing deadline or numeric parameter that the captured page does not state.
- Acceptance: NOT PASSED (0 errors, 13 UAE gaps). The `page_deadlines` category gap was removed; category 8, two CFC slots and ten treaty-pair records remain.
- Supabase sync and remote acceptance: passed on 2026-10-26. The `database` storage bucket had 260 expected objects, and all seven `database` schema table row counts matched the local snapshot (jurisdiction 11; doc 128; files 256; clause 5,945; param 170; decision 14; treaty 23).

## 2026-10-26 ae — tax residence and certificate procedure
- Registered: ae.fta.tax-resident-certificate-2024
- Download failures: none.
- Parameters added: ae.residence.individual_days_threshold_domestic; ae.residence.individual_conditional_days_threshold
- Absence records added: 0
- Scope and limitation: The first parameter records the 183-day domestic-law test. The second records the 90-day threshold only as a conditional alternative; its note preserves the required nationality/residence-permit and permanent-home/employment/business conditions.
- Slicing problems: The official PDF is preserved and cited using the conservative `#all` clause.
- Acceptance: NOT PASSED (0 errors, 12 UAE gaps). Category 8 was removed; all required UAE source categories are now covered. Two CFC slots and ten treaty-pair records remain.
- Supabase sync and remote acceptance: passed on 2026-10-26. The `database` storage bucket had 262 expected objects, and all seven `database` schema table row counts matched the local snapshot (jurisdiction 11; doc 129; files 258; clause 5,946; param 172; decision 14; treaty 23).

## 2026-10-26 ae-cn — DTA and MLI synthesised text
- Registered: treaty.ae-cn.1993.en; treaty.ae-cn.1993.mli.en
- Download failures: none.
- Treaty row added: ae-cn, in force 1994-07-22, with the official MLI synthesised text as `mli_doc_id`.
- Parameters added: ae-cn.outbound_wht.dividend_rate; ae-cn.outbound_wht.interest_rate; ae-cn.outbound_wht.royalty_rate; ae-cn.anti_abuse.ppt_applies
- Source and scope: The base treaty and synthesised text were both collected from the State Taxation Administration of China. The in-force date is independently recorded in the UAE Ministry of Finance index. Notes preserve the special government-recipient exemptions and the different MLI effect dates by tax type.
- Acceptance: NOT PASSED (0 errors, 11 UAE gaps). The ae-cn treaty-pair gap was removed; two UAE CFC slot gaps and nine UAE treaty-pair records remain.
- Supabase sync and remote acceptance: passed on 2026-10-26. The `database` storage bucket had 266 expected objects, and all seven `database` schema table row counts matched the local snapshot (jurisdiction 11; doc 131; files 262; clause 5,948; param 176; decision 14; treaty 24).

## 2026-10-26 ae-hk — DTA and MLI synthesised text
- Registered: treaty.ae-hk.2014.en; treaty.ae-hk.2014.mli.en
- Download failures: none.
- Treaty row added: ae-hk, in force 2015-12-10, with the official MLI synthesised text as `mli_doc_id`.
- Parameters added: ae-hk.outbound_wht.dividend_rate_government; ae-hk.outbound_wht.dividend_rate_other; ae-hk.outbound_wht.interest_rate; ae-hk.outbound_wht.royalty_rate; ae-hk.anti_abuse.ppt_applies
- Source and scope: The Hong Kong Inland Revenue Department supplied both texts and confirms the in-force date. Notes preserve the government-recipient dividend exception and different MLI effect dates for Hong Kong and the UAE rather than reducing them to one misleading date.
- Acceptance: NOT PASSED (0 errors, 10 UAE gaps). The ae-hk treaty-pair gap was removed; two UAE CFC slot gaps and eight UAE treaty-pair records remain.
- Supabase sync and remote acceptance: passed on 2026-10-26. The `database` storage bucket had 270 expected objects, and all seven `database` schema table row counts matched the local snapshot (jurisdiction 11; doc 133; files 266; clause 5,950; param 181; decision 14; treaty 25).

## 2026-10-26 ae-id — replacement DTA
- Registered: treaty.ae-id.2019.en
- Download failures: none. The large, scanned multilingual attachment required a longer local extraction pass but materialised successfully.
- Treaty row added: ae-id, in force 2021-08-19, with no separate MLI text required because the 2019 replacement treaty contains the relevant anti-abuse rule.
- Parameters added: ae-id.outbound_wht.dividend_rate; ae-id.outbound_wht.dividend_rate_government; ae-id.outbound_wht.interest_rate; ae-id.outbound_wht.royalty_rate; ae-id.anti_abuse.ppt_applies
- Source and scope: The Indonesian Directorate General of Taxes attachment to Presidential Regulation 34 of 2021 provides the replacement treaty, including the English version. The UAE Ministry of Finance DTA index provides the in-force date. No rate effective-from date was invented where the official attachment did not provide an unambiguous single date.
- Tool changes: Added the verified official `stats.pajak.go.id` host to the collection allowlist.
- Acceptance: NOT PASSED (0 errors, 9 UAE gaps). The ae-id treaty-pair gap was removed; two UAE CFC slot gaps and seven UAE treaty-pair records remain.
- Supabase sync and remote acceptance: passed on 2026-10-26. The `database` storage bucket had 272 expected objects, and all seven `database` schema table row counts matched the local snapshot (jurisdiction 11; doc 134; files 268; clause 5,951; param 186; decision 14; treaty 26).

## 2026-10-26 ae-jp — DTA MLI application and rate summary
- Registered: treaty.ae-jp.2013.mli.en; treaty.ae-jp.2013.summary.en
- Download failures: The Ministry of Foreign Affairs English base-convention PDF endpoint returned HTTP 403 and was not registered.
- Treaty row added: ae-jp, in force 2014-12-24, with the Ministry of Finance MLI application page as the available treaty and MLI source.
- Parameters added: ae-jp.outbound_wht.dividend_rate_parent; ae-jp.outbound_wht.dividend_rate_other; ae-jp.outbound_wht.interest_rate_government; ae-jp.outbound_wht.interest_rate; ae-jp.outbound_wht.royalty_rate; ae-jp.anti_abuse.ppt_applies
- Source and scope: The Ministry of Finance MLI page directly states that Article 7(1) applies and provides the effect dates. The investment-income limits are from the Ministry's official key-points table, retained as a supporting explanatory document. It is not represented as a substitute for the unavailable base treaty PDF.
- Tool changes: Added verified official `www.mofa.go.jp` and `www.mof.go.jp` hosts to the collection allowlist.
- Acceptance: NOT PASSED (0 errors, 8 UAE gaps). The ae-jp treaty-pair gap was removed; two UAE CFC slot gaps and six UAE treaty-pair records remain.
- Supabase sync and remote acceptance: passed on 2026-10-26. The upload session ended without a final status line, but a subsequent read-only remote verification passed: storage had 276 expected objects and all seven schema table counts matched the local snapshot (jurisdiction 11; doc 136; files 272; clause 5,953; param 192; decision 14; treaty 27).

## 2026-10-26 ae-kr — replacement DTA
- Registered: treaty.ae-kr.2019.en
- Download failures: none. The Korean National Law Information Center initially served its Korean default view; the registered source is the same official endpoint with its published English-view parameter, and its text states that the English version prevails if interpretations diverge.
- Treaty row added: ae-kr, in force 2020-02-29, with no separate MLI text. The 2019 convention supersedes the 2003 convention when its provisions take effect.
- Parameters added: ae-kr.outbound_wht.dividend_rate_parent; ae-kr.outbound_wht.dividend_rate_other; ae-kr.outbound_wht.interest_rate; ae-kr.outbound_wht.royalty_rate; ae-kr.anti_abuse.ppt_applies
- Source and scope: Article 10 sets 5% on qualifying direct 10% company holdings and 10% otherwise; Articles 11 and 12 set 10% caps. Article 26(5) is a treaty-level principal-purposes test with its stated object-and-purpose exception. Article 28 makes the withholding provisions effective from 2021-01-01; this date is retained on the rate parameters.
- Tool changes: `build.py` now re-materialises only a document explicitly replaced by `fetch.py --force`, updating its raw/text hashes and conservative `#all` clause. This corrects stale generated evidence after an intentional source refresh while preserving all other reviewed documents unchanged.
- Acceptance: NOT PASSED (0 errors, 7 UAE gaps). The ae-kr treaty-pair gap was removed; two UAE CFC slot gaps and five UAE treaty-pair records remain.
- Supabase sync and remote acceptance: passed on 2026-10-26. The first read-only verification hit a transient TLS error after the successful upload; the retry passed with 278 storage objects and all seven schema table counts matching the local snapshot (jurisdiction 11; doc 137; files 274; clause 5,954; param 197; decision 14; treaty 28).

## 2026-10-26 ae-sg — consolidated DTA, protocol and MLI text
- Registered: treaty.ae-sg.1995.mli.en
- Download failures: none.
- Treaty row added: ae-sg, in force 1996-08-30, using IRAS's official consolidated PDF as both the current treaty and MLI source. It contains the 1995 agreement, the 2014 Second Protocol, and Annex A MLI modifications.
- Parameters added: ae-sg.outbound_wht.dividend_rate; ae-sg.outbound_wht.interest_rate; ae-sg.outbound_wht.royalty_rate; ae-sg.anti_abuse.ppt_applies
- Source and scope: The 2014 Second Protocol replaces Article 10 and Article 11, giving exclusive residence-state taxation (0% source cap) for dividends and interest from 2017-01-01. Article 12 retains its 5% royalty cap, subject to the Protocol's changed definition. Annex A Article 27A supplies the PPT; its withholding-tax effect date in Singapore is 2020-01-01.
- Acceptance: NOT PASSED (0 errors, 6 UAE gaps). The ae-sg treaty-pair gap was removed; two UAE CFC slot gaps and four UAE treaty-pair records remain.
- Supabase sync and remote acceptance: passed on 2026-10-26. The `database` storage bucket had 280 expected objects, and all seven schema table counts matched the local snapshot (jurisdiction 11; doc 138; files 276; clause 5,955; param 201; decision 14; treaty 29).

## 2026-10-26 ae-th — DTA base text
- Registered: treaty.ae-th.2000.en
- Download failures: none.
- Treaty row added: ae-th, in force 2000-12-28, with no MLI document. Thailand Revenue Department records withholding application from 2001-02-01 and other-tax application from 2001-01-01.
- Parameters added: ae-th.outbound_wht.dividend_rate; ae-th.outbound_wht.interest_rate_financial_institution; ae-th.outbound_wht.interest_rate_other; ae-th.outbound_wht.royalty_rate
- Source and scope: Article 10(2) caps dividends at 10%; Article 11(2) caps financial-institution interest at 10% and other interest at 15%; Article 12(2) caps royalties at 15%. The base treaty has no directly citable PPT or general anti-abuse rule. Although Thailand's DTA index identifies MLI status, an official UAE–Thailand synthesised text has not yet been collected, so no modified provision is inferred.
- Acceptance: NOT PASSED (0 errors, 5 UAE gaps). The ae-th treaty-pair gap was removed; two UAE CFC slot gaps and three UAE treaty-pair records remain.
- Supabase sync and remote acceptance: passed on 2026-10-26. The `database` storage bucket had 282 expected objects, and all seven schema table counts matched the local snapshot (jurisdiction 11; doc 139; files 278; clause 5,956; param 205; decision 14; treaty 30).

## 2026-10-26 ae-vn — DTA base text
- Registered: treaty.ae-vn.2009.en
- Download failures: none.
- Treaty row added: ae-vn, in force 2010-04-12. The UAE Ministry of Finance provides the English text; Vietnam's Ministry of Foreign Affairs treaty database independently confirms signature on 16 February 2009 and entry into force on 12 April 2010.
- Parameters added: ae-vn.outbound_wht.dividend_rate_parent; ae-vn.outbound_wht.dividend_rate_other; ae-vn.outbound_wht.dividend_rate_government; ae-vn.outbound_wht.interest_rate; ae-vn.outbound_wht.royalty_rate
- Source and scope: Article 10 provides 5% for the stated direct company holding (more than 50% capital or at least USD 10 million), 15% otherwise, and residence-state-only taxation for qualifying government owners. Articles 11 and 12 provide 10% caps. No official UAE–Vietnam MLI synthesised text was collected, so no MLI anti-abuse rule is inferred. Vietnam's Ministry of Finance says the parties are negotiating/amending the DTA as of 2024; the registered text is the official published in-force instrument pending replacement.
- Upload repair: The first schema staging attempt timed out on its one large `COPY clause` command (PostgreSQL SQLSTATE 57014); remote tables remained at the preceding accepted counts while Storage already contained the new objects. `upload.py` now streams all CSV tables in 250-row COPY batches within the same staging transaction, preserving all-or-nothing schema replacement. The retry succeeded.
- Acceptance: NOT PASSED (0 errors, 4 UAE gaps). The ae-vn treaty-pair gap was removed; two UAE CFC slot gaps and ae-in/ae-my treaty-pair gaps remain.
- Supabase sync and remote acceptance: passed on 2026-10-26. The `database` storage bucket had 284 expected objects, and all seven schema table counts matched the local snapshot (jurisdiction 11; doc 140; files 280; clause 5,957; param 210; decision 14; treaty 31).

## 2026-10-27 — UAE–Malaysia treaty and UAE–India protocol source expansion

- Official source discovery: used the UAE Ministry of Finance public International Treaties dashboard. Its public AJAX listing returned the Malaysia DTA PDF and the India base agreement plus first and second protocol PDFs. The dashboard links are registered directly as official `mof.gov.ae` originals.
- Documents added: `treaty.ae-my.1995.en`; `treaty.ae-in.1992.p1.en`; `treaty.ae-in.1992.p2.en`. All three raw PDFs, OCR/extracted text and whole-document clauses were materialised by a full build.
- Metadata correction: `treaty.ae-in.1992.mli.en` is a scanned base-agreement PDF, not a verified MLI synthesised text. Its treaty row now has a blank MLI pointer; the separately collected protocols are not represented as an MLI result.
- Treaty row and parameters added: `ae-my`, in force 1996-09-18; Article 10 dividend cap 10%, Article 11 general interest cap 5% and government exemption, Article 13 royalty cap 10%. Article 28 makes the withholding rules effective from 1997-01-01 given the official Malaysian index's 1996-09-18 entry-into-force date.
- Evidence boundary: the India first protocol supplies a limitation-of-benefits clause; the second protocol supplies exchange-of-information wording. Neither changes Articles 10–12. No UAE–India rate parameter is claimed until the base-treaty rate text can be OCR-verified to citation quality.

## 2026-10-27 — UAE CFC absence resolved

- Document added: `ae.mof.top-up-tax`, the official Ministry of Finance Top-up Tax page, categorised as CFC material. Its source HTML, generated text and whole-document clause were materialised and hash-verified.
- Decision added: `ae.absent.cfc`, covering both company and individual CFC slots. The Ministry expressly states: “the UAE corporate tax regime does not include a controlled foreign company regime.” This is recorded as an absence decision, not as a fabricated CFC parameter or rate.

## 2026-10-27 — Indonesia–India MLI treaty expansion

- Document added: `treaty.id-in.2012.mli.en`, the official Indonesian Directorate General of Taxes English MLI synthesised text. The initial Python TLS download failed, so `fetch.py --engine curl` was repaired to use its documented curl engine with retry; the original was then downloaded, hash-registered and materialised.
- Treaty row added: `id-in`, entered into force 2016-02-05; the DGT index states MLI modification from 2021-01-01.
- Parameters added: Article 10 dividend cap 10%; Article 11 interest cap 10% and government/listed institution exemption; Article 12 royalty/technical-services cap 10%; MLI Article 7(1) principal-purpose test.

## 2026-10-27 — Indonesia–Japan MLI treaty expansion

- Document and treaty row added: `treaty.id-jp.1982.mli.en`, using the official Indonesian Directorate General of Taxes English MLI synthesised text; entry into force is 1982-12-31 and MLI application begins 2021-01-01 according to the DGT treaty index.
- Parameters added: Article 10 10% qualifying-company dividend cap (25% voting shares held for 12 months) and 15% other dividend cap; Article 11 interest cap 10%; Article 12 royalty cap 10%; MLI Article 7(1) principal-purpose test.

## 2026-10-27 — Indonesia–Republic of Korea MLI treaty registration

- Document and treaty row added: `treaty.id-kr.1988.mli.en`, sourced from the official Indonesian Directorate General of Taxes English MLI synthesised text. The DGT index records entry into force on 1989-03-03, effective from 1990-01-01, and MLI application from 2021-01-01.
- Parameters deferred: the complete official source is now stored and queryable; article-level rate and PPT parameters will be added only after a separate citation extraction pass.

### Follow-up parameter extraction

- Parameters added after citation review: Article 10 10% qualifying-company dividend cap (direct 25% capital) and 15% other dividend cap; Article 11 general interest cap 10% and government/public-institution exemption; Article 12 royalty cap 15%; MLI Article 7(1) principal-purpose test.

## 2026-10-27 — Indonesia–Malaysia MLI treaty expansion

- Document and treaty row added: `treaty.id-my.1991.mli.en`, the official Indonesian Directorate General of Taxes English MLI synthesised text; it records entry into force on 1992-08-11 and MLI application from 2022-01-01.
- Parameters added: Article 10 dividend cap 15%; Article 11 interest cap 15% and government-interest exemption; MLI Article 7(1) principal-purpose test. No royalty parameter was inserted because this published text did not provide a directly citable royalty article.

## 2026-10-27 — Indonesia–Thailand MLI treaty registration

- Document and treaty row added: `treaty.id-th.2012.mli.en`, from the official Indonesian Directorate General of Taxes English synthesised treaty page. The page records the MLI's entry into force on 2020-01-08 and application from 2023-01-01.
- The base treaty entry-into-force date and article-level parameters are deliberately deferred until separately sourced and cited from the official material.

## 2026-10-27 — Indonesia–Vietnam MLI treaty expansion

- Document and treaty row added: `treaty.id-vn.1997.mli.en`, sourced from the official Indonesian Directorate General of Taxes English treaty PDF published as modified by the MLI. The DGT treaty-and-MLI index records signature on 27 December 1997, entry into force on 10 February 1999, effective application from 1 January 2000, and MLI modification from 1 January 2024.
- Parameters added: Article 10 dividend cap 15%; Article 11 interest cap 15% and the stated government/central-bank/qualifying-government-financial-institution exemption; Article 12 royalty cap 15%.
- Evidence boundary: no separate principal-purpose-test parameter was added. The registered current text is the official MLI-labelled source, but the collected English text does not contain a directly citable PPT provision; none is inferred.

## 2026-10-27 — Indonesia domestic guidance and index coverage completed

- Documents added: `id.dgt.treaty-index`; `id.per25-2018.treaty-procedure`; `id.dgt.residence-registration`; `id.dgt.skd-spdn`.
- Official sources and scope: the DGT English treaty index supplies the treaty-list page; the official English PER-25/PJ/2018 text supplies treaty-benefit procedure and beneficial-owner requirements; the DGT residence/registration regulation supplies individual-residence and corporate-domicile determination guidance; and the current DGT domestic-taxpayer domicile-certificate service page supplies issuance conditions and portal procedure.
- Acceptance: `python database/tools/build.py --jur id` returned `PASSED`. This removes the final Indonesia category gaps (5, 6, 8 and `page_treaties`). A full materialising build reported 0 errors and 97 coverage gaps outside Indonesia.

## 2026-10-27 — Thailand corporate-scope and transfer-pricing expansion

- Documents added: `th.rd.transfer-pricing-legislation`; `th.rd.foreign-company-guide`.
- Parameters added: `th.inbound.foreign_company_thailand_income_taxable`; `th.residence.company_incorporated_under_thai_law`; `th.anti_abuse.transfer_pricing_market_price_adjustment`.
- Source and scope: the Revenue Department's foreign-company guide states the Thai-source withholding treatment of a foreign company with no Thai business, defines a Thai company as one registered under Thai law, and records the relevant tax-registration/filer rules. Its transfer-pricing page expressly describes market-price adjustment to prevent evasion from manipulated MNE transfer pricing.
- Acceptance: NOT PASSED (0 errors, 3 Thailand gaps). The three remaining gaps are company CFC, individual anti-abuse and individual CFC. No CFC absence was recorded because the collected official sources do not expressly state that Thailand has no CFC regime; an absence record will be made only with a direct official basis.
