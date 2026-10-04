# Native literature-review tab → software traceability

Reviewed **4 October 2026**. This records the native reference actually read, the primary-source corrections and the concrete places where its scientific backbone enters the software. It does not claim that every proposed extension in the reference is implemented.

## Native reference and scope

[Hackthon_Challenge 05](https://docs.google.com/document/d/1d7BG3Lx5xmoIiz8lxHH-8twFF0GsYC8FEzO9oFBoeew/edit?tab=t.921tgqhqj2uw) was inspected through the direct Google Drive/Docs connector. Native tab topology was read **before** the targeted text extraction.

| Index | Native tab ID | Exact title |
| --- | --- | --- |
| 0 | t.eysthq9qjolx | Final |
| 1 | t.0 | Rules |
| 2 | t.mjn3ddj3mi18 | Tasks & Timelines |
| 3 | t.921tgqhqj2uw | Literature reviews |
| 4 | t.kpxqn4snfwux | Existing Databases & Knowledge Graphs |
| 5 | t.k581ap2nt5ky | Backend (the logic the sw uses, the engine): |

There were six top-level tabs and no child tabs. The user's URL selected **Final**; the scientific review here targets the separately identified **Literature reviews** tab. A previous flat text export was not accepted as evidence that all tabs had been read.

Document metadata reported modification time **2026-10-04T10:16:18.182Z**. The targeted native response contained **374 paragraphs**, ending at index **26268**, with revision:

`ANLCKQnpY8_5bU-OKMU_4O1yqJ9aVUUW9HuVxYs43oTQsc0TQR0UFIR6P4sBknp3_VD9xm4VY_0v9yTdJksH15hR0NNhTMwDq0R1AriRPW8`

The indexed text was saved as a workspace review aid, without changing the Google Doc. Indices below are paragraph start indices in this native snapshot; later edits can move them.

**Implemented** means the scoped scientific claim is present in a curator field or projected graph relationship and has resolving sources. **Corrected/excluded** means the draft statement was narrowed, replaced or withheld because its stated implication was unsupported or stale. **Deferred** means a proposed resource, program or feature is outside this bounded demonstration; it does not mean it does not exist.

## Foundational evidence, variants and pathway

| Native location / material statement | Review decision and primary-source basis | Concrete software coverage |
| --- | --- | --- |
| 55, 5471: Capsida natural history may look recruiting | **Corrected.** Official NCT05462054 lists WITHDRAWN, enrollment 0, last posted 2024-10-18; checked 2026-10-04. | Historical study asset and clinical-study node; source nct05462054. Not enrollment advice. |
| 384: CPLX1 recessive versus predominantly heterozygous/de novo STXBP1 | **Implemented with scope.** Karaca/Redler families and Saitsu original cases support a reported inheritance contrast; exceptions remain explicit. | Both profiles' variant-effect/context and reciprocal related_disease_evidence.key_difference; sources karaca2015, redler2017, saitsu2008, lammertse2020. |
| 740: Small CPLX1 evidence base / PanelApp case count | **Narrowed.** Use the primary reports' described families, not a total world count or therapeutic proof. PanelApp rating is not adopted as drug evidence. | CPLX1 limitations and zero-candidate abstention; sources karaca2015 and redler2017. |
| 1041–1460: CPLX1 disease/gene/variant identity and OMIM examples | **Implemented/narrowed.** Existing MONDO atlas identity retained; primary family papers provide the reviewed genetic context. An arbitrary variant is not assigned loss of function. | CPLX1 alias/profile, disease MONDO:0033372, gene:CPLX1 and reviewed_gene_association; no patient diagnosis. |
| 1500: Karaca original homozygous CPLX1 report | **Implemented.** Verified primary paper DOI 10.1016/j.neuron.2015.09.048, PMID 26539891; two siblings with a nonsense allele. | karaca2015 paper record; CPLX1 disease/function/pathway/related claims and evidence-building experiment. |
| 1739: Redler independent families and mouse ataxia | **Implemented with species limit.** DOI 10.1038/ejhg.2017.52, PMID 28422131; three human cases in two families. Knockout-mouse ataxia is not a human patient finding. | redler2017 paper and genetic claims; CPLX1 limitations prohibit that species transfer. |
| 2021: PanelApp green rating as strength/MONDO evidence | **Partly implemented, classification excluded.** Stable existing atlas ID is used; neither PanelApp green nor a graph confidence label establishes therapy efficacy or a new ClinGen validity classification. | Existing identity reconciliation plus provenance/confidence scope. No PanelApp-based therapeutic points. |
| 2188, 3737: MalaCards/GO and SNAREopathies review as core bridge | **Implemented via primary evidence.** Karaca/Redler describe complexin context; primary STXBP1 functional papers support vesicle/SNARE regulation. The named review is not used to establish a measured drug effect. | pathway and shared_mechanism claims, inferred shared_research_mechanism edges with inheritance limits. |
| 2502: Saitsu discovery, explicitly requiring citation verification | **Verified and implemented.** DOI 10.1038/ng.150, PMID 18469812; original early-infantile cases and protein experiments. | saitsu2008 paper, STXBP1 disease/function context and source-resolving original HPO annotations. |
| 2738: Kovacevic instability, haploinsufficiency and approximately 50% protein reduction | **Implemented/narrowed.** Reduction refers to specified experimental preparations, not every patient's variant or universal effect size. | kovacevic2018 in functional_mechanism and variant_effect; model/background scope, no universal 50% patient rule. |
| 3027: Chen mouse inhibitory mechanism plus clinical frequency | **Mechanism implemented; universal frequency excluded.** DOI 10.7554/eLife.48705, PMID 32073399 supports mouse cortical inhibitory dysfunction. A population percentage is not transferred from that model. | chen2020 in functional_mechanism/pathway; explicit model/species scope. |
| 3311: Unnamed 2025–26 perspective / more than 300 variants | **Deferred.** No exact primary source for that count was established in this review. | No quantitative variant-count assertion or score input. |
| 4120: Docking/priming/fusion relationship | **Implemented at supported scope.** Reviewed Munc18-1 presynaptic-release context does not establish a uniform causal pathway direction. | reviewed_functional_mechanism and reviewed_pathway_context; saitsu2008, kovacevic2018, chen2020, lammertse2020. |
| 4265: Exact GABA synthesis/reuptake/degradation pathway name for both genes | **Excluded pending verification.** No confirmed shared database membership for this exact broad label. | Narrower vesicle/SNARE pathway. Chen's inhibitory-synapse result stays STXBP1 mouse-specific. |
| 10099: All known CPLX1 patients have one inheritance/family pattern | **Corrected.** The claim is limited to the reviewed families; no exhaustive case census. | CPLX1 variant-effect and limitations; related key_difference. |
| 10223: R406H dominant-negative mechanism implies different therapies | **Corrected to model-dependent evidence.** Guiberson coaggregation and Kovacevic heterozygous-background functional results differ; L446F is a further functional exception. Neither proves an individual drug direction. | STXBP1 variant_effect; mechanism/alignment edges carry a source-backed limiting claim. All entered variants remain unresolved/unranked. |
| 10593–11589: Seizure/movement/autism percentages, onset ranges and CPLX1 overlap | **Partly implemented; quantitative expansion deferred.** Original HPO annotations with resolving primary PMIDs are displayed as disease annotations. Unverified frequencies and age eligibility are withheld; mouse ataxia is not a shared human observation. | annotated_phenotype edges from inherited Atlas HPO data; no new frequency estimates, individualized findings or eligibility filter. |

## Therapeutics, safety, trials and real assets

| Native location / material statement | Review decision and source basis | Concrete software coverage |
| --- | --- | --- |
| 4644, 13075: Foundation community and research resources | **Implemented at verified scope.** Official research directory supports the named organization and registry links. Broader biobank/survey access is not assumed. | STXBP1 patient_group asset/node with stxbp1-foundation; CPLX1 only sees a clearly labelled STXBP1 comparison directory. |
| 4852: STARR current study, launch date and participant count | **Registry status implemented; counts/launch wording narrowed.** NCT06555965 lists RECRUITING, last posted 2025-10-29; checked 2026-10-04. No “over 150 seen” claim from this check. | STARR asset/registered_study_context; nct06555965 plus Foundation. No enrollment or data access conclusion. |
| 5093: ESCO registry and estimated cohort | **Implemented as dated study context.** NCT06625112 lists RECRUITING, last posted 2026-02-06; European STXBP1 Consortium is the sponsor. Estimated enrollment is not actual availability. | ESCO asset/node; nct06625112. |
| 5258: STARR 2026 protocol preprint usable as design | **Deferred as a validated protocol.** Registry design provides observational context; the software does not promote a preprint to clinical readiness or transfer criteria to CPLX1. | Registry asset only; no adopted trial-ready protocol. |
| 7949, 11844: CAP-002 closed but registry supposedly still suspended | **Corrected live.** NCT06983158 lists TERMINATED, last posted 2026-06-10, stopping rule met. The May 11 sponsor letter reports closure following the participant death and unresolved underlying reason. | Historical CAP-002 asset/node with nct06983158 and capsida2026; no ranked therapy, recruiting display or universal AAV contraindication. |
| 8434: Mixed-gene phenylbutyrate pilot proves shared-study/10× logic | **Narrowed.** Co-study design is research precedent, not proof of shared CPLX1 biology, efficacy or speed. Registration and observations are separate. | nct04937062 asset; no human-efficacy credit from registry and no CPLX1 candidate transfer. |
| 8832, 14776–14960: Source differences and verify statuses before demo | **Implemented as a review discipline.** All five registry APIs checked on 2026-10-04; cohort/registry distinctions retained. Exact prevalence disagreement remains outside curated claims. | Source reviewed_on/scope, dated asset status, visible uncertainty and this search/coverage record. |
| 12121: China AAV9 first-in-human report | **Deferred.** No reviewed primary clinical record/outcome supplied for this curation. | No candidate, available program or efficacy edge inferred from a roundtable report. |
| 12329: Quiver ASOs, Buffalo/CHOP AAV, Apertura capsid | **Deferred.** These require exact primary program, exposure, safety and current-status verification before assessment. | No invented assets, inferred available collaboration or therapeutic points. |
| 12491: Phenylbutyrate chaperone rescue and “results pending” | **Implemented and updated.** Guiberson2018 supports selected neuronal/worm 4-PBA results. The registry tests glycerol formulation. Barbour2026 adds uncontrolled parent observations and serious safety limitations; it is not controlled efficacy. | Phenylbutyrate mechanism/preclinical/human/safety assessments and limiting graph claims; sources guiberson2018, barbour2026, ravicti-label, nct04937062. |
| Additional result from the tab's Kovacevic primary paper | **Implemented; changes the ranking.** Acute/five-day levetiracetam mouse ECoG observations replace an unknown preclinical input with disclosed ordinal 0.40. Wang/Xian human differences remain. | Levetiracetam preclinical_evidence→28.25, rank1; source kovacevic2018. No protein-rescue or therapeutic-superiority claim. |
| Targeted chaperone comparator added to substantiate mechanism testing | **Implemented as an insufficient research tool.** Abramov2021 selected-model results; unreviewed human safety/PK/selectivity receive conservative missing-data treatment. | Compound-13 score5.5, insufficient_evidence, no rank; abramov2021. |
| Draft Final-tab phenytoin LOF contraindication | **Excluded.** Unsupported blanket contraindication and associated draft PMIDs were not accepted. | No phenytoin candidate or sodium-channel-blocker warning; explicit correction in limitations/review. |
| Draft low-organ-burden levetiracetam / generic PBA safety | **Corrected.** Official drug labels and the 2026 report constrain safety, organ and interaction claims. | Source-backed risk assessments; keppra-label, ravicti-label, barbour2026; unknown is never safe. |
| 12689: Bexicaserin/fenfluramine broader DEE trials | **Deferred.** A broader DEE trial does not establish STXBP1-specific efficacy, variant compatibility or CPLX1 response. | No candidate extrapolation or transfer edge. |
| 12835: STARR/ESCO/Boston natural history assets | **Verified subset implemented.** STARR/ESCO exact registries are used; unspecified additional Boston studies remain unreviewed. | Two named, dated observational assets; no comprehensive assets claim. |
| 12936, 13302, 14847: No CPLX1 therapy program/group/grant found | **Corrected to scoped gap.** No exhaustive present-tense registry/funding/community search was completed. | No claim that none exists or no NIH grant exists. CPLX1 says no reviewed drug evidence is curated here. |
| 13232: Global Genes concierge route | **Deferred.** Public existence/access route needs separate current verification; contact availability and reply cannot be assumed. | No contact or partnership created. |
| 15353: 4p/Wolf-Hirschhorn unexpected neighbor | **Excluded as an established bridge.** Locus proximity, GTR labels or conflicting aggregation data cannot establish shared disease mechanism or therapy. | No such edge, candidate or community-transfer claim. |
| 15623: JAX/MGI mice and iPSC models | **Partly implemented as publications only; procurement deferred.** Reviewed papers establish methods/models, not current stock or availability. | published_model asset; experiments require confirmed models, permissions and independent validation. |
| 15804: SYNGAP1/SLC6A1 sibling programs | **Limited to verified source context.** STARR includes SYNGAP1 and PB observations include SLC6A1; neither establishes CPLX1 therapeutic compatibility. | Registry/report scope; no added disease therapeutic profile. |
| 15945–16446: Case matching, registry platforms and funding resources | **Deferred.** ClinVar submitters, Matchmaker/GeneMatcher/DECIPHER, RARE-X/Searchlight/Ciitizen, RePORTER/ODC/CURE require scoped verification and applicable access/privacy review. | No patient list, grant absence, access agreement or invented investigator. |
| Verified public author identity | **Implemented narrowly.** Weill Cornell profile and primary papers identify Jacqueline Burre as coauthor. | Explicit investigator asset/node; burre-profile, guiberson2018, abramov2021. No outreach, assumed partnership or present availability. |

## Data, method and optional product proposals

| Native location | Coverage decision |
| --- | --- |
| 5692–6247: Monarch, HPO/MONDO/ClinVar/OMIM, registry/abstract/grant APIs and directories | Existing Atlas HPO/MONDO identities are reused, with primary PMID closure for projected annotations. Registry APIs were used for this dated review. No claim that all named sources are live integrated, monthly refreshed or exhaustive. ClinVar pathogenicity would not establish function/drug response. |
| 6301–6970, 16504: RARe-SOURCE competitor, 37-cluster paper and Monarch LLM plugin | Literature/method pointers are **deferred for comparator/method verification**. The curated graph is not claimed to reproduce the paper's clustering result, validate clinical discovery or beat a comparator. |
| 7150–7836: Evidence drawers and hand-curated seed edges | **Implemented:** primary-backed claim fields feed typed nodes/edges, each with source IDs, assertion, qualitative confidence/basis, scope and limiting claims. Registry/organization/author identities remain distinct from efficacy. |
| 7361: Study-plan agent adapting an observational protocol | **Narrowed:** expert-review-required laboratory validation proposals, with prerequisites and falsifiers. No clinical protocol, eligibility recommendation or shared-drug transfer. |
| 9049–10050: Wider STX1B/SNAP25/VAMP2/STX1A/UNC13A/SYT1/RIMS1/STXBP6 constellation | **Deferred from curated therapeutic assessment.** Existing atlas breadth is not equivalent to reviewed treatment evidence. Draft quantitative counts and emerging-gene conclusions are not propagated into these profiles. |
| 13499–14082: Dark constellation, related connections, evidence ladder and action/gap panels | Scientific backbone implemented by profiles, shared-research edges and source-led assessments/assets. UI rendering is verified separately by integration work. No new message/contact action is authorized by a reference suggestion. This document supplies the bounded coverage ledger; it does not claim a comprehensive negative search. |
| 14182: Eligibility slider, 10× slider, parent toggle and contribution button | **Deferred optional scope.** No patient criteria assessment or family observation ingestion. Plain explanations do not expand the approved evidence set. An illustrative speed thesis must remain explicitly unmeasured. |
| 15132: ClinGen confidence framework | Product confidence describes a scoped relationship, not a newly assigned official ClinGen gene-disease classification or clinical probability. |
| 16631–19122: Watchlist, scheduled APIs, diff, review queue and Pulse | **Deferred optional architecture.** A review date is shipped; no autonomous ongoing monitoring, six-hour refresh, comprehensive new-grant feed or live-update guarantee. API examples in the reference were not treated as implementation instructions. |
| 19281–20156: Weekly three-item brief and optional email sending | **Deferred.** No recurring job or real email was created/sent. |
| 20265–20647: Numerical freshness half-lives/opacity | **Deferred; scientific calibration excluded.** The suggested half-lives are illustrative design constants, not validated rates of evidence decay. Source review and registry update dates remain separate. |
| 20845–21799: Sibling scanner ranking by assets | **Deferred expansion.** STXBP1↔CPLX1 is the reviewed research bridge. Unsearched assets for other genes do not become “none.” |
| 21801–22236: CPLX1 case-finder | **Deferred.** Primary family reports are public resources, not a database of identified patients or a right to contact families. |
| 22445–22908: Grounded Ask-the-atlas retrieval/quote checks | Source closure and optional constrained explanation are implemented in the analysis flow. Free-question embeddings/top-eight-edge retrieval is **deferred**; no claim of this full extension. |
| 22997–23692: Structured CAP-002 eligibility sandbox | **Excluded from this submission's patient flow.** Terminated trial context remains visible; no dose, age, prior-treatment or patient eligibility determination. CPLX1 non-transfer is a research limitation, not a personalized exclusion decision. |

## Concrete source → assessment → graph proof

The library is **atlas/analysis/evidence.json**. The service validates profile/candidate types and source closure, computes scores and projects the response through **atlas/analysis/graph.py**. These are data-driven reviewed connections, not a bibliography detached from the result.

Actual Atlas-backed responses were inspected after curation. The following stable IDs are examples from those responses:

| Evidence path | Example graph relationship | Sources / boundary |
| --- | --- | --- |
| STXBP1 disease + functional_mechanism | gene:STXBP1 → mechanism:efcb6a5e1b52c76b, edge:309c251204fa8815, reviewed_functional_mechanism | saitsu2008/kovacevic2018/chen2020/lammertse2020; limiting claim also cites guiberson2018. No entered-variant classification. |
| CPLX1 functional_mechanism | gene:CPLX1 → mechanism:849c1642fa2538c2, edge:c59c6287a1649ff1 | karaca2015/redler2017; inferred genetic/protein-function context, no measured arbitrary-variant direction. |
| STXBP1 pathway | edge:bdddc94e49bd7856, reviewed_pathway_context | lammertse2020/chen2020; model-specific inhibitory scope. |
| Reciprocal related_disease_evidence | edge:13e42554edf87210 and edge:2eb1d2c592ad4a97, shared_research_mechanism | karaca2015/redler2017/lammertse2020 plus inheritance-limiting sources. No related disease → drug-response edge. |
| LEV preclinical_evidence | candidate:stxbp1-levetiracetam → disease:MONDO:0012812, edge:59a8987905c01479 | kovacevic2018; mouse symptomatic endpoint only; disclosed input0.40. |
| Candidate human_evidence | reported_human_evidence and candidate_under_research relationships | LEV Wang/Xian contrast; PB uncontrolled observations and safety limits remain source-bound. |
| Explicit investigator asset | disease:MONDO:0012812 → investigator:asset:1a815be80e4ff25f, edge:51cdfddff80c6257 | burre-profile/guiberson2018/abramov2021; published identity only. |
| Published variant example | variant:reported:lammertse2020:L446F, edge:101cc8d4bd162233 | Exact reviewed excerpt/genotype/model; separate from any entered variant. |
| Registry asset | registered_study_context and documented_by | Dated source status; historical CAP-002/Capsida listings remain closed. No efficacy credit. |
| HPO annotation | annotated_phenotype plus documented_by | Original annotation's PMID must resolve to a reviewed source. Annotation identity is not newly adjudicated prevalence or patient evidence. |

STXBP1 produced **47 nodes, 88 edges and 21 resolving sources**, including disease/gene/variant/mechanism/pathway/phenotype/candidate/paper/clinical-study/patient-organization/investigator/research-asset node kinds. CPLX1 produced **44 nodes, 85 edges and six resolving sources**, with seven node kinds and **zero candidate nodes**. Original reviewed-reference HPO annotations account for 13 STXBP1 and 31 CPLX1 phenotype nodes.

The CPLX1 response retains its mechanism and returns **No defensible therapeutic candidate found.** An entered STXBP1 p.R406H returns unknown individual function, no best candidate and no ranks. The published-example node remains a source-scoped example, not a matching patient's classification.

This verification establishes source/contract closure and correct deterministic projection. It does not establish biological validity, treatment efficacy, a complete literature search or final browser usability. Integration tests and visual checks are separate.

## Honest 10× thesis

Native indices **23920–25956** explicitly distinguish an illustrative preparation estimate from measured results. The draft's 40→4 months claim cannot be derived from its scientific sources.

The defensible product thesis is: **assembling a sourced research proposal may become faster when disease/mechanism evidence, limiting findings and real assets are already connected. A 10× improvement is a target or illustrative scenario, not a measured result.**

A proposal and an initial partner meeting are different milestones. Partner replies, expert review, ethics, contracts, funding and experimental work remain human-paced. Shortening evidence preparation must not be described as shortening clinical development by the same factor.

A measurement would require the same previously unseen task and an agreed quality rubric for manual and software-assisted users. Time source verification, correct identity/inheritance, contradictory evidence, current study status and completion of a reviewable proposal. An independent expert should score correctness/completeness and count unsupported claims before comparing completion times. Report actual sample size, timing and uncertainty; a projected table or timed page load is not this benchmark. No such comparative measurement was performed in this source review.

The scientific sources support the evidence connections and their limits. They do not support a numerical productivity multiplier or a claim that related-gene co-studies prove CPLX1 therapeutic compatibility.
