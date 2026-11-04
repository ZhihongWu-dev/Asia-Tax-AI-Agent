# Project goals

English copy of `目标.md`; where the two differ, the Chinese version prevails. Change one, change the other.

Written 2026-11-02 to prevent goal drift. Before changing a design, writing a spec or proposing an improvement, check it against this file; a change that conflicts with it goes to the user first.

## 1. What the supervisor asked for

### 1.1 The supervisor's email (forwarded by the user on 2026-10-22, verbatim)

> 1) Collect all tax documents from Asia (all countries, all relevant tax documents, usually: double tax agreement, CFC, exit tax, corporate tax, personal/individual tax)
> 2) Use the tax documents as input
> 3) Use the agent/algorithm as tool in order to ask for missing data and to optimize the case – since you have little time, you should maybe focus only on dividend tax (cross-border), but for corporates and for individuals. For solving an optimization problem, you basically need the input first, so the database of all pdf tax documents – read them out with AI, extract relevant data from the input needed for your dividend case.
> 4) your agent/algorithm should in the end use the information given and the variables from the database to show the user how he/she could improve the company structure (e.g. move the company from China to Singapore, or try to route the dividends through a singapore company instead of a Thai company, or route the dividends through singapore and indonesia instead of two other countries. Therefore, you need the input variables first.
> 5) results: in the end, the agent or your tool should prepare like a recommendation briefing. Outlining what is wrong with the current situation and what can be done or changed to improve the tax burden. Usually, having the input database, you should know exactly the connection between the countries.

### 1.2 Meeting notes

The original was not archived; the points below come from the session records of 2026-10-21 to 10-31.

- The focus is cross-border dividend optimisation in Asia, for companies and for individuals.
- The deliverable is a recommendation briefing of about 5 pages in six parts: Current State, Alternatives, Optimal, Tax Comparison between the current state and the alternatives, Requirements for the optimal structure to hold, and Implementation from the current state to the optimal one.
- A complete, runnable demo.
- The supervisor's European version, the three figures, is his own reference and is not to be copied.
- The modelling on the supervisor's slide: a log transform of each hop's rate, w = −ln(1 − t), and a Dijkstra-type shortest path that guarantees the optimum.

## 2. The goal in one sentence

The client states the background of the holdings and of one cross-border dividend and uploads the documents; from the official law in the library the system computes the tax of every feasible structure under every outcome of the judgment points and writes an advisor-grade recommendation report: what is wrong with the current state, which structure to move to, how the tax changes, what must hold, how to get there step by step, which points are uncertain and what the client should go and confirm. When the client brings the results back, the case runs again.

## 3. Scope

| Item | Scope |
|---|---|
| Taxes | Income tax: outbound withholding on dividends, taxation and exemption at the recipient, individual dividend tax, residence, CFC, anti-abuse; income tax and stamp duty on the share transfers a restructuring needs, as one-off costs |
| Persons | Companies and individuals |
| Jurisdictions | Built: Mainland China, Hong Kong, Singapore, Japan, Thailand. The supervisor asked for all of Asia; the library grows by the collection task sheet |
| Timing | Planning before the payment; past dividends only for the tax that can be recovered and the back-tax risk |

## 4. Settled design principles

### 4.1 Objective and comparison

1. One objective: the lowest tax per payment, that is, the largest saving per payment against the baseline (the route the money takes today to the destination the client wants). No probabilities, scores or preference weights; not multi-objective. The ranking uses the favourable side, since tax planning rests on the client's conditions, and the conditions the favourable side relies on are listed as premises; the report gives the single figure under the favourable answers, not the unfavourable side, and does not pre-write the design for a denied point; when the client brings back an adverse result, item 6 recomputes (decided by the user on 2026-11-02 and 2026-11-04). The one-off cost counts only the taxes the moves trigger at once; a tax that arises only through the tax office's discretion is an assumption. It is not a second objective: it orders structures of equal tax only, through the payback in payments (one-off cost ÷ saving per payment, not discounted); no holding period is asked (decided by the user on 2026-11-04). Source: optimization layer spec §0, §4.7.
2. The optimisation is exact: a resource-constrained multi-label shortest path with log-transformed edge weights, checked against exhaustive enumeration on small graphs; no metaheuristics.
3. The optimization layer gives structures, not plans. A plan is a structure plus how to get there, what must hold, the order, the cost, the premises and whom to ask before payment; the analysis agent draws it up, on the structure the optimization layer ranks first, and does not pick another structure. Decided by the user on 2026-11-01; on 2026-11-04 "what to do when a point is denied" was dropped (a denial starts a new round).

### 4.2 Uncertainty

4. No facts are made up for the client. A missing value is a value, not a stop; rules evaluate in three values: MISSING is to be asked, PLAN is a structural condition to be set, DISCRETION is a judgment point.
5. A judgment point has an answer only when the client states the conclusion. Unanswered points become labelled assumption branches; the report argues on the favourable assumptions throughout, declares them once at the start and lists them in Appendix A. An unfavourable answer closes a branch; a favourable answer is evidence only and both outcomes stay. Decided 2026-11-02.
6. The loop: the client goes and confirms or tries out the uncertain points and brings the results back. The front updates the facts and answers, the optimisation layer runs again in full and yields a preview card, and the points the client brings back accumulate in the current round; a new round with a new report starts only when every point that would change the first-ranked structure is answered, the previous edition's recommended structure has failed, or the client needs the report to act on. The new round compares the products of the two rounds; the program decides whether to revise the previous edition or rewrite it in full, and rewrites in full when unsure; figures come only from the current round's products; review comes before delivery. No separate re-planning logic. Amended 2026-11-04 after the trial of orchestration spec §9.
7. Fact gaps the client can fill at once, such as net assets, cost base or holding period, are asked before the handoff; judgment points that only practice can settle go through the loop above.

### 4.3 Layers and trust

8. Four layers: the database holds official originals and passes acceptance; the rule layer structures the law and evaluates in three values; the optimization layer builds the graph, finds structures, expands the scenarios and ranks; the agent layer has the front, analysis, polish and review agents; on top sit the web host and the interface. The first three layers are shovels that compute and do not judge; the agents are the only writers.
9. Every number traces back to a rule-layer output and from there to a clause; the LLM does no tax arithmetic; the same input always gives the same products. What is found on the web stays out of the products; it may go into the report with its source tier.
10. The library takes official originals only; captchas, WAFs and logins are never bypassed; a request is retried at most twice, then one alternative source.
11. The agents have every capability; only the deliverables are constrained, never the process.

### 4.4 Client and report

12. The client only states the background and uploads documents, and asks no questions; the front never writes words for the client, and the host records the client's messages word for word. The front keeps the business boundary: it takes only cross-border dividend structure planning between the jurisdictions of the library; when the client strays too far or asks questions it says so politely, does not answer and asks for the background; the client may choose the jurisdictions to consider, and those of the as-is structure, the destinations and the known entities always stay. Decided by the user on 2026-11-02.
13. The report is for the client, at the standard of a top firm's written opinion, with a body of about 5 pages. Structure: 1 Strategy, 2 Current State, 3 Alternatives, 4 Optimal, 5 Tax Comparison, 6 Requirements, 7 Implementation, Appendix A points to confirm and assumptions, Appendix B legal basis and sources. Parts 2 to 7 are the supervisor's six parts and must not be dropped.
14. Text the client sees carries no system identifiers, file paths, ids or internal ranks.

### 4.5 Language

15. Specs are in Chinese for people, each with an English copy; the Chinese prevails. Everything the AI writes itself is in English. The interface is English by default with a Chinese switch. The report follows the client's language.

## 5. Not done

- Metaheuristics, probabilities, multiple objectives, discounting; valuation, the consideration being the input net assets or appraised value.
- New structures outside the move vocabulary. The vocabulary is data: rows can be added and must pass the checks.
- Verifying that the client's documents are genuine, beyond listing contradictions between them; answering judgment points for the client.

## 6. Known gaps against the supervisor's requests

| Supervisor's request | Current state | Handling |
|---|---|---|
| All countries in Asia | The rule layer covers 5 jurisdictions | Not now; the user decided on 2026-11-02 |
| The example "move the company from China to Singapore" | The paying company is the fixed start; the move vocabulary has no relocation of the operating company | In progress, decided by the user on 2026-11-04: for trading, IP and service companies and individual businesses, whose business can move; totals add the operating level's profit tax, the move vocabulary gains relocating the paying company or an individual, the rule layer adds deemed liquidation and individual emigration, the client supplies the fair value of the assets and where the people and management are |
| Exit tax | Japan's exit tax on individuals (ITA 60-2) is in the rule layer and the one-off cost of a structure with a move is computed from it; Mainland China, Hong Kong, Singapore and Thailand have absence records | Built 2026-11-02 |
| CFC | The included tax is in the total: on the hop where an intermediate company pays a controlling shareholder, and as retention when money stays in the controlled company; Japan credits only the controlled company's own tax, the Mainland down the tiers under art. 24 | Built 2026-11-02; a chain of controlled companies included by the same shareholder hop by hop may be counted twice |

## 7. Change rules

- A new design or improvement is checked against sections 1, 4 and 5 first; a conflict goes to the user.
- When a gap in section 6 is closed, its row is updated.
- This file changes only with the user's consent, Chinese and English together.
