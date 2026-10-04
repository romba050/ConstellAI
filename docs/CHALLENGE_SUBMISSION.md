# Challenge 05: requirements and submission handoff

Checked against all six pages of the supplied **Challenge Buffalo.pdf** on
4 October 2026. Source SHA-256:
`9c502bdfcc0d5c400c11dd7a78bd9fc3c4b4f07529a973e076d109e28605d67e`.
The supplied Google Doc's scientific material is separately mapped in
`LITERATURE_REVIEW_TRACEABILITY.md`. This checklist records software coverage
and distinguishes it from completed organizer submission.

## Required product capabilities

| Brief location and requirement | Concrete coverage | Verification or boundary |
| --- | --- | --- |
| p2–3: Maria leads a complete disease-to-action journey | Primary therapeutic screen plus Maria-only `/atlas`; other audience switches and stored-persona restoration removed. | Actual browser checks; supporting Biology, Community and People tabs serve Maria. Separate persona modes are not a stated deliverable. |
| p2–3: connected disease, gene, variant, mechanism, symptom and research nodes | Original 6,457-disease atlas plus the typed reviewed therapeutic graph. | STXBP1: 47 entities/88 edges/all 12 entity types. Stable IDs and source closure checked. |
| p3: names/synonyms and stable identifiers | Existing atlas reconciliation/search and deterministic curated disease/gene aliases. | Unknown or conflicting identity abstains; same gene alone cannot substitute an unknown disease. |
| p3: variant effects, rather than shared gene labels | Published model examples have their own scope; every entered variant remains unreviewed. | A typed G544D is separate from the published example and withholds ranking. No gene-wide LOF/GOF treatment rule. |
| p3: disease–phenotype | Original HPO annotations and their provenance; reviewed PMID subset in the therapeutic graph. | Disease annotations remain separate from an individual's findings. Unverified phenotype frequencies are withheld. |
| p3–4: publication/claim/investigator; supporting and contrary research | Literature review maps source records to mechanism, candidate and graph claims; investigator identity tied to papers/institutional profile. | Qualitative confidence, model/variant limits and contradictory human observations remain visible. Authorship does not establish partnership. |
| p4: study/intervention; funding/researcher/asset; organization/registry | Original atlas retains PubMed, ClinicalTrials.gov, NIH RePORTER, patient organizations and connection assets. Reviewed hero adds dated studies, Foundation, published models and a verified investigator. | Current, withdrawn and terminated records are distinguished. No invented funding gap, stock availability, eligibility or collaboration. Legacy retrieval is separate from the reviewed cached hero. |
| p4: trustworthy inspectable connections and an honest gap | Edge inspector with source, relation, assertion, confidence basis, scope and contrary findings. CPLX1 shows reviewed biology with no drug candidates. | Citation/end-point integrity and corrupt-record withholding tested; unknown evidence is not safe or effective. |
| p4: mechanistic overlap and defensible clustering | Preserved phenotype/pathway similarity, Leiden groups and UMAP atlas; reviewed STXBP1/CPLX1 research bridge. | Shared pathways do not transfer therapeutic response. Variant/model counterexamples constrain interpretation. |
| p4: shareable assets and network overlap | Original connection/assets/People/constellation investigator scan preserved; hero shows publication-backed validation resources. | Name-level overlaps need identity verification; no shared human-treatment benefit or confirmed asset access claimed. |
| p4–5: readable interface, progressive disclosure, global search | Dark Maria journey; five candidate facets; expandable graph, literature, source and arithmetic details. `/atlas` retains disease/gene/symptom/mechanism/group search. | Desktop/mobile browser checks, graph pointer/keyboard checks and contained table scrolling pass. |
| p5: meaningful milestone and a 10× case with assumptions | Milestone: a defensible source-backed decision on which therapeutic hypothesis to investigate and what experiment can disprove it. Manual disconnected steps versus one structured workflow are compared. | Exact acceleration is unmeasured. `JUDGING_READINESS.md` gives a counterbalanced evaluation plan; expert review and experimental timelines retain their duration. |
| p5: OpenAI extraction, reconciliation and explanation | Server-side Responses integration with strict schema, exact source quotes, approved IDs, fallback and deterministic scoring. Existing atlas extraction/reconciliation/explanation retained. | Mocked transport is verified. A real model call is still required after the teammate adds the key, especially to substantiate track-prize model/tool use. |
| p6: concrete next experiment, reusable asset, collaborator or honest gap | STXBP1 proposes separate model-specific seizure-control and protein/function-rescue tests; CPLX1 proposes establishing variant function. Original sourced collaboration proposal remains available. | These are expert-review proposals. No experiment, contact, enrollment, partnership or clinical decision has occurred. |

The optional stretch ideas, investor/funder discovery beyond existing source
support, all-disease therapeutic validation and patient-contributed evidence
are not required for this focused complete demonstration and are not claimed.

## Required submission artifacts

| Brief p6 deliverable | Ready artifact | Remaining action |
| --- | --- | --- |
| Working prototype: deployed **or** easy to run locally | Included graph/evidence, `START_DEMO.cmd`, minimal runtime instructions, cached hero and explicit gap paths. | Judges can run locally. Public hosting is optional for this route and has not been updated. |
| Source repository with architecture and dataset reproduction README | New `therapeutic-hypotheses-demo` branch, architecture/data source/build instructions, tests, frozen schema and reviewed evidence. | Final branch URL and versioned source package are supplied in the delivery receipt. |
| Team video | Ready speaking outline below; use real teammate names and contributions. | Team must record the video and provide/upload its actual link. No recording is claimed. |
| One-minute walkthrough | Timed click/narration script in `THERAPEUTIC_DEMO.md`; repeatable cached UI; local complete render measured under one second. | Record the walkthrough and provide/upload its actual link. Rendering speed is not a viewer usability or 10× study. |

After the key is configured, follow the live activation check in
`THERAPEUTIC_DEMO.md`. Keep evidence scores unchanged and inspect provenance.
Then record the two videos, supply the actual team names and links, and submit
the package through the organizer's required channel. No organizer submission
or team communication has been performed by this software work.

## Mentor-aligned pitch

Families may know the diagnosis and causal gene while the path to research
remains fragmented across variants, pathways, papers, candidate medicines,
studies and safety evidence. ConstellAI starts from that genetic question and
helps Maria's patient organization choose a therapeutic direction worth
investigating, understand its evidence and uncertainty, and prepare a concrete
experiment and partner discussion.

The output is a data-driven research hypothesis and validation plan. Partners
must carry out laboratory work, clinical development and patient-specific
decisions. This is a gene-first research workflow; individualized clinical
precision medicine is a future validation goal, not an achieved capability.

Public sources include PubMed/PMC, MONDO/HPO/Reactome/ClinVar, ClinicalTrials.gov,
NIH RePORTER and verified organization/institutional pages. Sources, model
scope and safety limits remain visible. AI structures and explains supported
information; deterministic code computes the research-priority score.

For problem-scale slides, attribute any figures to their source and preserve
their endpoint. The brief p2 estimates 350 million affected and fewer than 5%
of rare diseases with an approved treatment. The mentor's cure percentage is
a different endpoint and is not silently substituted or advertised as a
verified software fact. The software needs no population statistic to make
its supported research decision.

## Team-video speaking outline

1. Each actual teammate briefly introduces their name, role and contribution.
2. State the problem: a genetic diagnosis can leave a community without a
   clear research direction because the evidence is disconnected.
3. Explain the approach: disease/gene → mechanism → connected sources →
   candidate evidence/safety → auditable hypothesis → next experiment/assets.
4. State the proof: one deeply reviewed STXBP1 case, literature-to-claim
   traceability, deterministic scoring, Maria-only dark UI, and a CPLX1/variant
   gap that withholds unsupported ranking.
5. Explain the milestone and honest 10× thesis: reduce repeated evidence
   assembly and decision-preparation work; measure completion, source accuracy
   and harmful omissions against manual research before claiming acceleration.
6. End with the next validation: independent scientific review, model-specific
   replication and verified partner access. The separate one-minute recording
   demonstrates the actual UI rather than claiming a completed clinical result.
