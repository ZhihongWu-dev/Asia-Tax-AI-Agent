# Vietnam resident business income: source review and implementation gap

Status: source acquisition and targeted review; calculator/API/UI not implemented.

Archived government original `database/raw/vn/vn.decree68.2026.vi.pdf`:
https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/3/68-ndcp.signed.pdf
Government landing page: https://vanban.chinhphu.vn/?docid=217111&pageid=27160
SHA256: `8d5b8099009a0981baa14ed65d5906fc2adb3e774042397e7b33c233a9c3811a`.
19 pages, 969565 bytes. Scanned PDF without extracted text; physical pages 1–6
visually reviewed. This is not a review of all nineteen pages.

Article 4 distinguishes resident business income, the revenue-percentage method,
the income-minus-costs method, and property rental. Article 4(3) permits allocation
of the annual revenue deduction across eligible business categories/locations,
with one total cap rather than a deduction for every income line. Article 4(5)
specifies method election and two-year continuity, including the following-year
switch after a revenue-method business exceeds the applicable upper boundary.
Articles 5–6 prescribe revenue recognition and allowable expenses; expenses
are not simply every amount entered by the taxpayer. VAT is a separate tax.

Decree 141/2026 Article 1(1), visually rechecked on physical page 1 of the already
archived government original, replaces the 500 million VND references in
Decree 68 Article 4 (among specified other provisions) with one billion VND.
The original Decree 68 threshold must therefore not be shipped unchanged.
Its provenance and effective-date review are in
`vietnam-decree141-credit-scope-20261118.json`.

PIT Law Article 7 was visually reviewed in the existing Gazette archive
`vn.law.pit2026.vi.pdf`, physical pages 35–36. This file contains several laws;
other occurrences of Article 7 concern education or construction, not income
tax. Article 7(2) gives profit-based rates of 15%, 17%, 20% with revenue bands;
7(3) provides distinct business-category percentages and 7(4) property rental.
The original threshold must be reconciled with the later amendment above.

Extracted Decree 253/2026 Article 45 (physical page 29) expressly refers resident
business taxation to PIT Law Article 7 and Decree 68 with amendments; its annex
provides detailed industry classification. Article 68(3) similarly refers business
settlement/refunds to Decree 68. These passages still require visual review with
the annex and Article 69 transition before final implementation.

Required next work:

- Review Decree 68 remaining filing/transition provisions, Decree 253 industry
  annex and effective application, and Decree 398 personal-business reduction.
- Model explicit method election/history, all-business revenue reconciliation,
  category/location deduction allocation, documented expenses, and payments.
- Integrate with saved personal-income cases and sourced immutable assessments;
  cover threshold boundaries, mixed categories, method continuity, relief and
  save/reload behavior. Existing employment and capital-transfer adapters do not
  satisfy this business-income requirement.

No active catalog, frozen planner input or calculation policy changed in this review.
