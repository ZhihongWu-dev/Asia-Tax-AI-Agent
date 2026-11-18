# Vietnam resident business income: source review and implementation gap

Status: calculation component, saved-case API and bilingual UI implemented;
ordinary domestic business browser acceptance passed. Broader business scope remains open.

Archived government original `database/raw/vn/vn.decree68.2026.vi.pdf`:
https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/3/68-ndcp.signed.pdf
Government landing page: https://vanban.chinhphu.vn/?docid=217111&pageid=27160
SHA256: `8d5b8099009a0981baa14ed65d5906fc2adb3e774042397e7b33c233a9c3811a`.
19 pages, 969565 bytes. Scanned PDF without extracted text; all nineteen
physical pages visually reviewed across the initial and follow-up reviews.

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
settlement/refunds to Decree 68. Physical pages 56–57 and 59–61 were subsequently
visually reviewed: Article 69(1)(a) applies resident business-income provisions
from tax year 2026; the three-page annex confirms the category percentages.

Decree 398 physical pages 1–3 were visually reviewed for Article 2. The 30%
reduction applies to resident business income for 2026/2027 when actual annual
business revenue does not exceed 10 billion VND, irrespective of calculation
method. Above that revenue threshold, provisional relief must be reconciled
and repaid. The component calculates final annual entitlement, not quarterly
filing penalties or an automatic refund claim.

`packages/income_tax/vietnam_business.py` now implements the 2026 resident
ordinary domestic business component: explicit method/evidence attestations,
reconciled category revenues, one shared allocated revenue deduction, profit
expenses, boundary-sensitive rates, annual reduction and payment balance.
It preserves the following-year method switch when a valid revenue-method
business crosses 3 billion VND. It does not choose a method or allocation for
the user. Thirty focused tests passed, covering threshold and rate boundaries,
category rates, allocation caps, losses, prepayments, rejected inputs and
source isolation. Source provenance is included in the result.

The `vn_business_2026` basis now routes through the existing saved-case API.
Every saved business income must have exactly one indexed classification;
amounts come from the saved case rather than a second editable revenue copy.
Revenue deductions or profit expenses must reconcile to saved deductions.
Foreign income/credits, unsupported periods, residency, subject and carried
losses are rejected. Thirteen additional contract/API tests passed, including
result persistence after storage restart, request replay and invalidation after
facts change (43 focused tests in total).

The frontend now collects a classification for each saved income and either
allocated revenue deductions or verified profit-method expenses. Changing the
method clears confirmation and omits inapplicable fields from the API basis.
The result displays activity amounts, annual relief, method-continuity notices
and the five preserved source references. Two browser tests passed for mixed
digital-content/goods income: revenue-method tax 3,500,000 VND and profit-method
tax 105,000,000 VND, including save/reload and Chinese display. The production
frontend build passed. Initial test failures were exact label locators for
select elements; accessible-role locators resolved them without product changes.
The combined income-tax browser regression then passed all 59 tests in 4.3
minutes (`income-tax.spec.ts`, `income-tax-coverage.spec.ts`, and
`vietnam-business.spec.ts`), using the local API, SQLite and fixture authentication.
This is local integration evidence, not hosted two-account/provider acceptance.
React's official preserving-and-resetting-state and thinking-in-react examples
in https://github.com/reactjs/react.dev informed the existing controlled-form
integration; no external code or dependency was adopted.

Development reference: https://github.com/openfisca/openfisca-core (period-specific
rules/tests; AGPL-3.0). No source code or new dependency was adopted; existing
project Decimal arithmetic and source snapshots were used.

Required next work:

- Add property-rental handling and reconcile mixed property/ordinary-business
  cases, special exemptions and foreign business separately; the component's
  explicit scope excludes these rather than assigning them ordinary rates.
- Surface method-history and documented-expense verification in case intake;
  the calculation component requires verification but does not establish it.

No active catalog or frozen planner input changed. The new API policy and
calculation component and UI do not complete broader business acceptance or
hosted delivery.
