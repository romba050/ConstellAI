# STXBP1 and CPLX1 evidence review

Reviewed on **4 October 2026**. The curated library contains **21 primary or official source records**, a STXBP1 therapeutic demonstration and a CPLX1 evidence-context profile. No candidate is classified as a supported clinical treatment. This is a dated curated snapshot, not a comprehensive or continuously updated literature search.

The native Google Doc **Literature reviews** tab was read separately from **Final**. Its verified foundations now populate mechanisms, assessment inputs, related-disease claims and typed graph relationships. [LITERATURE_REVIEW_TRACEABILITY.md](LITERATURE_REVIEW_TRACEABILITY.md) maps the tab's material statements to implemented, corrected/excluded or deferred coverage.

## Research assessments

| Candidate | Curated interpretation | Computed score / rank / status |
| --- | --- | --- |
| Levetiracetam | A short STXBP1 mouse ECoG study supports symptomatic investigation; human comparative findings differ. No protein repair or therapeutic superiority is established. | 28.25 / 1 / research hypothesis |
| Phenylbutyrate | Selected missense-model protein/function rescue supports research. Human reports primarily concern glycerol phenylbutyrate, with formulation and safety limitations. | 27 / 2 / research hypothesis |
| Compound 13 | Experimental assay comparator with unknown human safety, exposure and interactions. | 5.5 / unranked / insufficient evidence |
| CPLX1 | Reviewed genetics and pathway context are retained; no drug response is transferred from STXBP1. | No candidates or ranks |

All inputs are **curator ordinal judgments**, not published effect sizes, probabilities or a validated clinical prediction. Python computes the disclosed heuristic; evidence and compatibility gates can withhold ranking regardless of score. Differences of a few points have no calibrated therapeutic meaning.

The six positive ratings, in order, are mechanism, variant compatibility, human evidence, preclinical evidence, phenotype and quality:

| Candidate | Six ratings | Positive total | Penalty total |
| --- | --- | --- | --- |
| Phenylbutyrate | 0.90 / 0.50 / 0.25 / 0.80 / 0.65 / 0.60 | 63 | 36 |
| Levetiracetam | 0.45 / 0.45 / 0.45 / 0.40 / 0.75 / 0.60 | 49.75 | 21.50 |
| Compound 13 | 0.90 / 0.50 / unknown / 0.70 / 0.50 / 0.60 | 55.50 | 50 |

Positive weights are 30/15/20/10/10/15. Penalties use the worse of toxicity/organ burden (15), interactions (10), spillover (10) and uncertainty (15). Unknown positive data earns zero credit; unknown risk receives the full penalty. Research and supported thresholds remain 20 and 60. No threshold is calibrated to clinical outcomes.

**Literature-tab correction:** the first curation had no reviewed levetiracetam preclinical source. Kovacevic's primary report contains an acute and five-day Stxbp1+/- mouse spike-wave-discharge experiment. The preclinical input changes from unknown/zero credit to 0.40. This modest judgment reflects a short symptomatic assay in one model, with no demonstrated Munc18-1 correction or human translation. With all other inputs and weights unchanged, the score changes **24.25 → 28.25**, moving levetiracetam above phenylbutyrate. The ranking was allowed to change; the score was not tuned to retain a preferred lead.

Any supplied variant remains unreviewed, including a label resembling a published example. The service returns unknown individual function/compatibility, full variant uncertainty, no best candidate and no ranks. A gene, pathogenicity annotation or inheritance pattern cannot establish individual drug compatibility.

## Verified source record

Each source below has a public URL, review date, scoped description and a short exact excerpt in evidence.json. Claim text elsewhere is curator paraphrase or a disclosed research-design proposal.

| Source ID | Primary or official source | Evidence boundary |
| --- | --- | --- |
| karaca2015 | [2015 family rare-variant report](https://pmc.ncbi.nlm.nih.gov/articles/PMC4824012/), PMID 26539891 | Homozygous CPLX1 nonsense allele in two siblings; genetic evidence, not a drug study. |
| redler2017 | [2017 CPLX1 family report](https://pmc.ncbi.nlm.nih.gov/articles/PMC5520065/), PMID 28422131 | Three affected individuals from two families; no therapy transfer or world case count. |
| saitsu2008 | [Original STXBP1 report](https://pubmed.ncbi.nlm.nih.gov/18469812/), DOI 10.1038/ng.150 | Original early-infantile presentation and protein experiments; not every STXBP1 phenotype. |
| kovacevic2018 | [Allelic series and mouse models](https://pmc.ncbi.nlm.nih.gov/articles/PMC5917748/), PMID 29538625 | Protein instability, model/background limits and levetiracetam ECoG observations. |
| chen2020 | [Haploinsufficient inhibitory-synapse models](https://elifesciences.org/articles/48705), PMID 32073399 | Mouse cortical inhibition; no universal GABA pathway effect or clinical drug response. |
| guiberson2018 | [Chemical-chaperone experiments](https://www.nature.com/articles/s41467-018-06507-4), PMID 30266908 | Selected missense neuronal/worm rescue; no human efficacy test. |
| abramov2021 | [Targeted chaperone experiments](https://link.springer.com/article/10.15252/emmm.202012354), PMID 33332765 | Compound 13 in selected models; clinical safety/exposure unestablished. |
| lammertse2020 | [Homozygous L446F report](https://pmc.ncbi.nlm.nih.gov/articles/PMC7009479/) | Gain-of-function model counterexample to uniform loss of function. |
| wang2022 | [Levetiracetam cohort](https://pubmed.ncbi.nlm.nih.gov/35007884/) | Non-randomized partial-remission association. |
| xian2023 | [Published Brain cohort](https://pmc.ncbi.nlm.nih.gov/articles/PMC10689925/), PMID 38015929 | Did not find superior levetiracetam seizure reduction. |
| barbour2026 | [Parent-interview observations](https://pmc.ncbi.nlm.nih.gov/articles/PMC13405358/), PMID 42447769 | Uncontrolled mixed-gene cohort; serious toxicity reported. |
| ravicti-label | [Glycerol phenylbutyrate label](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=900e7dc0-9afe-4f50-80de-90567bb78519) | Urea-cycle indication, metabolite/organ/interaction risks; not STXBP1 approval. |
| keppra-label | [Levetiracetam label](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=3ca9df05-a506-4ec8-a4fe-320f1219ab21) | SV2A pharmacology, behavioral risks, renal clearance and studied interactions. |
| stxbp1-foundation | [Official research directory](https://www.stxbp1disorders.org/clinicaltrialsandresearch) | Real organization and study links; no access or partnership established. |
| burre-profile | [Jacqueline Burre institutional profile](https://vivo.weill.cornell.edu/display/cwid-jab2058) | Public identity and published coauthorship only; no outreach or availability assumption. |
| capsida2026 | [Sponsor community statement, 11 May 2026](https://capsida.com/stx-community-letter-5-9-2026/) | Reports CAP-002 closure after a participant death; underlying reason unresolved. |
| nct04937062 | [Phenylbutyrate pilot registry](https://clinicaltrials.gov/study/NCT04937062) | Study existence and formulation/design; no efficacy credit from registration. |
| nct06555965 | [STARR registry](https://clinicaltrials.gov/study/NCT06555965) | Observational STXBP1/SYNGAP1 study, not a treatment. |
| nct06625112 | [ESCO registry](https://clinicaltrials.gov/study/NCT06625112) | Observational registry; European STXBP1 Consortium is the named sponsor. |
| nct06983158 | [CAP-002 registry](https://clinicaltrials.gov/study/NCT06983158) | Terminated historical gene-therapy study. |
| nct05462054 | [Capsida natural history registry](https://clinicaltrials.gov/study/NCT05462054) | Withdrawn without enrollment; not a recruiting asset. |

The 2026 interview report includes 18 children, 13 with STXBP1. Pooled outcomes must not become STXBP1-specific efficacy estimates. Preparation identity matters: free 4-PBA, sodium phenylbutyrate and glycerol phenylbutyrate are distinct. The study cannot establish causal developmental improvement.

The supplied Xian PMC10197795 / PMID 37215006 link is a preprint; this library uses the final publication. The earlier 20-child phenylbutyrate pilot referenced by Barbour is a 2024 medRxiv report. It is not promoted to controlled efficacy evidence or evidence of CPLX1 response.

## Mechanistic and human limits retained in the graph

Guiberson's selected missense preparations support instability/coaggregation. Kovacevic found no detectable functional effect when variants were overexpressed on a heterozygous neuronal background. These are different models and limiting findings; neither supports a universal dominant-negative classification. Lammertse's homozygous L446F example further prevents a blanket loss-of-function rule. Mechanism and alignment edges carry this source-backed interpretation limit.

Levetiracetam's Wang and Xian observations remain together in the human-evidence assessment and graph's limiting-claims list. The mouse seizure endpoint does not resolve the human disagreement or show disease modification. Phenylbutyrate's safety findings similarly limit translation without disproving laboratory rescue.

CPLX1 family reports support a genetic and presynaptic context, with a related STXBP1 research bridge. CPLX1 receives **zero candidates**, an explicit abstention and a proposal to establish variant function/assay suitability. Mouse knockout ataxia is not recast as an observed phenotype in those human reports. No claim that a CPLX1 program, grant or patient group does not exist is made.

## Dated registry checks

Official ClinicalTrials.gov v2 records were read on 2026-10-04. These are dated sponsor entries; no participant eligibility, current site access or available collaboration is determined.

| Record | Design/context | Listed status | Last update posted | Posted results |
| --- | --- | --- | --- | --- |
| NCT04937062 | Glycerol phenylbutyrate; early phase 1, open label | ACTIVE_NOT_RECRUITING | 2026-01-22 | hasResults=false |
| NCT06555965 | STARR; observational natural history | RECRUITING | 2025-10-29 | hasResults=false |
| NCT06625112 | ESCO; observational registry | RECRUITING | 2026-02-06 | hasResults=false |
| NCT06983158 | CAP-002 gene therapy; actual enrollment 1 | TERMINATED | 2026-06-10 | hasResults=false |
| NCT05462054 | Capsida natural history; actual enrollment 0 | WITHDRAWN | 2024-10-18 | hasResults=false |

The literature tab's CAP-002 “listed suspended” wording is now stale. Its older natural history listing must not imply recruitment. Sponsor reporting of the participant death and uncertain underlying mechanism is kept separate from the registry's stopping-rule statement. Neither justifies a universal AAV contraindication.

Absent results **posted to a registry** are distinct from published observational findings. Registration earns no efficacy points. No contacts were sent; no material/data access or partnership is claimed.

## Corrections and exclusions

- Phenytoin contraindication for STXBP1 loss of function was unsupported in this review. It is excluded; no blanket sodium-channel-blocker warning is generated.
- Draft PMIDs 31024012 and 34512011 were not adopted. Verified references replace them.
- “SNARE Research Consortium” was unverified. The real European STXBP1 Consortium is named only with the ESCO source.
- STARR uses NCT06555965, not the draft NCT04938219.
- Levetiracetam renal/behavioral risks replace the draft's generic low-organ-burden wording.
- Exact PathCards membership for both genes was not verified; the curated connection is the narrower primary-supported vesicle/SNARE context.
- Frequency percentages, universal CPLX1 case counts, gene-neighborhood therapy transfer and a Wolf-Hirschhorn bridge are not accepted as demonstrated evidence.
- ClinGen validity classifications are not assigned from the product's qualitative confidence labels.

## Proposed experiments and verification

The STXBP1 proposal separates symptomatic mouse EEG replication from selected-missense protein/function rescue. It defines model/genotype, preparation, exposure, controls, independent replication and distinct falsifiers; one arm cannot validate the other. The CPLX1 proposal first establishes variant/function and assay suitability. Both require expert review and confirmed access. Neither is a completed experiment, patient protocol, dose recommendation, eligibility decision or clinical comparison of superiority.

On the reviewed build, actual Atlas-backed AnalysisService responses validated all source references. STXBP1 returned the scores/ranks above and a graph with **47 nodes / 88 edges / 21 sources**, including all 12 supported node kinds. CPLX1 returned its sourced mechanism with **44 nodes / 85 edges / 6 response sources**, zero candidates and the exact abstention. An entered p.R406H returned unknown function and no ranks/best candidate.

Phenotype projections are inherited HPO annotations whose original PMID resolves to the reviewed source ledger: 13 in the STXBP1 response and 31 in CPLX1. These are labelled disease-level atlas annotations, not newly adjudicated patient observations or curator-validated prevalence estimates. Graph checks reject dangling provenance and cross-disease drug-response transfer.

The graph is a deterministic projection of reviewed records, not new clinical discovery.
The separate six-hour Pulse now discovers bounded public paper/trial records while the
server runs; those items remain unreviewed and do not advance this therapeutic ledger's
review date or alter graph claims, scores or ranks. Exhaustive investigator/funding
search, broader disease curation, material procurement, independent biological
replication and clinical validation remain outside the reviewed snapshot. No measured
10× improvement is claimed. See [Pulse operation and coverage](PULSE.md).
