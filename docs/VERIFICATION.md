# Verification — 2026-10-04

This release is a working research prototype with one curated STXBP1 hero,
not a clinically validated treatment-ranking system. The new branch starts from
ConstellAI main `ad86a0a00ae870b604253b723f0acf766a41cb3f`.

## Engineering evidence

| Check | Observed result |
| --- | --- |
| Python API and ranking suite | 31/31 passed with `python -m unittest discover -s tests -v`. |
| Fresh source export | All 31 checks and JS syntax passed again from an export of the staged source without `.git`, `.env` or cache files. A separate fresh server became ready in 2.379 s; real HTTP hero/fixture parity and both primary/atlas pages passed. |
| Frozen contract | Public schema equals `docs/analyze-disease.schema.json`; production response equals `web/demo-analysis.json`. |
| Deterministic scoring | Tested known arithmetic, missing data, shared toxicity/organ penalty, clamping, stable ties, and evidence/status gates. |
| Evidence integrity | Production ledger has 13 source records; references resolve. Corrupt references withhold analysis with a sanitized 503. Primary-source review and scope limits are in `EVIDENCE_REVIEW.md`. |
| Abstention | Unknown disease, conflicting gene, ambiguous identity, CPLX1 and every nonempty unreviewed variant withhold a leading hypothesis. |
| Responses integration | Mocked transport through the public API verifies strict `text.format` JSON schema, refusal/incomplete/invalid output fallback, exact quote and source checks, timeout/no retries, sanitized logs, and unchanged scores/statuses/medical text. |
| No-key operation | Actual local health reports `openai_enabled: false`; included evidence and ranking remain available. No live paid OpenAI call was made. |
| Frontend | JavaScript syntax passed. Actual browser checked desktop live and mock, mismatch rejection, mobile variant and CPLX1 gaps, and expandable score audit. No browser warnings/errors observed. |
| Dark responsive layout | Desktop override 1280 x 900 and mobile 390 x 844. Document width stays within the viewport; the audit table scrolls within its own labelled region. |
| Complete hero render | An actual analyze-button click rendered the complete hero, including proposed experiment, in 340 ms locally. This measures application rendering, not a timed user comprehension study. |
| API latency | Five local hero requests: 111.74, 124.48, 105.85, 72.51 and 71.86 ms. No external retrieval/key was required. |
| Existing atlas | `/atlas` renders the original 6,457-disease canvas; original atlas, disease and gene APIs pass regression checks. |
| Source preservation | Nine assets have no Git content changes from main: original app JS/CSS/D3, graph binary, patient organisations, store, connection and enrichment modules, and Dockerfile. Text comparisons account for Git's CRLF checkout conversion; the graph binary is byte-identical. |
| Dependency metadata | OpenAI minimum is 2.26.0, supporting Responses. Project and frozen-lock metadata agree; existing lock pins 3.24.0. Runtime tests used OpenAI 2.26.0, FastAPI 0.135.3, Pydantic 2.12.3 and Python 3.12.10. |

## Medical interpretation limits

Two candidates remain **research hypotheses**, with heuristic scores 27 and 24.25.
Compound 13 is **insufficient evidence** and unranked. No `supported_candidate`
is claimed. Any supplied variant is unreviewed and removes all ranks. These
scores express disclosed curator ratings, never efficacy, safety, response
probability or an individual treatment decision.

Free 4-PBA, sodium phenylbutyrate and glycerol phenylbutyrate must remain distinct.
Human observations are uncontrolled, mixed or contradictory. Related CPLX1
biology does not establish shared therapeutic response. Published models,
registries and organisations establish potential research resources, not
collaboration, participant eligibility, material access or a completed experiment.

## External checks still pending

The teammate will add the server-side API key after GitHub upload. A real
Responses request and any provider/model/account permissions remain unverified.
Follow the activation steps in `THERAPEUTIC_DEMO.md`; fallback is intentional
when the call cannot be verified.

The software is running locally and packaged for an easy-to-run prototype.
The existing public Hugging Face Space has not been updated by this release.
Its Docker configuration is retained, but an actual Docker image build and
Space deployment were not tested here (Docker and an authenticated Space
deployment credential were unavailable). Legacy atlas enrichment still depends
on its original live-source/cache behaviour; the primary hero uses the included
curated snapshot. Video recording and organizer submission are team actions.
