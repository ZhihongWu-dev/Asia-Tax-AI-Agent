# Li/Main integration status (2026-11-15)

This is the trial integration on `Zhihong-Wu`. `main` has not been changed.

## Data

- The existing private Supabase `database` schema contains 38,152 clauses and 287 documents from the 2026-11-13 Li upload. The existing chat's `public.sources` / `public.legal_units` are separate.
- Compared the immutable `main` and Li clause CSVs by `cite_id`: 107 main-only citations and 25 shared citations with different text. All 107 main-only citations are whole-document (`#all`) records. The cloud library already has the parent document for 82 of them; 25 parent documents are missing there.
- Created private `database_integration.source_review` through migration `li_data_overlay_20261115` and registered all 132 differences as `candidate`. No candidate has been accepted or exposed to user answers. The table records the main commit, base upload identifier, and document metadata. `anon` and `authenticated` have no table grants.
- The 25 missing documents are predominantly Japan and Thailand sources, plus two Korea documents. Their original content and the 25 conflicting texts still require source, date and hash review before publication. Re-running Li's upload would drop and rebuild the base schema, so it is not an integration mechanism.

## Feature

- The authenticated `/api/library/search` endpoint reads the private cloud library with a bounded query and explicit jurisdiction.
- Explicit mainland-China tax questions in ordinary chat now use a separate source-grounded path. It only admits official `.gov.cn` URLs, requires exact quoted evidence in the model output, and saves the library version and citations with the conversation. A model failure returns links to the source excerpts, not an ungrounded conclusion. Hong Kong-only and mixed Hong Kong/mainland questions remain on the existing workflow.
- English interface selection is honored for new answers even when the question is in Chinese, unless the user explicitly requests another language.

## Acceptance evidence

- Live cloud lookup for `中国内地企业所得税税率是多少？` found `cn.law.eit#4` and related official passages. The generated answer cited Article 4 and distinguished the 25% general rate from conditional rates.
- A local account-scoped FastAPI request created a case and posted the same question: HTTP 201 then 200, saved revision 1, answer status `source_grounded`, workflow `library-cn-0.1.0`. The streaming route also returned a `done` event and an English answer when `locale=en`.
- Compile and staged diff checks passed. The full existing test suite, cloud account isolation, Li planner/report flow, rule evaluation, and Render deployment have not yet been verified.

## Next gates

1. Validate each missing/conflicting source against its official original and effective period, then publish accepted overlay data with an immutable text hash. Keep rejected candidates out of retrieval.
2. Resolve Li's added and changed rule citations against the accepted source version; run its golden cases without replacing the existing HK workflow.
3. Adapt Li's planner and report flow behind the signed-in case API with durable runs and account isolation; add a frontend entry without switching to Li's standalone local-user server.
4. Run regression and cross-account tests on `Zhihong-Wu`, verify the deployed branch, then merge reviewed commits to `main`.
