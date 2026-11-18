# Vietnam business and property-rental consolidation

Government original archived as `database/raw/vn/vn.vbhn25.2026.business.vi.pdf`.
Landing: https://chinhphu.vn/?classid=2629&docid=219194&pageid=27160
Original: https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/8/25-vbhn-btc.signed.pdf
SHA256: `f26a121b3f3c8d5e3c77563f83ba6bd658e6d243eea2de3a195b8b916878ba57`.
808168 bytes, 21 pages; physical pages 1, 3 and 4 visually reviewed.

The 13 August consolidation combines Decree 68 with Decree 141. Article 4
shows the amended VND 1 billion thresholds and footnotes their 1 January 2026
effect. Paragraph 3 governs allocation across ordinary business activities;
paragraph 4 separately addresses property-rental contracts. For tenant-filed
returns, the contract must specify filing/payment responsibility and the
allocated deduction; unused deduction can continue across other rental contracts.
Paragraph 5 retains ordinary-business method selection and continuity rules.

Next implementation must retain per-contract allocations and tenant-filed
amounts, distinguish accommodation services, and reconcile all annual receipts.
Mixed property/ordinary-business deduction interaction still needs explicit
review; these pages alone are not recorded as resolving that interaction.
The consolidation predates Decree 398, so annual relief still needs the later
source. No active catalog was changed by this archive.

## Implementation and verification

`vietnam_rental.resident_property_rental_tax` and the saved-case policy
`vn_property_rental_2026` now handle annual resident domestic rental-only cases.
Each saved income maps to exactly one unique contract. Revenue is derived from
saved facts; allocated deductions reconcile to the saved total. Contract filing
responsibility, contractual allocation and actual prepaid amounts require explicit
verification. Per-contract and aggregate balances preserve overpayments.

Thirty-two new tests cover threshold boundaries, shared allocations, payment
balances, rejected inputs, case reconciliation and API persistence/replay after
store restart. Editing facts invalidates the current result while retaining its
historical snapshot. The full income-tax suite passed: 1,406 tests in 23.46 seconds.
All six referenced original-file hashes were verified locally.

Frontend intake remains pending. Mixed business/rental, accommodation, foreign
income, VAT and filing/rounding procedures remain outside this component and
remain outstanding toward the broader business objective.

Development reference: https://github.com/openfisca/openfisca-core (AGPL-3.0;
recent maintenance and open period/precision issues reviewed). Existing project
Decimal arithmetic and immutable case snapshots were retained. No external code
or dependency was adopted.
