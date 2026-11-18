# China personal rental: calculation periods and integration evidence

Status: monthly expense-base component implemented; annual workflow pending.
This does not establish rental business acceptance.
Delivery remains local only. Corporate and personal coverage of all eleven
dividend jurisdictions remains the overall requirement.

## Confirmed rules and implications

- IIT Implementation Regulations Article 14(2) defines a rental occurrence as
  income obtained within one month. Verified in the archived `cn.reg.iit` original
  (SHA-256 `e5f3ca819c7638df993babe537b9c91907b87bf5ae8f0213c8fa9fef4019a221`).
  An annual rental total cannot establish the monthly tax calculation.
- IIT Law Article 6(4) provides the 800 deduction up to 4,000 and 20% expense
  deduction above that threshold. Article 3 establishes the ordinary 20% rate.
- Announcement 2020-3 section II(3) requires foreign classified income to be
  calculated separately from domestic income. Rental tax belongs in the relevant
  country's other-category Chinese tax before applying foreign-credit limits.
  The archived original is already part of the personal credit source manifest.
- The official 1994-89 provisions permit evidenced taxpayer-borne repairs,
  limited to 800 per occurrence, carrying unused repairs to subsequent occurrences.
  The official Yunfu explanation of 2009-639 identifies the deduction order as
  rental taxes/fees, rent paid to the lessor, repairs, then statutory expenses.
  The latter is interpretive evidence, not authority for automatically applying
  local collection methods to foreign rental properties.

Sources inspected on 2026-11-19:

- https://fgk.chinatax.gov.cn/zcfgk/c100010/c5194444/content.html
- https://fgk.chinatax.gov.cn/zcfgk/c100009/c5193028/content.html
- https://fgk.chinatax.gov.cn/zcfgk/c102416/c5207136/content.html
- https://fgk.chinatax.gov.cn/zcfgk/c100011/c5216297/content/metadata/征收个人所得税若干问题的规定.pdf
- https://guangdong.chinatax.gov.cn/yfsw_zcedwjjd/2019-12/02/content_fe1d6a84a5494a17bda1be0b0e389946.shtml

## Required workpaper and verification

Preserve saved-income links, country, month and property identity; establish the
legally appropriate aggregation unit before imposing uniqueness. Reconcile all
monthly gross amounts to saved facts. Record opening eligible repair balance,
new evidenced repairs, used repairs and closing balance, with chronological
processing and no cross-property or cross-country transfer inferred. Do not
allow duplicate papers to multiply the monthly deduction. Annual balances need
replayable evidence across years, not an unexplained annual deduction total.

The threshold basis is now resolved by the national explanation reproduced at
https://shanghai.chinatax.gov.cn/tax/zcfw/zcjd/200912/t291158.html:
use the balance after taxes/sublease rent and repairs, then apply statutory
expenses. The original HTML is archived and hashed in
`cn_personal_rental_sources.json`. For example, gross 5,000 less established
preceding deductions 1,200 leaves 3,800; the statutory expense is 800 and the
remaining base is 3,000, not 3,040. At exactly 4,000, both formulas give 3,200.

The internal `monthly_expense_base` component preserves this order and exact
decimal precision, with 15 passing tests including threshold boundaries,
annual/monthly counterexample, invalid inputs and archived source hashes.
It does not determine eligibility of preceding deductions or calculate annual
tax. Negative balances require separate eligibility/carry treatment and are
rejected, rather than silently generating a loss deduction.

Before annual integration, resolve treatment of months with insufficient income, the aggregation of
multiple properties, and housing-rate eligibility for foreign property. Domestic
housing FAQs mentioning 10% do not alone prove foreign housing eligibility.
Direct downloads of the Shanxi 2009-639 original and national 1994-89 HTML
returned HTTP403 during this pass; neither has been archived or added as a
calculation source. Archive the repair entitlement provisions before adding
automatic repair carry. Keep separate paid foreign income tax eligible for
credit and rental expenses, so the same payment cannot silently count twice.

Acceptance must include monthly versus annual counterexamples, threshold
boundaries, multi-month repairs, year-end carry, multiple properties/countries,
invalid duplicate/missing months, deduction reconciliation, foreign-credit
allocation, saved-case replay and bilingual readable exports. Existing snapshots
without rental papers must retain historical results. Complete the API, UI and
reports after the rules are established; a standalone calculator is insufficient.

## GitHub design research

Reviewed https://github.com/openfisca/country-template as a reference for
separating time periods, formulas and parameters. The repository declares
AGPL-3.0 and Python 3.11 support. No external code or dependency is adopted.
This reference does not supply Chinese tax rules. Recent maintenance, open
issues and compatibility would need a fresh dependency review before any
adoption; no adoption is proposed here.


## Repair ledger followup

The Guangdong tax authority reproduction of1994-89 is now archived as
`database/raw/cn/cn.rental.1994-89.html` and hashed in the rental source manifest.
Its partial-repeal notice identifies the old rate tables and Articles13/15;
this component uses only Article6(2), not those repealed provisions.

`repair_ledger` checks twelve explicit months for one established property,
chronological availability, the800 monthly ceiling, and conservation of opening
balance plus new eligible repairs less established deductions. It preserves
unused balances through inactive months and reports year-end carry. Deduction
eligibility (especially insufficient rent), property aggregation and annual
income reconciliation are not established by this ledger. Those remain required
before opening the annual rental workflow.22 component tests passed in0.85s,
including duplicate/missing months, borrowing future repairs, cap excess,
reordered input, context independence and source hashes. No UI/API route enabled.


## Saved-fact calculation integration

RentalYear now links one property to one saved rental income, requires12 explicit
months, reconciles gross totals, checks monthly deductions/donations/reductions,
and calculates ordinary20percent tax per month. Property IDs and income indices
cannot be duplicated. Repair cost incurred is distinct from deductions used.
The personal foreign workpaper accepts optional rentals and includes each
country's calculated rental tax in its other-category credit limit. Claimed
case deductions reconcile to taxes/fees, subrent, repairs used and donations;
statutory rental expense deductions are not counted twice.

67 component, personal assessment and historical replay tests passed in8.22s.
A60000 gross rental fixture with6400 established deductions produces8560 tax;
10000 eligible foreign tax is capped at8560. Housing concessions, negative-month
eligibility, property aggregation judgments and advance-rent allocation are not
inferred. Rental API persistence/reopen/export acceptance, UI and readable
monthly reports remain pending. This does not complete rental business coverage.


## Persistence and readable export verification

The mixed personal-income API test now includes an ordinary rental property.
It saves facts, calculates, disposes/reopens the SQLite store, checks the exact
saved run, exports both languages, and verifies all12 closing repair balances
and the700 year-end carry in the readable section before the JSON appendix.
Source hashes remain in the report; an invalid recalculation returns422 and
leaves the saved state unchanged. The rental total remains8560 after reopen.

Readable exports include monthly gross, taxes/fees, subrent, new repairs, repairs
used, statutory expense base/deduction, donation, taxable income, gross tax,
reduction and net tax, plus opening/closing repairs. Scope text no longer says
rental is excluded for snapshots actually containing rental results; historical
snapshots without rentals retain their prior wording. Markdown escaping is
preserved.69 focused assessment/component/report tests passed in6.70s.
Frontend entry and browser acceptance are still pending. Full business coverage
and actual-case acceptance remain incomplete.
