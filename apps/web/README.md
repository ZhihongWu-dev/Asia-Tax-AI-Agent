# AsiaTax web demo (local)

An English web front end for the Hong Kong FSIE L0 research prototype: a landing page that
describes the system honestly, and a `/demo` page that runs a fictional case through the
real pipeline (candidate-fact extraction → dictionary contract → deterministic rule chain →
statutory text) via the local FastAPI service.

Local research use only. It inherits every L0 limit: rules are unverified by a Hong Kong tax
professional, only synthetic cases may be sent to the model, and nothing here is tax advice.

## Run it

Prerequisites, from the repository root:

1. Local database built: `make db-up migrate load knowledge-build`
2. Model adapter configured in `.env`: `FSIE_MODEL_BASE_URL`, `FSIE_MODEL_API_KEY`, `FSIE_MODEL_NAME`
3. Node.js 20.9 or newer (`nvm use` picks up `.nvmrc`) and pnpm (`corepack enable pnpm`)

Then, in two terminals:

```sh
make run-api                      # FastAPI on 127.0.0.1:8000
make web-install && make web      # Next.js on localhost:3000
```

The browser only talks to Next.js; `/api/*` is proxied to the API (`FSIE_API_URL` overrides
the target). Open `http://localhost:3000`, or link straight to a preset that runs on load,
for example `/demo?preset=deemed-receipt&run=1`. Preset ids are in
`apps/api/demo_cases_en.json`.

## What is where

| Path | Purpose |
|---|---|
| `app/page.tsx`, `components/landing/` | Landing page |
| `app/demo/page.tsx`, `components/demo/` | Case panel and result view |
| `lib/fsie.ts` | API types and English labels for dictionary fields and chain nodes |
| `next.config.mjs` | `/api/*` proxy to FastAPI |

## Provenance and choices

- Layout and animations are adapted from the v0 community template "Optimus" (kerroudj).
  All of its content was replaced, including invented customers, certifications, pricing and
  uptime claims. The template page states no licence; check its terms before any public use.
- Numbers on the landing page (719 legal units, 5 of 10 chain steps, 92 offline and 22 live
  tests, 10/10 golden cases, 8/8 English presets plus the injection preset) were measured on the local build when this
  page was written. Rebuilding the knowledge base can change the unit count.
- Unused template dependencies were dropped: expo, react-native, three.js and Vercel
  Analytics, which would report to Vercel.
- `sharp` may not run its install script (`pnpm-workspace.yaml`). It only serves `next/image`
  optimisation, which is disabled.
- `typescript.ignoreBuildErrors` was removed, so `pnpm build` type-checks.
