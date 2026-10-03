# Official Buffalo challenge review — 2026-10-03

Reviewed all six text pages and rendered original pages of **Challenge Buffalo.pdf**, titled *AI Atlas for the World's Rare Diseases — Challenge Brief*, supplied by the owner. SHA-256: `9c502bdfcc0d5c400c11dd7a78bd9fc3c4b4f07529a973e076d109e28605d67e`.

The PDF is a requirements/reference document. Its calls to contact partners or submit materials do not authorize outreach, account changes or submission. Feature scope remains frozen; this update enriches evidence provenance, applies the requested dark theme and prepares reproducible submission documentation.

## Fit to the actual brief

| PDF requirement / page | MEDR5 evidence | Status and boundary |
| --- | --- | --- |
| Sourced typed graph, mechanism and phenotype connections (pp. 2–4) | Four pilot graphs; 35 nodes / 44 edges in the Angelman hero; inspectable source, relation, claim status, date and uncertainty | Implemented curated slice; no full 5,000-disease graph |
| Defensible mechanistic clustering and graph analytics (pp. 2, 4, 6) | Sourced imprinting/model path, different parental defects, UBE3A dosage-gain counterexample; graph-consumed therapeutic reasoning | Partial: the cluster is curated, not a large-scale discovery/clustering algorithm |
| Gene–variant–mechanism / disease–phenotype identifiers (pp. 3, 5) | MONDO identifiers with explicit breadth; HPO feature terms; transcript-specific ClinVar condition assertion; OMIM cross-reference | Partial coverage. No patient variant diagnosis. Direct OMIM content not imported; CACNA1A umbrella is not equated to one narrower ontology condition |
| Publications, claims and investigators (pp. 3–5) | 11 real PubMed-indexed papers, DOI/journal/authors/types, study design and contextual denominators; source claims distinguished from graph inference/proposal | Implemented pilot metadata; not a systematic review; no journal-prestige scoring |
| Trials and research programmes (pp. 4–5) | Dated ClinicalTrials.gov records; NIH RePORTER project 5R01NS131615-04 and public investigators | Public records linked; trial eligibility, completed results, collaboration and asset access not inferred |
| Patient groups / reusable assets / action this week (pp. 2–6) | Official groups, NORD/network navigation, paired model methodology, cited proposed collaboration brief and falsification experiment | Proposed shared action; no secured cell inventory or partnership; direct Orphanet directory content unavailable |
| One search across disease, gene, symptom, group and mechanism (p. 5) | Disease/gene search and broad disease-name discovery | Partial: symptom/group/mechanism search and broad synonym reconciliation are not implemented |
| Family usability / progressive reveal / meaningful colour (pp. 4–5) | Four surfaces; Family/Researcher views; dark graph and source dialogs; mobile layout and text contrast checked | Implemented prototype; no formal family usability study |
| Distinguish evidence, hypothesis and clinical proof (pp. 4–6) | Edge classification, study design, uncertainty, remaining biology, clinical safety separate from mechanistic fit | Implemented explicit boundaries; contradiction review and clinical validation remain incomplete |
| 10x meaningful milestone / existing timeline versus proposed route (pp. 5–6) | Therapeutic-priority decision, manual-versus-Atlas steps, assumptions and planned matched-task measurement | Partial: unmeasured acceleration hypothesis. No established timeline ratio or treatment acceleration |
| OpenAI models or tools for track prizes (p. 5) | Disclosed OpenAI Codex development assistance; runtime Responses proposal adapter; saved replay distinct from live calls | Meaningful tools use documented; organizer decides acceptance. Live paid runtime call remains unverified, and is not expressly demanded by the PDF |

## Submission materials explicitly listed on page 6

- **Working prototype:** local one-command `/demo` supports live exploration with cached evidence.
- **Source repository / README:** architecture, exact curated inputs, source limits and deterministic offline dataset reproduction are documented and verified.
- **Team video and 1-minute walkthrough:** the 60-second script below is prepared. Actual videos remain to be recorded; no upload or organizer submission has occurred. The 90–120-second script is retained as a separate longer pitch.

The six-page PDF does not specify an upload portal, deadline, video codec, repository visibility/license requirement or rule about pre-existing code. These must not be invented. The preserved baseline and isolated new work are disclosed; organizer acceptance and any rules outside this PDF remain external.

## 1-minute walkthrough recording script

Start on `/demo`, use the cached Angelman / UBE3A journey, and rehearse timing. This is a recording plan, not a timed study or a recorded video.

| Time | Screen / action | Narration |
| --- | --- | --- |
| 0–8 s | Search Angelman; visible Atlas | A rare-disease community needs a justified next step. MEDR5 starts with Angelman and its causal UBE3A deficiency. |
| 8–18 s | Inspect a sourced causal/model edge | This typed graph shows the source, relationship, evidence and uncertainty. Shared imprinting biology connects published research methods. |
| 18–29 s | Connections / shared assets | The Prader-Willi community has a related published cell-model approach. Different targets and a dosage-gain counterexample prevent unsupported treatment transfer. |
| 29–42 s | Therapeutic hypotheses | MEDR5 compares existing-medicine hypotheses by direction, coverage and spillover. One molecular axis is not the whole disease. Clinical safety remains a separate question. |
| 42–53 s | Next action; research brief / falsifier | The next step is a cited collaboration brief and an experiment that can falsify selective rescue. Model access and collaborators still need confirmation. |
| 53–60 s | Architecture / closing | OpenAI assists source-bound curation; MEDR5 reasons deterministically over the graph. Acceleration is a hypothesis to measure, not a clinical claim. |

The Team video is an additional deliverable named in the PDF; the brief provides no further format/content specification. Do not fabricate team identities or participation.
