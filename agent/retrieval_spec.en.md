# Reading and Retrieval Specification (RAG)

English copy of `agent/检索规范.md`; when the two differ the Chinese version prevails, and whoever changes one updates the other.

2026-11-03. The fifth specification of the agent layer, beside the four agent specifications (front, analysis, polish, review). Everything the AI writes itself (code, comments, tool descriptions, index fields, evaluation records) is in English; provisions, product values and the client's words stay verbatim, untranslated and unparaphrased.

§15 records the user's decisions of 2026-11-03; the build order is in §13.

## 0. Why

The four agents read three kinds of material: the law library (database/), the optimization layer's products (cases/<case>/intake/products/<run_id>/) and the case file (facts, sources, dialogue and documents under intake/). Today they find and read on their own, through the host's Glob / Read / Grep and the whole-block readers of each layer's MCP. Measured on CASE-20261102-a032c0 on 2026-11-03:

| Observation | Figure |
|---|---|
| Analysis node, qwen3.8-flash, in 22 minutes | 98 tool calls, nothing written |
| Of which, finding files | 21 Glob calls: 9 refused by the guard (whole-case sweeps), several empty because a pattern with a sub-folder fails on Windows; 5 Grep |
| Tool results read into the context | 531,446 characters in total, about 140 thousand tokens; largest single results 62,545 (a file the host saved for an oversized result), open_items 56,071 (read twice), requirements 39,034 and 39,003, brief.json 33,674 |
| Model thinking | 212,349 characters against 186 characters of visible text: every turn re-thinks over a context of well over a hundred thousand tokens |
| Same node, qwen3.8-max | 5,197 s, 114 turns, 172,349 output tokens; the 46,480-character sources table was sent whole three times |
| Products of one run | 47 MB: edges/ 3,876 files 43 MB, graph.json 2.3 MB, deltas 247 KB, tax 206 KB, gap 135 KB |
| Law library | 156 documents, 18,411 clauses, 24.2 million characters; clause length median 360 characters, p90 1,877, p99 9,334, maximum 6.5 million (a whole act cut as one clause); 1,717 clauses over 2,000 characters |
| Case documents | 16 files, 1.6 MB, PDF and PNG scans |

Conclusion: the slowness comes from not finding and from reading too much, not from the model. A faster model wrote faster and the total time did not fall. The literature explains the observation consistently: the longer the input, the worse and the less uniform the model's performance, even when the information is in the context [R18]; an agent's tools should return token-efficient information, and a bloated tool set is itself a common failure [R19].

## 1. Position and principles

1. **A shovel, not an author.** The retrieval service is a program: it slices, indexes, finds, fetches and checks, all deterministically; the same index version and query always give the same result. It writes no report, judges nothing and rewrites no question for the model. `目标.md` §4.3 items 8 and 9.
2. **Returns only original text and original values.** Provisions verbatim, product values as they are, the client's words verbatim. Index fields (heading paths, template verbalisations) serve matching only and are never returned as content. No generated text enters a return body.
3. **No scores.** Returns carry rank, the channels that found the hit, validity and language, never a similarity or reranker score, so that no score can leak into the report (`目标.md` §4.1 item 1 forbids scoring).
4. **Nothing from the web is indexed.** The index covers the library, the products and the case file. What an agent finds online still goes only into the report, with its tier stated (§4.3 item 9).
5. **Abilities are added, never removed.** The new tools are additions; the host's Read / Glob / Grep stay, the guard rules stay (§4.3 item 11). Make Glob unnecessary rather than forbidden.
6. **Provenance is one thing.** Every returned fragment has a stable id, and the id is the `ref` of the sources table; before delivery the program checks that every figure and citation in the draft occurs in the fragments it cites. Ids are internal and never appear in client text (§4.4 item 14): polish removes them, and `report_check`'s leak patterns gain the id formats.
7. **Method by material.** The three kinds of material differ in nature; one vector search does not fit all. A method is adopted on this project's evaluation, not on a paper's numbers (§12).
8. **Time.** A provision is taken as in force on the transaction date; a date before the library's coverage is answered "not covered", never with today's text (finding I20 of round I, already implemented in the archived `official/` knowledge layer).

## 2. The three materials and their methods

| Material | Nature | Retrieval unit | Method | Basis |
|---|---|---|---|---|
| Law library | Long bilingual text; chapter hierarchy, cross-references, effective dates; one provision often has a Chinese and an English expression | The clause; long clauses cut into units (at most 260 characters for Chinese, Japanese and Thai, 700 for English), each with its hierarchical heading | Exact channel first (article numbers, cite_id, param id); FTS5 BM25 (CJK bigrams) + BGE-M3 dense, reciprocal rank fusion, language-balanced; bounded expansion along explicit reference edges; optional reranking; date filter | I1, I2, I4, I5, I6, I15, I20; R6, R7, R11; this project's round-I evaluation |
| Optimization products | Structured JSON that is itself a graph: structure → branch → hop → rule → clause; judgment points, scenarios, condition trees, open items | Typed records, each with a stable id, filter fields, a one-sentence program-written verbalisation, a compact card and a pointer to the full record | Field filters + BM25 over the verbalisation; bounded expansion along the product graph after a hit; card first, full record on request; whole files are no longer returned |  R13, R14, R15, R16, R17 |
| Case file | Fact keys, source quotes, dialogue paragraphs, notes; documents are scans, mostly Chinese, with tables | Fact key, source row, dialogue paragraph, note entry; documents by page, tables by cell | Facts and dialogue by fields + BM25; documents parsed once by the program on upload (text layer first, OCR for scans), pages and cells indexed; quotes grounded verbatim or with tolerance | R22, R23, R16; I21 |

## 3. Overall structure

```text
A Index layer (program; each material at its own moment)
   law        at the end of database/tools/build.py          → database/index/ (index.sqlite + vec.npy)
   products   after the optimizer run, called by the orchestrator → cases/<case>/intake/products/<run_id>/index/
   case file  on put_document / write_intake                  → cases/<case>/intake/index/
B Retrieval service (MCP, mounted per identity: tax-read-front / -analysis / -review / -polish)
   map · search · get · expand · ground · pack
C Prefetch pack (program; made when a node starts; the task text gives its path and the file inventory inline)
D Provenance (id = ref; report_check verifies figures and citations against the cited fragments)
E Evaluation (golden sets, metrics, ablations, end to end; run only on instruction)
```

The design follows the hybrid strategy of [R19]: what is always needed is prefetched (C); the rest the agent fetches on demand with tools (B); both share one scheme of ids and provenance.

## 4. Law library retrieval

Revive the archived knowledge layer (`archive/old-model-2026-10-31/official/tools/graph.py`, `search.py`, `eval_search.py`, 1,428 lines in all) and move it onto database/. It already implements unit splitting, hierarchical headers, explicit reference edges, FTS5, BGE-M3 vectors, reciprocal rank fusion, language-balanced fusion, personalized-PageRank expansion, three-valued validity and quote anchoring, and was evaluated on this project's golden standard (round-I synthesis §4, §6). This section records only what is kept, adjusted and added.

### 4.1 Units and context

- The clause (one row of clause.csv) is the citation unit; a clause longer than about 1.4 times the cap is cut into units: first at structural markers (paragraphs, items, numbered parts), then at sentence ends, small pieces merged up to the cap, what is still too long cut hard. The cap is 260 characters for Chinese, Japanese and Thai and 700 for English (about 100 English words of reading), as in graph.py's `split_units`: the values the round-I evaluation used. A unit must map back to a span of the original (start and end offsets); what is returned is that span, not a rewrite.
- Each unit carries a `header` used for matching only: the act's title, the path of part / chapter / section / article, the article heading, and short names the document defines for itself. This is deterministic contextualisation: Anthropic's contextual retrieval has a model write a 50 to 100 token explanation for each chunk and lowers the top-20 failure rate from 5.7% to 3.7%, to 2.9% with BM25 added, to 1.9% with reranking [R4]; on legal corpora, adding a document-level summary to each chunk clearly reduces retrieving from the wrong document [R11]. This library uses hierarchical headers rather than model summaries, because the header is part of the original and can be checked. Model-written explanations (`gloss`), decided by the user on 2026-11-03: switched on only once the whole library is collected; the index reserves the gloss field and a cache by text hash, so switching it on adds glosses without rebuilding the rest; a gloss enters only the matching fields and is never returned.
- Splitting follows structure, not semantics: across 36 chunking methods, 6 domains and 5 embedding models, structure-preserving chunking clearly beats fixed-length splitting, and paragraph grouping is best for law and mathematics [R7]; the compute of semantic chunking is not repaid by consistent gains [R9]; cutting legal documents at provision boundaries gives 100% boundary precision against 7.7% for recursive splitting and preserves 97.6% of cross-references against 0% [R6]. There is no universally best chunk size: factual questions favour small chunks (64 to 128 tokens), context-hungry questions large ones (512 to 1,024 tokens), and the optimum depends on the embedding model [R8]; this library keeps units small and fetches the parent clause on demand, serving both.

### 4.2 Channels and fusion

1. **Exact channel**: article numbers ("第十条", "section 15(1)(b)", "Article 10(2)"), cite_id, param id, decision id, short names of acts. A hit ranks first and does not enter fusion. Queries about rules and parameters belong here: in the round-I evaluation, queries made of our own invented discretion names were weak in every configuration (R@10 ≤ 0.13).
2. **BM25**: SQLite FTS5, CJK as character bigrams, everything else as words, two fields: `header` and body. Zero-shot, BM25 is a strong baseline and dense retrieval often loses to it out of domain [I1].
3. **Dense**: BGE-M3 (cached on this machine, 568M parameters, 8,192 tokens, strong in Chinese and English; in round I it lifted the params set from BM25's R@10 0.187 to 0.353 after fusion). Decided by the user on 2026-11-03: BGE-M3 only, no model comparison; Qwen3-Embedding (MTEB multilingual 0.6B 64.33, 4B 69.45, BGE-M3 59.56 [R1]) stays an option for later.
4. **Fusion**: reciprocal rank fusion, k = 60, no score calibration [I2]. **Language balance** is necessary: equal-weight fusion pushes every cross-language candidate below the same-language lexical candidates; in round I, Chinese-gold R@10 rose from 0.032 to 0.318 and cross-language (treaty zh→en) R@10 reached 0.717.
5. **Graph expansion**: personalized PageRank along explicit edges only (contains, cites, same_provision, substitutes), with node specificity down-weighting, weight 0.5 (round I: R@10 0.353 → 0.377, cross-language 0.717 → 0.825). No model-extracted edges: incomplete and uncheckable [I13]. The literature places graph retrieval clearly: on simple fact lookup plain retrieval is equal or better, graphs win on multi-hop reasoning and synthesis [R13, R14]; on legal QA hybrid systems beat graph-only ones, which lose the text's semantics [R15]. Expansion therefore runs only after a hit, as a supplementary channel, depth 1 by default.
6. **Reranking**: a cross-encoder reranks the fused top 50 and returns the top k. Qwen3-Reranker-0.6B (decided by the user on 2026-11-03, no comparison): the same 0.6B as bge-reranker-v2-m3, multilingual retrieval subset MMTEB-R 66.36 against 58.36, English MTEB-R 65.80 against 57.03, long documents MLDR 67.28 against 59.51, Chinese CMTEB-R 71.31 against 72.16, about even [R1, the authors' own runs]; 32k context, so long clauses need no truncation; accepts a task instruction. Japanese clauses (10,353), the mostly English Hong Kong and Singapore clauses and the bilingual treaties are the majority of the library, so stronger multilingual ranking fits. Reranking is switched on only after evaluation: on a contract corpus a general reranker has been reported to push Recall@64 from 61.06 down to 47.54 [second-hand report of R10, unverified]. The reranker has a separate switch per material type.
7. **Time**: `as_of` filters the effective windows of documents and parameters; a date before coverage answers NotCovered with the reason [I20].
8. **Cross-language**: the Chinese and English expressions of a treaty are linked by same_provision edges; query expansion uses a term dictionary (the Chinese and English meanings in rule/variable.csv and predicate.csv, plus the short names documents define for themselves). Cross-language targets come from explicit edges and the dense channel; the lexical channel is useless across languages [I4].
9. **Optional experiments**: late chunking (encode a whole clause or section with the long-context embedding model first, then pool per unit; no training needed [R5]); BGE-M3's sparse weights as a fourth channel. Adopted only if the evaluation shows a gain.

### 4.3 Returns

A hit: `id` (= cite_id or unit_id), act title, article heading, language, validity window, the verbatim fragment (the unit's text, at most `max_chars`), `other_lang` (ids of the same provision in the other language), `parent` (the clause), rank, channels. `get(cite_id)` returns the whole clause, paged by offset for long clauses, as tax-db's `clause` does.

## 5. Product retrieval

### 5.1 Typed records

After a run the program cuts the products into records, each with a stable id `<run_id>:<type>:<key>`:

| type | key | Source | Fields (for filtering) |
|---|---|---|---|
| structure | cand_id | paths.json, brief.json, ranking.json | path, moves, restructuring, signature, rank |
| branch | branch_id | tax.json, branches.json | cand, assumed answers, floor / ceiling, completeness |
| hop | branch_id/edge_id | hops/, the hops of tax.json | tail, head, jurisdiction, each tax item |
| cell | branch_id/edge_id/slot_key | the items of edges/ | jurisdiction, slot, rules, cite_ids, status, needs |
| rule | rule_id (used in this run) | rules_applied of edges/ | jurisdiction, slot, cite_ids, decisions |
| point | key@jur | brief.json, open_items.json | about, changes_rank, first under either answer, at stake, blocked branches |
| scenario | scenario_id | brief.json, scenarios.json | against, amounts per structure, first |
| requirement | cand_id/node | requirements/ | variables, predicates, source rules |
| open_item | key | open_items.json, gap.json | kind, client_supplies, question |
| transfer | cand_id/seq | transfers/ | consideration, cost, tax, stamp, flags |
| exposure, penalty | cand_id or branch_id | deltas.json, penalty/ | tax, interest, fine |
| past_payment | date | past_payments.json | amounts, conflicts, refundable |
| basis | cand_id | the cite_ids of hops/ and transfers/ with the library's text | every provision the structure's cells and transfers rest on: cite_id, title, article, the rules applying it, the cells, the text (first 800 characters each); those setting rates, exemptions and anti-abuse first, residence last. Added 2026-11-03: the analysis agent was fetching provisions one by one to check them |
| diff | field | diff.json | rank and interval moves against the previous run |

Each record carries: its filter fields; one English **verbalisation** (program template, ≤ 300 characters, used only for BM25 and the optional dense match, e.g. "branch c5.b0: cn:company > hk:company > sg:individual, all points favourable, tax 700,000 CNY (5.0 per 100), hops cn>hk wht 5%, hk>sg 0"); a **card** (≤ 600 characters, fields and values as they are); and a pointer to the full record (file path + JSON path). Values are always copied from the products, never recomputed (`目标.md` §4.3 item 9).

### 5.2 Graph and retrieval

- Edges: structure → branch → hop → cell → rule → clause (crossing into the law library by cite_id); point → the branches it blocks and the first structure under either answer; requirement → variables → fact keys; scenario → each structure's amount; transfer → structure.
- A query is first parsed for ids and filter words (cand, branch, key@jur, jurisdiction, slot, scenario); what filters can locate directly skips text matching, since on factual lookups graphs and vectors only add noise [R13]. The rest runs BM25 over the verbalisations (optionally plus dense), then expands the hits on request to depth ≤ 2 and at most 30 records. This is the two-level "schema then cells" idea: give the schema first, then fetch the cells asked for [R16]; choose the structure type (graph, table, catalogue) that fits the task at inference time [R17].
- **Hierarchical return**: cards by default; `get(id)` the full record; `expand(id, kinds, depth)` neighbour cards. Files like open_items (56 KB), requirements (39 KB each) and graph.json (2.3 MB) are no longer read whole into the context.
- brief.json remains the entry point, but its digest goes into the prefetch pack (§9), so the agent need not read it whole.

### 5.3 Relation to the existing slicing tools

Decided by the user on 2026-11-03: the mounts are slimmed together with the retrieval service, without waiting for the evaluation. The analysis agent mounted 65 MCP tools (tax-db 12, tax-rule 14, tax-opt 17, tax-case 22), and tool definitions themselves take context [R19].

| Identity | Mounts |
|---|---|
| Analysis, review | tax-read, tax-rule, tax-case; tax-opt registers only `evaluate` (evaluate one structure on demand) and `fx` (exchange rates), none of its readers; no tax-db |
| Front | tax-read, tax-rule, tax-opt-front (it runs the optimizer), tax-case; no tax-db |
| Polish | unchanged |

tax-read must cover every use of each reader removed:

| Old tool | tax-read |
|---|---|
| tax-db `find` | `search(scope=law)` |
| tax-db `clause` | `get(cite_id)`, same paging |
| tax-db `doc` / `param` / `param_history` / `decision` | `get("doc:<id>")` / `get("param:<id>")` (with the history along superseded_by) / `get("decision:<id>")` |
| tax-db `params_for` / `absent` / `treaty` / `jurisdictions` / `blocked` / `version` | `list("params" / "absences" / "treaties" / "jurisdictions" / "blocked")`; the version is in `map` |
| tax-opt `ranking` / `paths` / `scenarios` / `open_items` / `transfers` / `requirements` / `penalty` / `deltas` / `tax` / `hops` | `list("structures" / "scenarios" / "points" / "open_items" / "transfers" / "requirements" / "penalties" / "exposures" / "branches" / "hops", filters)` returns cards; `get(id)` the whole record |
| tax-opt `version` / `product_check` | the products digest of `map`; `product_check` is run by the orchestrator after a run, not by an agent |

## 6. Case-file retrieval

### 6.1 Facts, sources, dialogue, notes

- Records: every key of facts.json (value, unit, source row); every row of sources.json (key, doc, page, quote); every paragraph of dialogue.md (#n, verbatim); every judgment point of answers.json (value, quote); every entry of notes.md; every entry of constraints and to_collect. Ids `<case>:fact:<key>`, `:source:<n>`, `:dialogue:<n>` and so on.
- Retrieval by fields + BM25. Dialogue paragraphs and quotes are returned verbatim.

### 6.2 Documents

- Parsed once by the program at `put_document`, cached by sha256: a PDF with a text layer uses the text layer and its tables (PyMuPDF); scans and images are read by Qwen3-VL-4B-Instruct (Apache-2.0, local weights, greedy decoding, so the same page always gives the same text), one pass per page giving the text and its tables written as HTML [R26]. Decided by the user on 2026-11-03: nothing from Baidu (PaddleOCR, PaddlePaddle, nor MinerU or RapidOCR, which bundle PaddleOCR models), internationally recognised models where possible. Recognition quality is spot-checked on this project's documents with OmniDocBench's methodology (page and element level [R22]) and recorded in the evaluation notes.
- Index units: pages (text blocks in reading order) and table cells (table number, row header, column header, value). Cell indexing targets bank statements and financial statements: the agent can ask "amount received in June 2024" without reading the whole page. Tables of a PDF with a text layer come from PyMuPDF; tables of a scan come from the HTML tables the recognition model writes.
- OCR text is a **derivative**, not a source: the source remains "document + page"; returns are marked `derived: ocr` with a confidence grade (high / medium / low, no score). The agent may still Read the page image through the host. Grounding (§10 `ground`) allows approximate matching for documents and returns the matched span, for review to judge.
- Not done: multi-vector retrieval over page images (ColPali and the like [R24]). A case has a dozen or so documents; the text index suffices; revisit when cases reach hundreds of pages.

## 7. Query understanding and corrective retrieval

All by program; the service calls no model.

1. **Routing**: recognise ids and article numbers first (exact channel); then extract filter words: jurisdictions (Chinese and English names and codes), cand / branch / key@jur, slot, date, scenario, document name; filter words alone give a structured lookup; otherwise hybrid retrieval with reranking. This is Adaptive-RAG's idea of choosing the path by question complexity [R21], done with rules instead of a classifier.
2. **Batch**: `search` accepts several queries and returns each one's hits in one call, saving turns.
3. **Expansion**: the term dictionary expands between Chinese and English (受益所有人 / beneficial owner, 常设机构 / permanent establishment and so on); a word that finds nothing is split into shorter words and listed under relaxed (tax-db's `find` already does this).
4. **Correction**: when hits are empty or all filtered out, the program relaxes in a fixed order: drop the weakest filter → widen the language → split words, at most twice; still empty returns `not_found` with `tried`, never a guess. CRAG uses an evaluator to judge retrieval quality and correct [R21]; this service uses program rules, because a model's own judgment of whether its context suffices is unreliable [I22].
5. **Not done**: model query rewriting, HyDE-style generated pseudo-documents. The agent may rephrase on its own.

## 8. Context budget and de-duplication

- A return is at most 4,000 characters by default and a card at most 600; the rest comes through `cursor`; `get` pages at 6,000 characters with `total_chars` and `offset`.
- **Session de-duplication**: the service process lives exactly as long as one `claude -p`; it remembers the ids already returned in the session, and a repeat hit returns only the id and "returned at call n" unless `full=true`. This is the server-side form of tool-result clearing, which Anthropic lists as the lightest and safest compaction [R19].
- The prefetch pack is at most about 9,000 tokens (36,000 characters; beyond that whole sections from the end are left out and named, never cut in the middle); the inline inventory in the task text at most about 1,500.
- Basis: across 18 models performance falls consistently with input length, distractors worsen it, and a focused input of about 300 tokens beats the full 113 thousand tokens across the board [R18]; comparing long context with retrieval, chunk retrieval falls behind while summary-based retrieval comes close to long context [R20], so the pack must be a good summary, not a pile of originals. Anthropic suggests skipping retrieval below 200 thousand tokens [R4]: the law library at 24.2 million characters and the products at 47 MB are far above that line.

## 9. Prefetch pack

Generated by the program when the orchestrator starts a node, written to `cases/<case>/report/<run_id>/pack/<node>.md`; the task text gives the path and inlines the file inventory (the output of `map`). Every item in a pack carries its id, so the agent cites it as ref without fetching again.

| Node | Contents |
|---|---|
| analysis | Case digest (entities, holdings, amount, dates, from facts.json); handoff.md in full; structure names and the five tables (the frame of today's `sections.py`); judgment points with the first structure under either answer; every hop of the first structure with its rules and cite_ids; the unit text of those cited provisions (each cut at the unit cap); open items; file inventory |
| review_draft / review_final | The digest part of the above, plus the provenance check of every figure in this round's draft (§10 `cite_check`) |
| review_intake | List of fact keys, list of sources, parsing status of the documents (which pages have a text layer, which are OCR), the change diff |
| front | Parsing digest of the uploaded documents (each: pages, scanned or not, tables found), list of fact keys |
| polish | No pack; reads only the draft and the sources table |

## 10. Tool interface

Service name `tax-read-<identity>`, one process per identity, bound to identity and path permissions like tax-case-<identity>; the permission rules share one module with `guard_hook.py` (`agent/tools/access.py`) so they are not maintained twice: no reading of other agents' notes, of earlier runs' products and reports (the revised-edition exception per orchestration spec §9), or of log/.

| Tool | Parameters → return |
|---|---|
| `map` | case_id → the folders and files this identity may read: path, size, one-line meaning (a fixed table in the program), the current run_id, a products digest (structures, branches, judgment points). Replaces Glob |
| `search` | queries[] (or query), scope ∈ {law, products, case, all}, filters {jur, as_of, run_id, cand, branch, point, doc, lang, slot}, k = 8, max_chars → per query a hit list: id, scope, type, title / label, verbatim fragment or card, rank, channels, validity, language, other_lang, parent; plus tried, relaxed, not_found |
| `get` | id, offset, max_chars → the whole record or clause, verbatim; with total_chars |
| `expand` | id, kinds[], depth ≤ 2, k → neighbour cards grouped by edge kind |
| `ground` | id, quote → match ∈ {exact, approximate, none} and the matched span; approximate allowed for documents |
| `list` | kind, filters, k, cursor → cards of one kind of record: from the library params / absences / treaties / jurisdictions / blocked / decisions / docs; from the products structures / branches / hops / points / scenarios / open_items / requirements / transfers / exposures / penalties / past_payments; from the case file facts / sources / dialogue / documents / pages / cells. Replaces the layers' slicing tools (§5.3) |
| `pack` | case_id, node → the pack's path and the list of its item ids (usually called by the orchestrator; agents may re-fetch) |
| `cite_check` | case_id, run_id → whether every ref of the draft's sources table resolves, whether every figure and citation in the body occurs in the cited fragments, and the list of figures no source covers. For `report_check` and the review agent |

Conventions: text and quote in returns are verbatim; no scores; every call is logged to `cases/_log/read.jsonl` (query, filters, returned ids, characters, time) for evaluation-set mining.

With scope all, `search` returns its hits grouped by material (the first few of the law, the products and the case file, each ranked within its material), not merged into one ranking: the three rankings have no common scale, and having the reranker order their union, tried on 2026-11-03, was unfair to the products and the case file (asked about the HSBC credit, it put a treaty article first). For more of one material, search that scope alone.

## 11. Integration with the four agents

- **Analysis**: read the pack first and `search` for what is missing; cite provisions from the structure's basis record, whose match to the products the rule layer has already checked, and fetch a clause again only to quote it; the task lists what the round's notebooks already hold, which are appended to, not reread whole; the rule layer's requirements returns a summary by default; several questions per `search`; sources-table refs are ids; `map` instead of Glob for paths. The prompt is revised accordingly, removing instructions such as "start from the sections of brief.json" that lead to whole-file reads.
- **Review**: run `cite_check` first and look only at the uncovered figures and mismatched citations it reports; quotes through `ground`.
- **Front**: after an upload, check parsing status in `map`; when extracting facts, `search(scope=case)` over document pages and cells; ground quotes with `ground`. Multimodal reading of page images stays available.
- **Polish**: unchanged.
- **report_check**: adds `cite_check`; leak patterns gain the id formats (`\d{8}-[0-9a-f]{8}:\w+:`, `:unit:`; cite_ids of the form `#\w+` are already covered).
- **Orchestrator**: builds the products index after a run; generates the pack before a node starts; inlines the inventory in the task text.

## 12. Evaluation

In the spirit of `目标.md`: methods are adopted on this project's numbers. Tests run only when the user instructs.

### 12.1 Golden sets

| Set | Query | Gold | Size |
|---|---|---|---|
| L-params | name and quote of param.csv | cite_id | 365 |
| L-rules | the condition text of each rule in rule.csv | cite_ids | 200 |
| L-decisions | the statement of decision.csv | cite_id | 26 |
| L-xlang | the text of a treaty's Chinese clause | the cite_id of the English expression | from same_provision edges |
| P-template | questions generated from templates over structures, judgment points, scenarios and transfers ("the tax of c5 with every point favourable" and so on) | record ids | hundreds per run, program-generated |
| P-hand | hand-written questions (starting from the 5 of the 2026-11-03 model comparison) | record ids | accumulated |
| C-sources | each key of sources.json turned into a question | doc + page | about a hundred per case |
| C-dialogue | a quote | dialogue paragraph number | per case |

Items the agents actually asked (in `read.jsonl`) and later wrote into the sources table are added to P-hand and the C sets from time to time.

### 12.2 Metrics

- Retrieval: Recall@5 / 10 / 20, nDCG@10, MRR, reported per language and per set.
- Grounding: verbatim hit rate of quotes; number of uncovered figures reported by `cite_check`.
- End to end: the analysis node's tool calls, characters read, output tokens and seconds; the review verdict and number of items sent back. The baseline before the change is the table of §0.

### 12.3 Ablations and adoption threshold

Every component has its own switch: header context, dense channel, language balance, graph expansion, reranking, late chunking, sparse weights (model-written explanations join once the whole library is collected; no model comparison, decided by the user on 2026-11-03). A component is adopted when nDCG@10 or Recall@10 improves on the development set and does not fall on the test set; reranking must also keep single-call latency under 1 second on the GPU. Results are recorded in `agent/retrieval_eval.md` (English).

## 13. Implementation and dependencies

- **Environment**: conda env tax (Python 3.11, torch 2.11 + CUDA 12.8 available, sentence-transformers 6.1, transformers 5.20, SQLite 3.53 with FTS5, pypdf); GPU RTX 5070 Ti 12 GB. BGE-M3 weights are cached (about 4.3 GB in two formats). To install: Qwen3-Reranker-0.6B (about 1.2 GB); Qwen3-VL-4B-Instruct (about 8.3 GB); pdfplumber. No vector database: about 30 thousand law units and under 10 thousand product records per run, brute-force cosine in numpy suffices (the judgment of round-I synthesis §5 stands).
- **Storage**: `database/index/` (index.sqlite: unit, edge, term, unit_fts; vec.npy cached by text hash); `cases/<case>/intake/products/<run_id>/index/` (records.sqlite with fts; optional vec.npy); `cases/<case>/intake/index/` (facts, dialogue, pages, cells; OCR cache by sha256). An index records the engine hash, model name and build time; a products index is immutable with its run.
- **Code**: `agent/tools/read_index.py` (building the three indexes), `agent/tools/read_server.py` (MCP), `agent/tools/access.py` (permissions, shared with the guard), `agent/tools/pack.py` (prefetch pack; absorbs the frame part of `sections.py`), `agent/tools/read_eval.py` (evaluation). The law part migrates from the archived graph.py / search.py, keeping the table structure.
- **Order** (decided by the user on 2026-11-03: built in one go, in dependency order, without stopping in between):
  1. access.py (permissions shared by the guard and retrieval); products and case-file indexes; read_server's map / search / list / get / expand / ground / pack / cite_check, covering every old use in the mapping table of §5.3; mount slimming; prefetch packs; the orchestrator builds the index after a run, issues the pack before a node and inlines the inventory in the task; report_check calls cite_check.
  2. Law index (units, explicit edges, FTS5, BGE-M3, language-balanced fusion, PPR expansion, time); term dictionary; the evaluation tool and the L, P and C sets.
  3. Qwen3-Reranker reranking; document parsing (text layer, Qwen3-VL-4B-Instruct) with page and cell indexes; late-chunking experiment.
  4. Run the evaluation and set each switch per §12.3; update the prompts; one end-to-end run on CASE-20261102-a032c0 compared with the baseline of §0.
  - Evaluation: the user allowed on 2026-11-03 that the retrieval evaluation of §12 runs during this build without asking each time.

## 14. Check against `目标.md`

| Item | Requirement | This specification |
|---|---|---|
| §4.1 item 1 | No probabilities or scores | Returns rank and channels, no scores; OCR confidence only as a grade |
| §4.3 item 8 | The first three layers are shovels; the agent is the only author | The service only slices, finds, fetches and checks; it writes and judges nothing; no model call inside the service |
| §4.3 item 9 | Every figure traces to a rule-layer output and a provision; the LLM does no tax arithmetic; same input, same product; nothing from the web in products | Product records copy values; provisions verbatim; the index holds nothing from the web; the index is deterministic and records engine hash and model name |
| §4.3 item 11 | Abilities fully open, only deliverables constrained | Tools are added, none removed; Read / Glob stay; the guard is unchanged; the budget can be exhausted with cursor |
| §4.4 item 14 | No system identifiers in client text | Ids are internal refs; polish removes them; report_check's leak patterns gain the id formats |
| §4.5 | Specs in Chinese with an English copy; the AI's own text in English | This file + `检索规范.md`; index fields, verbalisations and evaluation records in English; originals untranslated |
| §5 Not done | Verifying the authenticity of the client's documents | Documents are only parsed and indexed; conflicts are listed, not judged, as before |
| Database spec | The library holds only official texts | The index is a derived layer over the library; `header` comes from the original's structure; model-written explanations are off by default (§15) |

No conflict found. Two boundaries for the user to confirm are §15 items 2 and 3.

## 15. The user's decisions (2026-11-03)

| Matter | Decision |
|---|---|
| Embedding model | Local BGE-M3; no comparison. No API models (DashScope and the like): an API upgrade would break "same input, same product" |
| Reranker | Local Qwen3-Reranker-0.6B; no comparison; a switch per material type, off if the evaluation shows harm |
| Model-written explanations at index time | Off; switched on once the whole library is collected (gloss field and cache reserved) |
| Document OCR | Qwen3-VL-4B-Instruct (decided by the user on 2026-11-03: nothing from Baidu, replacing the PaddleOCR-VL first chosen); OCR text marked as derived; quotes grounded with tolerance, the matched span returned for review to judge |
| Mount slimming | Together with the retrieval service (§5.3) |
| Phasing | One go (§13) |
| Evaluation | Run during this build |


## 16. Implementation record (2026-11-03)

| Part | File | Measured |
|---|---|---|
| Text helpers | `agent/tools/textutil.py` | Unit splitting, FTS tokens (CJK, kana and Thai bigrams; a figure also in its plain form, so 14,000,000.00 is also 14000000), verbatim and tolerant anchoring |
| Permissions | `agent/tools/access.py` | Shared by the guard hook and the retrieval service; the six guard cases give the same result as before |
| Law index | `agent/tools/law_index.py` → `database/index/` | 18,411 clauses, 67,901 units; explicit edges: cites 20,010 (3,298 across documents: e.g. article 80 of the EIT regulations to article 24 of the EIT Law, the Japanese Special Taxation Measures Act to the Income Tax and Corporation Tax Acts; "法第X条" in a Japanese order to its parent act), contains 12,081, same_provision 1,765, rule / param / decision cites 734, co_cited 257. Built in 8 s; BGE-M3 vectors at fp16 on an RTX 5070 Ti in about 4 minutes, cached by text hash, 0 s on rebuild |
| Product and case indexes | `agent/tools/read_index.py` | One run of this case: 1,224 records, 3,613 edges, 0.3 s; the case file 409 records |
| Document parsing | `agent/tools/doc_parse.py` | PDFs with a text layer through PyMuPDF; scans and images through Qwen3-VL-4B-Instruct (transformers' own implementation, SDPA, bf16, pages capped at 1.6 megapixels, greedy decoding), text and HTML tables in one pass. The 7 scanned images in 2 min 52 s; tables split correctly by column (e.g. the withdrawal, deposit and balance columns of the HSBC statement, the 11 rows of the 2024 tax certificate), case-file cells from 173 to 227; when the GPU has less than 10.5 GB free, Qwen3-VL-2B-Instruct (also Apache-2.0) is used and the model is recorded in the cache. Needs torchvision 0.26 (cu128). The PaddleOCR-VL tried first was removed at the user's request, with its output |
| Reranking | `agent/tools/rerank.py` | Qwen3-Reranker-0.6B at fp16; only the order is used, no score leaves it |
| Retrieval service | `agent/tools/read_core.py`, `read_server.py` | Tools map / search / list / get / expand / ground / pack / cite_check; a law query takes about 1 s once warm; a real analysis-agent session did map, search and list in 4 turns and 32 s |
| Prefetch pack | `agent/tools/pack.py` | Absorbs the frame of `sections.py` (structure names and the five tables) |
| Evaluation | `agent/tools/read_eval.py` → `agent/retrieval_eval.md`, `agent/retrieval_settings.json` | Run on 2026-11-03 (120 sampled per law set, half development, half test). Mean change of nDCG@10 / R@10 on the test split: dense +0.226 / +0.242 (the cross-language set from 0 to 0.87), language balance +0.016 / +0.071, graph expansion +0.007 / +0.033, all on; law reranking −0.004 / −0.021 and about 1.2 s more per query, off (0.153 → 0.252 on the params set, but the 10-item decisions set fell a lot; not adopted under the equal-weight rule fixed beforehand, and the rule was not changed afterwards); products reranking +0.108 / +0.294 and case-file reranking +0.046 / 0, on |
| Mounts | `.mcp.json`, `agent/tools/make_agents.py` | Analysis, review: tax-case, tax-read, tax-rule, tax-opt-calc (evaluate and fx only); front: tax-case, tax-read, tax-rule, tax-opt-front; polish unchanged |
| Orchestration | `agent/tools/orchestrate.py` | Builds the products index after a run; OCR before the intake review; before review_intake, analysis, review_draft and review_final it writes the pack and names the pack and the file list in the task |
| Delivery check | `agent/tools/case_server.py` report_check | The draft goes through cite_check: an unresolvable ref and a body figure no source row states are problems; tried on an old draft: every real figure covered, the two false figures planted were caught; leak patterns gained the record id formats |

## 17. Literature

The 21 papers of round I (I1 to I22, archived under `archive/old-model-2026-10-31/literature/notes/`, synthesis in `I_综合.md`) remain the basis of the law-library part and are not repeated. Below are the sources consulted on 2026-11-03, each with the finding used and where; figures marked "second-hand" come from others' reports and were not checked against the original.

| Id | Source | Finding | Use |
|---|---|---|---|
| R1 | Zhang et al., 2025, Qwen3 Embedding: Advancing Text Embedding and Reranking Through Foundation Models, arXiv:2506.05176 v3 | MTEB multilingual: 0.6B 64.33, 4B 69.45, 8B 70.58, BGE-M3 59.56; CMTEB: 0.6B 66.33, 4B 72.26; reranking MMTEB-R: Qwen3-Reranker-0.6B 66.36, 4B 72.74, bge-reranker-v2-m3 58.36; CMTEB-R 71.31 / 75.94 vs 72.16; Apache 2.0 | §4.2 candidate models |
| R2 | Chen et al., 2024, BGE M3-Embedding, arXiv:2402.03216 (note I4) | Dense, sparse and multi-vector in one; 8,192 tokens; 100+ languages | §4.2 default embedding |
| R3 | BAAI/bge-reranker-v2-m3 model card | 0.6B, multilingual, sigmoid normalisation, Apache 2.0 | §4.2 default reranker |
| R4 | Anthropic, 2024-09, Introducing Contextual Retrieval | 50 to 100 token model-written context prepended per chunk; top-20 failure rate 5.7% → 3.7% (contextual embeddings) → 2.9% (plus contextual BM25) → 1.9% (plus reranking); 20 chunks best; under 200k tokens skip retrieval | §4.1 basis of contextualisation and the option; §8 |
| R5 | Günther et al., 2024/2025, Late Chunking, arXiv:2409.04701 v3 | Encode whole then pool per chunk; no training; needs a long-context embedding model | §4.2 optional experiment |
| R6 | Singh et al., 2026, StrucChunk: Structure-Aware Retrieval for Legal Document RAG, arXiv:2610.26313 | Cutting legal documents at provision boundaries and resolving cross-references: boundary precision 100% vs 7.7%, cross-references preserved 97.6% vs 0%, Char-Recall@8 48.18 vs 23.59; BM25 + BGE-M3 + RRF | §4.1 structural splitting; §4.2 channel set |
| R7 | Shaukat et al., 2026, A Systematic Investigation of Document Chunking Strategies and Embedding Sensitivity, arXiv:2603.06976 | 36 methods, 6 domains, 5 models: structure-preserving beats fixed-length; paragraph grouping best for law (nDCG@5 0.459 vs < 0.244 for fixed); chunking and large embeddings complementary | §4.1 |
| R8 | Bhat et al., 2025, Rethinking Chunk Size for Long-Document Retrieval, arXiv:2505.21700 | 64 to 128 tokens for factual, 512 to 1,024 for broad context; model-dependent | §4.1 small units + parent on demand |
| R9 | Qu, Tu, Bao, 2024, Is Semantic Chunking Worth the Computational Cost?, arXiv:2410.13070 | The cost of semantic chunking is not repaid by consistent gains | §4.1 no semantic chunking |
| R10 | Pipitone, Alami, 2024, LegalBench-RAG, arXiv:2408.10343 | 6,858 QA pairs, 79M characters, contract corpora; second-hand: recursive chunking without reranker best, a general reranker pushed Recall@64 from 61.06 to 47.54 | §4.2 reranking must pass evaluation |
| R11 | Reuter et al., 2025, Towards Reliable Retrieval in RAG Systems for Large Legal Datasets, NLLP 2025 | Names Document-Level Retrieval Mismatch (DRM); a document-level summary on each chunk clearly reduces DRM and raises precision and recall; a generic summary beats an expert-targeted one; adding BM25 helps DRM slightly but lowers in-document precision (Table 2: keyword weight 0 → 75%, DRM 19.29 → 18.18, precision 11.03 → 8.23); best chunk 500 characters + 150-character summary | §4.1 header context; §12 evaluate "right document" and "right clause" separately |
| R12 | Gutiérrez et al., 2025, From RAG to Memory (HippoRAG 2), arXiv:2502.14802, ICML 2025 | Deeper passage integration on HippoRAG's personalized PageRank; 7% over the best embedding model on associative-memory tasks | §4.2 PPR expansion |
| R13 | Xiang et al., 2025/2026, When to use Graphs in RAG, arXiv:2506.05690 v3 | GraphRAG-Bench, 7 graph systems vs plain RAG (with reranking): plain RAG equal or better on simple fact retrieval; graphs win on complex reasoning and summarisation; graph prompts up to about 40k tokens, adding noise | §4.2, §5.2 graph as a supplementary channel only |
| R14 | 2026, Do We Still Need GraphRAG? Benchmarking RAG and GraphRAG for Agentic Search Systems, arXiv:2604.09666 | Agentic search narrows the gap between plain and graph RAG substantially; GraphRAG keeps an edge on complex multi-hop; offline cost must be amortised | §5.2 |
| R15 | Ongris et al., 2025, Benchmarking KG-based RAG Systems: A Case Study of Legal Documents, RAGE-KG @ ISWC 2025 | On legal QA, hybrid systems (LightRAG Mix, LlamaIndex Hybrid) beat graph-only ones; graph-only loses textual semantics | §4.2 |
| R16 | Chen et al., 2024, TableRAG: Million-Token Table Understanding, arXiv:2410.04739, NeurIPS 2024 | Query expansion + schema retrieval + cell retrieval; much shorter prompts | §5.2 hierarchical return; §6.2 cell index |
| R17 | Li et al., 2024, StructRAG, arXiv:2410.08815 | Choose the best structure type for the task at inference and restructure the information | §5.2 |
| R18 | Hong, Troynikov, Huber, 2025-07, Context Rot (Chroma technical report) | 18 models: performance falls consistently with input length; a single distractor already hurts; a focused input of about 300 tokens beats 113k tokens across the board | §0, §8 budget |
| R19 | Anthropic, 2025-09, Effective context engineering for AI agents | Hybrid of prefetch and just-in-time retrieval; tools should return token-efficient information; bloated tool sets are a common failure; tool-result clearing is the lightest compaction; sub-agents return condensed summaries; structured note-taking | §3, §5.3, §8, §11 |
| R20 | Li et al., 2024/2025, Long Context vs. RAG for LLMs: An Evaluation and Revisits, arXiv:2501.01880 | Long context ahead on QA overall; summary-based retrieval close to long context, chunk-based behind; RAG ahead on dialogue and general questions | §8, §9 the pack must be a summary |
| R21 | Singh et al., 2025/2026, Agentic Retrieval-Augmented Generation: A Survey, arXiv:2501.09136 v4; with Self-RAG (arXiv:2310.11511), CRAG (arXiv:2401.15884), Adaptive-RAG (arXiv:2403.14403) | Self-reflective, corrective and complexity-adaptive mechanisms | §7 the deterministic parts implemented as program rules |
| R22 | Ouyang et al., 2024/2025, OmniDocBench, arXiv:2412.07626, CVPR 2025 | Document-parsing benchmark: 9 sources, 19 layout categories, page- and element-level evaluation | §6.2 evaluation method |
| R23 | 2025, PaddleOCR-VL, arXiv:2510.14528 v4 | 0.9B, 109 languages, claims state of the art in page- and element-level parsing | First chosen as OCR; replaced on 2026-11-03 at the user's request (nothing from Baidu) |
| R26 | Qwen Team, 2025-11, Qwen3-VL Technical Report, arXiv:2511.21631 | Dense 2B / 4B / 8B / 32B and two MoE models; §5.4 of the report evaluates OCR and document parsing on OmniDocBench, OCRBench and CC-OCR; the 4B model is Apache-2.0, about 3.9 million downloads on Hugging Face | §6.2 reading scans |
| R24 | Faysse et al., 2024/2025, ColPali, arXiv:2407.01449, ICLR 2025 | Multi-vector retrieval over page images, ViDoRe benchmark | §6.2 not done for now |
| R25 | Sarthi et al., 2024, RAPTOR, arXiv:2401.18059, ICLR 2024 | Recursive summary tree; +20% absolute on QuALITY | Not adopted: generated summaries cannot be checked item by item (as round-I synthesis §5) |
