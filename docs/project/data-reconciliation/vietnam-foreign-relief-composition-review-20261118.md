# Vietnam foreign credit and annual reduction: composition review

Status: source evidence established; combined assessment remains incomplete.

Reviewed the archived original Decree398/2026, physical pages3–5, against SHA256 `97a1811294e23e12b564d1b103d1ea8ee64e9bbedb6208ebab498d28d9f66180`:
https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/11/398_2026_nd-cp_29102026-signed.signed.pdf

Article3(2) explicitly covers the enterprise's entire annual income, including income described in CIT Law Article18(3). It applies the annual reduction after other tax incentives. Therefore an adapter must not assume that income excluded from ordinary preferential incentives is automatically excluded from this30% annual reduction. Article3(3) defines the revenue threshold using sales/service revenue before revenue deductions, financial revenue and other income; dependent units and post-resolution splits require the specified aggregation. Article4 applies to tax periods2026 and2027, effective29October2026. Article5(1) assigns implementation questions to the Ministry of Finance.

Separately re-read the scoped original Decree320 Article12(2): treaty-country investments follow the applicable treaty under(a); the explicit20% rate, payment/supplemental filing and project loss provisions in(b) are situated within the non-treaty branch. A combined policy must not copy this branch wholesale across the ten covered treaty counterparts. Existing ordinary domestic company calculation intentionally rejects foreign income, while the credit workpaper accepts a separately established same-income tax limit. Neither currently proves a combined company assessment.

Required next evidence: map the current03/TNDN annual return and its annexes, then resolve how the2026 reduction and treaty credit interact in the same-income cap and final liability. The reviewed Decree398 text specifies ordering after incentives but does not itself provide an explicit foreign-credit ordering formula. No combined formula or assumed foreign-income exclusion was added from inference.

Development reference revisited: https://github.com/openfisca/openfisca-core (period-scoped tax modelling). Existing project arithmetic and immutable case snapshots remain the integration approach; no external code or dependency adopted. Source research also found a November2026 consultation for amendments to Decree320; a consultation draft is not an enacted amendment and has not been applied.

Verification artifacts: local `vn398-review-3.png`, `vn398-review-4.png`, `vn398-review-5.png` under the integration audit directory; original SHA256 checked. Original optimizer PID16760 remained live during the review. No frozen calculation inputs, catalog data, deployment or remote branch changed.


## Additional official publication check

The Ministry of Industry and Trade market-surveillance publication of Decree398
was checked on 2026-11-18, including its appendix. The appendix lists three
personal-income-tax forms (business declaration, withholding/on-behalf declaration,
and adjustment after exceeding the revenue threshold). It does not supply a
corporate foreign-credit/annual-reduction composition worksheet. Article3(4)
addresses corporate provisional payments and later adjustments, without resolving
the outstanding same-income cap ordering. This check does not justify a combined
calculation change; the existing incomplete status remains.

Source: https://www.dms.gov.vn/documents/20182/22561/_VB_1793672891399_VB_2026%2BNgh%E1%BB%8B-%C4%91%E1%BB%8Bnh-398-2026-N%C4%90-CP%2BGIAM%2BTHUE%2BTHU%2BNHAP%2BCA%2BNHAN%2BDN.pdf/b820efca-c2b5-c231-d9f2-b58cafb351fa?t=1793672891420&version=1.0
