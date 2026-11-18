# Atlas frontend integration — partial verification

Ported Li's TaxAtlas, CountryPage, Glossary, ClauseDialog, map projection and
formatting components into the existing authenticated workspace. Existing chat,
income-tax and planning panels remain in the application. Added a sidebar entry
and return-to-workspace control, upstream English strings, stale-response guards,
and packaged dependency notices in public/atlas-licenses.txt.

## Reference and dependency review

- https://github.com/d3/d3-geo — repository pushed 2026-11-03; installed 3.1.1.
  Inspected package permission notice. Open issues include projection precision
  and antimeridian bounds; map is browsing context, not a boundary authority.
- https://github.com/topojson/topojson-client — ISC, pushed 2022-08-31;
  installed 3.1.0. Open issues include ESM adoption and mesh API changes.
- https://github.com/topojson/world-atlas — ISC, archived, pushed 2021-08-11;
  installed 2.0.2. Open issues include disputed boundaries and duplicate country
  IDs. Retained Li's static Natural Earth geometry for display, separate from
  the engine's jurisdiction codes. This is not evidence of current boundaries.

The npm audit returned five high-severity findings in the existing Vite toolchain
(vite, picomatch, fdir, tinyglobby, source-map-js), not the new map packages.
Raw report: integration-audit-20261116/atlas-npm-audit-20261118.json outside repo.
Follow-up: upgraded Vite from 8.3.1 to 8.3.8 and ran non-forced audit fix.
The Vite-specific and source-map-js findings no longer appear. Full audit still
reports five high entries, now all from picomatch and its dependent development
packages (fdir, tinyglobby, Vite, plugin-react). GHSA-fc5q-39xc-vjpf lists no patched
version as of this review; forcing npm's proposed downgrade to Vite 6.2.7 would
cross major versions and is not an accepted fix. Production-only npm audit
reports zero vulnerabilities. Render starts uvicorn and serves built static
assets, not the Vite development server. Development dependency risk remains.

References: https://github.com/vitejs/vite/releases and
https://github.com/advisories/GHSA-fc5q-39xc-vjpf . Post-upgrade audit archived as
atlas-npm-audit-after-20261118.json in the same external audit directory.

## Verification and remaining work

- Production TypeScript/Vite build passed (existing >500 kB chunk warning).
- Edge/Playwright: one navigation/unavailable-data/return-to-workspace test passed.
- Added successful fixture-based browser coverage for rates, unknown values,
  country detail, complete long clause text, Escape dismissal and glossary.
  These fixtures verify presentation, not live catalog or tax-law correctness.
- Backend atlas projection/process/API suite: 21 passed in the preceding change.
- Still required: live reviewed-bundle map/country execution; successful map,
  glossary and citation browser flows; cross-view snapshot consistency; mobile
  layout and keyboard dialog review; dependency remediation; full regression.
- No production deployment or final branch push performed for this change.
