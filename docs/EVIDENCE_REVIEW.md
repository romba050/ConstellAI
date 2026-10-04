# STXBP1 evidence review

Reviewed on **4 October 2026**. The shipped evidence is a curated research demonstration with three evaluated candidates. No candidate is classified as a supported clinical treatment.

## What the evidence supports

| Candidate | Curated interpretation | Default score / status |
| --- | --- | --- |
| Phenylbutyrate | Selected-model rescue motivates investigation. The human reports chiefly concern glycerol phenylbutyrate, requiring formulation-aware translation. | 27 / research hypothesis |
| Levetiracetam | Symptomatic human observations are mixed; comparative superiority and disease modification are unestablished. | 24.25 / research hypothesis |
| Compound 13 | Experimental comparator with unreviewed human safety, exposure and interactions. | 5.5 / insufficient evidence; unranked |

All component values are **curator ordinal judgments**, not published effect sizes, probabilities, or a validated clinical model. Scores are calculated in Python from disclosed inputs. Status and compatibility gates can withhold ranking regardless of score.

The six positive ratings are mechanism, variant compatibility, human evidence, preclinical evidence, phenotype and quality. Phenylbutyrate uses 0.90 / 0.50 / 0.25 / 0.80 / 0.65 / 0.60; levetiracetam uses 0.45 / 0.45 / 0.45 / unknown / 0.75 / 0.60; compound 13 uses 0.90 / 0.50 / unknown / 0.70 / 0.50 / 0.60. High mechanistic alignment refers to a selected biological model. Modest compatibility ratings express disease context without assigning the user's variant.

Weights are 30/15/20/10/10/15. Penalties use the worse of toxicity/organ burden (15), interactions (10), spillover (10), and uncertainty (15). Unknown positive data earns zero credit; unknown risk takes the full penalty. This policy leaves compound 13 unranked. Every supplied variant requires further functional review; the backend withholds compatibility and candidate ranking rather than making a universal LOF/GOF assumption.

## Verified sources and scope

| Source ID | Primary or official source | Evidence boundary |
| --- | --- | --- |
| guiberson2018 | [2018 chaperone report](https://www.nature.com/articles/s41467-018-06507-4), PMID 30266908 | Selected-model rescue; not human efficacy. |
| abramov2021 | [Targeted chaperone report](https://link.springer.com/article/10.15252/emmm.202012354), PMID 33332765 | Compound 13; clinical exposure/safety unestablished. |
| lammertse2020 | [Homozygous L446F report](https://pmc.ncbi.nlm.nih.gov/articles/PMC7009479/) | Functional counterexample to uniform loss of function. |
| wang2022 | [Levetiracetam cohort](https://pubmed.ncbi.nlm.nih.gov/35007884/) | Non-randomized partial-remission association. |
| xian2023 | [Published Brain cohort](https://pmc.ncbi.nlm.nih.gov/articles/PMC10689925/), PMID 38015929 | Did not find superior levetiracetam seizure reduction. |
| barbour2026 | [Parent-interview report](https://pmc.ncbi.nlm.nih.gov/articles/PMC13405358/), PMID 42447769 | Uncontrolled mixed-gene observations; serious toxicity reported. |
| ravicti-label | [Glycerol phenylbutyrate label](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=900e7dc0-9afe-4f50-80de-90567bb78519) | Urea-cycle indication, metabolite and interaction risks. |
| keppra-label | [Immediate-release levetiracetam label](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=3ca9df05-a506-4ec8-a4fe-320f1219ab21) | Behavioral risks, renal clearance, studied interactions; no STXBP1 repair claim. |
| redler2017 | [CPLX1 family study](https://pmc.ncbi.nlm.nih.gov/articles/PMC5520065/), PMID 28422131 | Recessive inheritance and pathway context; no therapy transfer. |
| stxbp1-foundation | [Official research directory](https://www.stxbp1disorders.org/clinicaltrialsandresearch) | Establishes the patient organization and named study links. |

The 2026 parent-interview study includes 18 children, of whom 13 had STXBP1. Its pooled response figures must not become STXBP1-specific efficacy estimates. One sodium phenylbutyrate exposure is described; clinical preparation identity matters. The source's reports cannot establish causation or independent developmental benefit.

The original supplied Xian link, PMC10197795 / PMID 37215006, is the preprint. The evidence uses the final publication above. The separate earlier phenylbutyrate clinical pilot referenced by Barbour appears as a 2024 medRxiv report; it has not been promoted to controlled efficacy evidence.

## Dated registry checks

The official ClinicalTrials.gov v2 API was read for all three records on 2026-10-04. These are sponsor registry entries; present site availability must be confirmed with study teams.

| Record | Intervention/design | Listed status | Last update posted | Posted results |
| --- | --- | --- | --- | --- |
| [NCT04937062](https://clinicaltrials.gov/study/NCT04937062) | Glycerol phenylbutyrate; early phase 1, single-group open label | Active, not recruiting | 2026-01-22 | hasResults=false |
| [NCT06555965](https://clinicaltrials.gov/study/NCT06555965) | STARR; observational natural history | Recruiting | 2025-10-29 | hasResults=false |
| [NCT06625112](https://clinicaltrials.gov/study/NCT06625112) | ESCO; observational registry/natural history | Recruiting | 2026-02-06 | hasResults=false |

The absence of results **posted to a registry** is distinct from the existence of published observational findings. Registration gives no efficacy points. STARR and ESCO provide research-planning context; they are not candidate therapies. No contacts were sent and no access or partnership is claimed.

## Corrections to the supplied Google Doc example

- The claim that phenytoin is contraindicated for STXBP1 loss of function was unsupported in this review. Phenytoin is excluded; no blanket sodium-channel-blocker warning is generated.
- The example PMIDs 31024012 and 34512011 were not adopted. Verified primary references replace them.
- The unnamed “SNARE Research Consortium” was not verified and is not included. The European STXBP1 Consortium is explicitly identified in the ESCO registry.
- STARR is linked to verified NCT06555965, not the example's NCT04938219.
- A generic “low organ burden” levetiracetam description is removed.
- Free 4-PBA, sodium phenylbutyrate and glycerol phenylbutyrate are not interchangeable exposures.
- CPLX1 pathway overlap does not establish phenylbutyrate response, clinical eligibility or a shared trial population.

## Proposed experiment and remaining gaps

The experiment is a **proposal requiring expert review**, not a completed test or a patient protocol. Published assays inform paired protein-solubility and synaptic-function readouts; the proposed design adds explicit variant/zygosity, chemical identity, measured exposure, controls and falsification requirements.

A result fails the hypothesis if protein stabilization lacks functional rescue, activity diverges further from controls, or benefit depends on cytotoxic exposure. Model access, procurement, independent replication, statistical design, exposure translation and clinical interpretation remain unverified. No doses, age eligibility, treatment starts or monitoring schedules are provided.

Source objects contain dated scope and short exact excerpts. Other claims are explicitly curator paraphrases or research-design judgments, with source IDs attached. The curation covers one hero disease, rather than implying comprehensive literature coverage.
