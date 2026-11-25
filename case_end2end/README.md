# case_end2end: end-to-end case CASE-001, a Mainland subsidiary paying a dividend to its Hong Kong holding company

One case, mixing real files and simulated documents, for running the end-to-end flow from start to finish (intake, extraction, review, evaluation and questions, strategy, report, and the assistant and checks). The companies, people, numbers and amounts are all fictitious; the official forms, guidance and treaty texts under `documents/real/` are real files (source URLs in `documents/manifest.csv`).

## Files

| File | Content |
|---|---|
| `prompt.md` | The transaction background the client filled in on the intake page, in the original Chinese with an English transcription: the parties, the holdings, the dividend to be paid, the history, the attachments. Background only, no questions: the system analyses by itself and does not lead the client to ask |
| `documents/S01–S15` | 15 simulated documents (9 PDF, 7 PNG): the payer's business licence, registration record, articles extract, shareholders' resolution, corporate income tax return extract, the 2024 remittance slip and tax payment certificate; the recipient's certificate of incorporation, annual return, board minutes, audited accounts extract, certificate of resident status, bank statement; the group chart; the Singapore parent's ACRA record; the company secretary's invoice |
| `documents/real/R01–R05` | Real files: the information report form (annex to SAT Announcement 2019 No. 35), form IR1313A, DIPN 44, SAT Announcement 2018 No. 9 (beneficial ownership), the full text of the Mainland–Hong Kong arrangement |
| `documents/manifest.csv` | For each file: real or simulated, format, which party it belongs to, what it proves, which variables it supports |
| `facts.json` | The expected extraction: rule-layer variable → value → source file and sentence; the expected answers of the predicates and their basis; the expected question list and withholding range |
| `expected/` | The rule layer's output on the facts of this case: `eval_cn-hk_as_is.*` (as is, bo, parent_bo and ppt unanswered), `eval_cn-hk_bo_yes_ppt_no.txt`, `eval_cn-hk_bo_no.txt` (both routes denied), `eval_cn-hk_safe_harbour_parent.txt` (the parent's safe-harbour route), `judgment_points_cn-hk.json` (judgment points: question, factor provisions, current facts, the range under each answer), `eval_cn-sg_alternative_plan.txt` (the alternative of a direct holding by the Singapore company), `eval_hk-sg_onward.txt` (the money paid on from Hong Kong to Singapore), `trace_cn-hk_as_is.txt` (trace-back check, 8 items all PASS) |

## The case

- **Payer**: Shenzhen Chenguang Precision Manufacturing Co., Ltd., a Sino-foreign joint venture (a foreign-invested enterprise), registered capital RMB 50 million, taxable income for 2025 RMB 46 million, tax paid at 25% RMB 11.5 million. Shareholders: Brightpeak Holdings (HK) Limited, Hong Kong, 70% (acquired 2019-06-30, held since) and Shenzhen Chenhui Investment Partnership, 30%.
- **Dividend**: on 2026-03-20 the shareholders resolved to distribute RMB 20 million of the 2025 profit; the Hong Kong shareholder receives RMB 14 million, payable before 2026-04-30.
- **Recipient**: Brightpeak Holdings (HK) Limited, incorporated in Hong Kong in 2019, a pure holding company with no employees and the company secretary's address as its registered address; two directors, one in Singapore and one in Hong Kong; board meetings held in Hong Kong (the chairman by video); it holds a Hong Kong certificate of resident status for 2025 and has applied for 2026. Its sole shareholder is Brightpeak Asia Pte. Ltd., Singapore (3 employees, Singapore tax resident), held in turn by Mr TAN Wei Liang, a Singapore resident. The Singapore parent wants the money paid on once it reaches Hong Kong.
- **History**: in 2024 the 2023 dividend of RMB 8.4 million was paid; on the Hong Kong shareholder's part RMB 840,000 was withheld at 10%, no treaty benefit was claimed, and the money went to an HSBC account in Hong Kong.

## What the rule layer should give

With the facts complete (`facts.json`) the two predicates bo and ppt are still unknown:

| Cell | Result |
|---|---|
| cn\|company\|outbound_wht\|hk | range [5, 10], pending group `(cn-hk.outbound_wht.cap_5, {bo})`; cap_10 equals the statutory 10%, so it is not asked |
| cn\|company\|anti_abuse\|hk | ppt pending; flipping it moves the floor from 5 to 10, so it is recorded |
| hk\|company\|inbound\|cn | 0: under FSIE received in Hong Kong but the participation exemption is met (70% ≥ 5%, 82 months ≥ 12, Mainland rate 25% ≥ 15, profits taxed); the economic substance route answers no, the main purpose rule answers no |
| hk\|company\|final\|* | of no practical effect on this dividend (included at 0); the two-tier rate is pending because the year's assessable profits are unknown |

The question list should ask two things only: beneficial ownership (with the factors of Article 2 of Announcement 2018 No. 9 and the relevant passages of S08, S09, S10 and S15) and the principal purpose test (with Article 6 of the fifth protocol). Answering bo=yes and ppt=no gives 5% (RMB 700,000); bo=no gives 10% (RMB 1.4 million).

The alternatives (`expected/eval_cn-sg_alternative_plan.txt`, `eval_hk-sg_onward.txt`): a direct holding by the Singapore company is also [5, 10], and on the receiving side the exemption conditions of s13(8) are met (source rate 25%); but when, as things stand, the money is paid on from Hong Kong to Singapore, Hong Kong withholds nothing, yet the Hong Kong dividend itself was not taxed in Hong Kong, so the "subject to tax" condition of Singapore s13(9)(a) fails and the RMB 14 million is included at 100% and taxed at 17%. This is one of the planning points of the case. The one-off cost of the restructuring itself (indirect transfer, stamp duty) is outside the dividend's scope.

The RMB 840,000 withheld at 10% in 2024: Article 10 of SAT Announcement 2019 No. 35 (`cn.sta.2019-35#10` in the library) allows a refund of the **overpaid part** within the period of the Tax Collection and Administration Law: the difference between 5% and 10% on the Hong Kong shareholder's RMB 5.88 million, RMB 294,000, on condition that the 5% conditions were also met in 2024; not the whole RMB 840,000. The rule layer does not model the refund procedure; the report cites the article. The system should find this in the background on its own; the client did not ask.

2026-10-31 addition: the rule layer writes the beneficial-ownership safe harbour of Announcement 2018 No. 9 as a conditional rule (D-cn-5). Here the Singapore parent holds 100% for more than 12 months and the China–Singapore treaty also gives 5%, so 5% has two routes: the Hong Kong company qualifies on the factors itself (bo), or the parent is the beneficial owner (parent_bo). `expected/judgment_points_cn-hk.json` and `eval_cn-hk_safe_harbour_parent.txt` cover the two routes. The intention to pass the dividend on (passes_on_within_12m) is carried as a factor, not as a condition.

2026-10-31 second addition: after the rule layer's second revision the cn→hk files of `expected/` were regenerated (same input: `--facts` is the payment and payee facts of facts.json flattened, `--answers gaar=no;substance=no;fsie_mpr=no` plus each variant's bo / parent_bo / ppt). Values, states and pending items are exactly as before; the only change is that `rules_applied` now lists only the rules that decide that side's value (the floor side of the Hong Kong final cell lists only the 8.25% two-tier rule, no longer also the 16.5% standard rate); the trace-back check still passes all 8 items. The penalty cells the rule layer added (`cn|all|penalty|*`, `hk|all|penalty|*`) are not in expected for this case; the optimization layer takes them as needed.

## Regenerating

The simulated documents were generated with PyMuPDF by `gen_case.py` in a session scratchpad (system fonts STSong, STHeiti, STKaiti; font subsets embedded). `expected/` is generated by `rule/tools/eval.py --flow cn hk company --date 2026-04-30 --facts … --answers substance=no;fsie_mpr=no;gaar=no` and `rule/tools/trace.py --items`; after a change to the rule layer, run them again and compare.
