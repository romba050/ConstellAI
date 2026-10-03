# Challenge compliance — official Buffalo PDF and frozen work order

Audit basis: the owner's pasted work orders, final scope freeze and the supplied six-page **Challenge Buffalo.pdf**, reviewed as text and rendered pages on 2026-10-03. The PDF confirms the five judging criteria and submission materials. See OFFICIAL_CHALLENGE_REVIEW.md for page-specific coverage and remaining gaps; organizer acceptance is not certified by this checklist.

## Required objective and entities

- [x] 5,000+ monogenic rare-disease scalability story: general source/graph/scoring schema and gated ingestion path; 6,131 inherited discovery names. **Only four curated pilots and one deep journey; broad validation is not claimed.**
- [x] Evidence-backed: 39 public source records; 11 verified PubMed bibliography records. Every curated graph item resolves provenance. Unknown dates/denominators and source-access limitations are explicit.
- [x] AI knowledge graph: Codex-assisted relationship curation plus strict runtime OpenAI extraction adapter, reviewed cached graph, provenance validation. Runtime extraction is proposal-only.
- [x] Disease connections: Angelman/PWS shared imprinting/model context with distinct therapy directions; dosage-gain counterexample.
- [x] Gene connections: cited causal biology, UBE3A and relevant SNORD116-region context.
- [x] Symptom connections: source-reported phenotypes; no diagnosis inferred.
- [x] Study connections: primary publications and registered trial metadata.
- [x] Patient-group connections: official organizations for four pilots and PWS.
- [x] Actionable patient next steps: related community, reusable publication/model approach, shared brief, clinician resource and dated trial navigation.
- [x] Actionable researcher next steps: gaps, gated hypothesis priority, experimental comparators, proposed collaboration and early-kill experiment.
- [x] Working prototype: one-command loopback app, cached data, unit/API tests and browser acceptance.
- [x] Provenance/citations: graph inspector, dialogs, sources and exports.
- [x] Differentiation from ordinary graph: signed mechanistic coverage, irrelevant/spillover and uncertainty penalties, remaining biology, non-redundancy gates and falsification questions.

## Five judging criteria

| Criterion in the official PDF (p. 6) | Implemented evidence | Honest limit |
| --- | --- | --- |
| Graph quality | Typed disease/gene/variant/phenotype/mechanism graph; cited cross-community model path; explicit non-connection; filters and relationship picker | One illustrative ClinVar variant, no patient diagnosis; one deeply curated cluster; no large-scale graph-clustering algorithm |
| Evidence integrity | FACT / INFERENCE / HYPOTHESIS / CLINICAL EVIDENCE labels; source/date/type/confidence/observed-inferred/contradiction fields | Not systematic contradiction or independent clinical review; source-specific observations |
| Patient progress | Family journey to PWS community/model publication/shared-action brief, then researcher and therapeutic views | No agreed collaborator, verified model access or completed patient outcome |
| 10x impact | Visible manual-vs-Atlas workflow and milestone; preplanned evaluation | Unmeasured hypothesis; curation and validation cost not hidden |
| Ambition/product craft | Disease/gene search; four major surfaces with patient/researcher views; progressive provenance; readable dark responsive interface | Symptom/group/mechanism search not implemented; prototype storage, no production access controls or large-scale ingestion |

## Updated journey acceptance

- [x] Search a rare disease / causal gene.
- [x] Understand plain-language disease biology.
- [x] See causal gene / mechanism class.
- [x] See defensible shared imprinting-model cluster.
- [x] Inspect citations for major connections.
- [x] See a sourced dosage-direction counterexample.
- [x] Find another official patient community / publication team.
- [x] Find a reusable published model/study approach.
- [x] Open deterministic MEDR5 reasoning.
- [x] Compare three interventions on direction, coverage, spillover and evidence.
- [x] Retain unresolved disease biology.
- [x] Export a proposed shared action / see next falsification experiment.
- [x] Show unmeasured 10x acceleration story.
- [x] State remaining validation requirements.

## OpenAI and submission gates

- [x] Meaningful OpenAI development use disclosed: Codex-assisted claim/relation curation, explanations and proposed experiment drafting.
- [x] Runtime OpenAI Responses extraction implemented with strict source-bound schema; numerical scores are deterministic.
- [x] Offline replay clearly distinguished from live execution.
- [x] Official PDF reviewed: prize eligibility wording requires OpenAI **models or tools** (p. 5). It does not explicitly require a paid live runtime call. Codex tools use is disclosed; organizer decides acceptance.
- [x] Source repository README explains architecture and deterministic offline reproduction of the curated graph dataset; reproduction and output hashes verified.
- [x] 1-minute walkthrough recording script prepared to match p. 6; longer pitch retained separately.
- [ ] Team video and actual 1-minute walkthrough video: **not recorded or submitted**. The PDF does not provide further Team-video format details.
- [ ] Live paid OpenAI API execution: **not verified; server-side API key absent**. Mock adapter tests do not prove live execution. This is an implementation limit, not a PDF-imposed paid-API requirement.
- [ ] Any organizer rules outside the supplied PDF, including pre-existing-code policy and final submission portal/deadline: **not established by this PDF**. The app cannot certify organizer acceptance.
- [ ] Measured acceleration / clinical validation / partner asset access: **not established**, and not represented as established.

Pre-existing MEDR5 source is preserved and disclosed; hackathon work is isolated. Research decision support, no diagnosis/prescription, no efficacy/safety claims, no invented organ-burden number, no private patient records, no automatic outreach.

## Final P0 scope freeze

- [x] `/demo` and Cached demo link load the cached Angelman hero without PubMed/OpenAI/network calls.
- [x] Only four major surfaces: Atlas; Connections / shared assets; Therapeutic hypotheses; Next action. Patient / Family and Researcher are audience views within these surfaces.
- [x] Atlas is a visible interactive typed graph with selectable edge dots, nodes, relationship picker and provenance inspector.
- [x] Product therapeutic reasoning consumes typed graph edges, with regression checks that removed/reversed edges block ranking.
- [x] Small visible OpenAI → graph → deterministic MEDR5 architecture diagram and clean closing statement.
- [x] 90–120-second scripted route documented; human pitch timing has not been measured.
- [x] Requested dark palette verified in graph, evidence panels, controls and mobile layout; core reasoning gates preserved.
- [x] Real PubMed / PMC bibliography, ClinVar condition assertions, MONDO/HPO terminology and a NIH RePORTER programme are visible separately from mechanistic priority. Journal prestige is not scored; no Ovid dependency.
- [x] Lightweight prior, connectivity correction and small benchmark stay secondary, source-limited and disclosed. No MATRIX recreation, embeddings or broad ML pipeline.

Feature scope is frozen; final work is verification, documentation, commit and push.
