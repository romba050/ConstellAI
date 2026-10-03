# Validation report — 2026-10-03

Scope: isolated Buffalo Atlas prototype on the preserved MEDR5 baseline. Automated prototype checks, source inspection and browser testing do not constitute clinical validation.

| Check | Result | Evidence / boundary |
| --- | --- | --- |
| Unit/API suite | PASS, 88/88 | Four direction quadrants, unknown direction/evidence, signed coverage, uncertainty, spillover, redundancy, safety separation, graph projection/deletion/reversal, source/provenance integrity, priors, normalization, benchmark leakage/abstention, Responses transport mocks, HTTP routes/exports/security boundaries |
| Production frontend build | PASS | Fresh npm ci added 11 packages; fresh Vite 5.4.21 build passed, four modules; build output ignored in Git |
| Deterministic `/demo` | PASS | Cached Angelman graph and hypotheses; offline network-failure tests |
| Browser acceptance | PASS | Search → visible graph → actual causal-edge dot click/citation → cluster/asset source → counterexample → comparisons → direction/spillover → retained biology → patient next action → falsifier → acceleration → OpenAI disclosure → closing |
| Patient resources / citations | PASS | Official groups, primary study/model source, dated registered study; no trial eligibility inferred |
| Real text export | PASS | Cited preview, HTTP attachment tests, actual browser save to MEDR5-Atlas-angelman-collaboration-brief.txt |
| Browser console | PASS | No error/warn entries in final browser session |
| Responsive layout | PASS | Desktop at natural app viewport; mobile 390×844: document width 375 with scrollbar, no page horizontal overflow; graph/table scroll remain contained |
| Live OpenAI API | NOT VERIFIED | Server-side key absent. Honest UI configuration state; strict adapter success/failure/span rejection tested with mocks |
| Local model endpoint | NOT VERIFIED | Optional adapter tested via mocks/unavailability; no local model inference claimed |
| Source-only fresh checkout | PASS | Index-exported source copy: 88/88 tests; /demo, actual graph-edge click and .63 priority verified in browser with dist absent; no runtime packages needed |
| Original source preservation | PASS | 30 additive staged files only; original backend/frontend diff against pre-hackathon-medr5 empty; dependencies/dist/bytecode/key paths excluded |

## Benchmark results

Four typed known positive observations: three preclinical mechanism observations, one clinical symptom RCT. Relation-only ablation: Hit@1 .250, Hit@3 .500, MRR .375, 2/4 abstentions. This retains source-derived mechanism features and leaks information, so it is only diagnostic. Source-disjoint: Hit@1/Hit@3/MRR zero, 4/4 abstentions. Clinical fold abstains; no clinical link recovery demonstrated. Full folds and stratification: BENCHMARK_REPORT.md.

## Source resolution

Hero primary identifiers checked against indexed/primary sources: PMID 20876107, 25884337, 22190039, 25470045, 23995680, 28436452 and 38977672. Source URLs and regulatory label resolve; some primary sites may impose rate limits or anti-bot interstitials. Trial registry status is from the official v2 snapshot, not the static web page shell. Internal graph citations all resolve to the 25-record registry with contextual metadata. Broad GARD names are not revalidated mechanisms. Contradiction review is not systematic.

## Known limits and submission gates

Four curated pilots; one deep Angelman hero. Not all 5,000+ diseases, every variant, dose, exposure or pathway. PWS is a shared-model neighbor, not an equivalent monogenic mechanism or drug recipient. Model access/collaboration unverified. No clinical validation, efficacy, combination safety or measured 10x acceleration. The 90–120-second route is a scripted pitch target; no human timed usability study performed. OpenAI live proof and exact organizer eligibility/PDF review remain submission gates.

Fresh-checkout verification exposed a Windows connection-reset race on early cross-origin POST rejection. The handler now drains the bounded body before returning 403. Both final working-copy and source-only suites pass 88/88 after that repair. Final builds: index 0.53 kB, CSS 22.22 kB, JS 40.46 kB.
