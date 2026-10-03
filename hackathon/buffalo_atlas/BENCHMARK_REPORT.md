# Small withheld-positive benchmark

Frozen pilot run: 2026-10-03. Numerical MEDR5 adapter; no training, embeddings or tuned model. Four cited positives: three preclinical mechanism observations and one randomized clinical symptom-effect reference. These are not four proven clinical repurposing successes.

Reproduce from `hackathon/buffalo_atlas`: `python -m atlas.benchmark`.

| Mode | n | Hit@1 | Hit@3 | MRR | Abstentions | Wrong-pilot eligibility |
| --- | --- | --- | --- | --- | --- | --- |
| relation_only | 4 | 0.250 | 0.500 | 0.375 | 2 | 0 |
| source_disjoint | 4 | 0.000 | 0.000 | 0.000 | 4 | 0 |

## Per-fold results

| Mode | Withheld pair | Positive evidence kind | Rank / eligible pool | Prior after withholding |
| --- | --- | --- | --- | --- |
| relation_only | topotecan / angelman | preclinical_mechanism | 1 / 2 | Unknown |
| relation_only | ube3a-ats-aso / angelman | preclinical_mechanism | Abstain / 2 | Unknown |
| relation_only | pha533533 / angelman | preclinical_mechanism | 2 / 2 | Unknown |
| relation_only | ganaxolone-reference / cdkl5 | clinical_symptom_evidence | Abstain / 0 | Unknown |
| source_disjoint | topotecan / angelman | preclinical_mechanism | Abstain / 1 | Unknown |
| source_disjoint | ube3a-ats-aso / angelman | preclinical_mechanism | Abstain / 2 | Unknown |
| source_disjoint | pha533533 / angelman | preclinical_mechanism | Abstain / 1 | Unknown |
| source_disjoint | ganaxolone-reference / cdkl5 | clinical_symptom_evidence | Abstain / 0 | Unknown |

## Stratified interpretation

Relation-only, preclinical n=3: Hit@1 1/3; Hit@3 2/3; MRR 0.500; one abstention. Clinical symptom n=1: ganaxolone/CDKL5 abstains because symptom evidence does not establish a sourced CDKL5-restoring mechanism. Source-disjoint: all three preclinical cases and the clinical reference abstain; no withheld clinical link is recovered.

The prior label is removed in every fold. Candidate pool is all four intervention records without known-positive disease-membership prefiltering; numeric scoring does not use summaries or names. Eligible ranks include research comparators for this diagnostic, so this is not an approved-drug benchmark. Unknown-spillover ASO is withheld. Wrong-pilot eligibility is checked against the other three pilot signatures, not a set of clinically verified negatives.

**Relation-only retains mechanistic features derived from the positive source papers: information leakage prevents interpreting its recovery as out-of-sample prediction.** Source-disjoint also removes all held-source references from scored effect, spillover and risk features across every candidate. Source records remain for identity/provenance integrity, but no score accesses unlinked summaries. Strict removal reveals the pilot has insufficient independent evidence to recover those pairs.

Abstentions count as misses in Hit@k and MRR. An eligible pool can contain fewer than four records because evidence gates apply. No clinically meaningful accuracy, generalization, superiority over Every Cure or therapeutic efficacy is demonstrated. A broader held-out clinical benchmark would need independent mechanism sources, validated positive/negative endpoints, alias/duplicate/source leakage auditing and a frozen larger candidate universe; that work is intentionally outside the frozen hackathon scope.

The separate prior and degree normalization implement small explicit policies. Each real curated candidate has only one recorded disease link, so normalization currently leaves positive priority unchanged. Unit tests use labeled synthetic four-link cases to verify a 0.5 factor; those tests are not new drug–disease evidence.

Concept references: [Every Cure frequent-flyer transformation](https://docs.dev.everycure.org/pipeline/pipeline_steps/matrix_transformation/), [Every Cure evaluation](https://docs.dev.everycure.org/pipeline/data_science/evaluation_deep_dive/). This implementation does not recreate MATRIX or use its predictions.
