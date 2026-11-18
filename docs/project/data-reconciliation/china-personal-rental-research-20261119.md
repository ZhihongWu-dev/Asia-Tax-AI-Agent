# China personal rental: calculation periods and integration evidence

Status: implementation pending; this does not establish rental business acceptance.
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

Before implementation, resolve the threshold basis after taxes/sublease rent and
repairs, treatment of months with insufficient income, the aggregation of
multiple properties, and housing-rate eligibility for foreign property. Domestic
housing FAQs mentioning 10% do not alone prove foreign housing eligibility.
Archive and hash the applicable original deduction provisions before including
them as calculation sources. Keep separate paid foreign income tax eligible for
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
