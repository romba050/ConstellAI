# Verification — 2026-10-04, literature and graph revision

This working research prototype has two reviewed disease contexts and one curated STXBP1 therapeutic hero. It is not a clinically validated ranking system. Branch `therapeutic-hypotheses-demo` starts from ConstellAI main `ad86a0a00ae870b604253b723f0acf766a41cb3f`.

## Engineering evidence

| Check | Observed result |
| --- | --- |
| Fresh source export | 44/44 Python checks and syntax checks for both frontend scripts passed from an export of staged source without `.git`, `.env` or cache files. A separate server became ready in 2.438 s; actual HTTP schema/fixture parity and primary/atlas pages passed. The temporary server was closed afterward. |
| Frozen contract | `constellai-analysis-v2` includes the typed `knowledge_graph`. Public schema equals `docs/analyze-disease.schema.json`; actual production response equals `web/demo-analysis.json`. |
| Deterministic scoring | Known arithmetic, missing data, shared toxicity/organ penalty, clamping, stable ties and evidence/status gates are tested. The model cannot alter medical facts, ratings, ranks or statuses. |
| Native reference | The separate Literature reviews tab was read: six native tabs, 374 targeted paragraphs. More than 50 material groups are mapped to implemented, corrected/excluded or deferred decisions in `LITERATURE_REVIEW_TRACEABILITY.md`. |
| Evidence integrity | The ledger contains 21 reviewed source records and two disease profiles. Invalid source references, unsafe URLs or graph endpoints withhold analysis with a sanitized 503. Primary-source scope is documented in `EVIDENCE_REVIEW.md`. |
| Therapeutic graph | Actual STXBP1 response: 47 entities, 88 edges, 21 sources, all 12 contract entity types. Edges expose claim provenance, relationship, qualitative confidence basis, observed/inferred/unknown status, scope and contrasting findings. |
| CPLX1 graph and gap | Actual CPLX1 response: 44 entities, 85 edges and six sources; zero therapeutic candidates or candidate nodes. Its reviewed biology remains visible without borrowing STXBP1 drug evidence. |
| Variant boundary | Unknown disease, conflicting gene, ambiguous identity and every nonempty entered variant withhold a leading hypothesis. A typed G544D remains unreviewed and separate from the same-name published example; all ranks are withheld. |
| Original HPO annotations | Only inherited atlas phenotype annotations with exact reviewed PMID references are projected: 13 STXBP1 and 31 CPLX1 phenotype nodes. These remain disease annotations, not newly adjudicated patient observations. |
| Responses integration | Mocked public-API transport verifies strict `text.format` JSON schema, refusal/incomplete/invalid-output fallback, exact quote/source checks, timeout/no retries, sanitized logs and unchanged scores/statuses/medical text. |
| No-key operation | Actual preview and fresh server health report `openai_enabled: false`. Included evidence, graph and ranking remain available. No real provider call was made. |
| Actual browser | Twenty checks cover graph pointer/keyboard controls, source/contrary-evidence inspector, entity filtering/search, literature-to-claim mapping, live/mock parity, mismatch recovery, CPLX1/variant abstention, Maria-only atlas, preserved disease tabs, mobile header and map resizing. No warnings/errors were observed. |
| Dark responsive UI | Desktop 1280 × 900 and mobile 390 × 844 were checked. Mobile document width was 375 px; graph width stayed inside it. The score table scrolls within its own container. Temporary viewport overrides were reset. |
| Interaction repairs | Horizontal SVG edges have nonzero control bounds and keyboard focus outlines. Global scrolling uses `auto` for stable control activation. Atlas resizing preserves the constellation; narrow grid/panel layouts contain tabs, long text and Reset view. Actual mobile and SVG interactions passed after the repairs. |
| Complete hero render | An actual analyze-button click rendered the complete hero, including the proposed experiment, in 325 ms locally. This measures application rendering, not user comprehension or 10× research acceleration. |
| API latency | Five actual local hero requests: 72.22, 68.83, 71.77, 69.79 and 70.66 ms. No external retrieval or provider key was required. |
| Existing atlas | `/atlas` renders the original 6,457-disease canvas. Original atlas, disease and gene API regression checks pass. |
| Source preservation | Seven assets have no Git content changes from main: D3, graph binary, patient organisations, store, connection/enrichment modules and Dockerfile. Atlas HTML/JS/CSS were adapted for the requested Maria-only view; original versions remain in Git and the prior release package. Package comparisons account for Git CRLF checkout conversion; the graph binary is byte-identical. |
| Dependency metadata | OpenAI minimum is 2.26.0, supporting Responses; project and frozen-lock metadata agree, with lock pin 3.24.0. Tests used OpenAI 2.26.0, FastAPI 0.135.3, Pydantic 2.12.3 and Python 3.12.10. |

## Medical interpretation limits

Levetiracetam and phenylbutyrate remain **research hypotheses**, with heuristic scores **28.25** and **27**, respectively. Reading the reviewed Kovacevic mouse study replaced an unknown levetiracetam preclinical input with a disclosed curator rating of 0.40; weights and all other ratings were unchanged. The small score difference is uncalibrated and establishes no therapeutic superiority. Compound 13 scores 5.5 but is **insufficient evidence** and unranked. No `supported_candidate` is claimed. Any supplied variant removes all ranks.

Mouse seizure suppression, protein/function rescue and human clinical outcomes are different endpoints. Free 4-PBA, sodium phenylbutyrate and glycerol phenylbutyrate remain distinct. Human observations are uncontrolled, mixed or contradictory. Shared CPLX1 biology does not establish shared drug response. Published models, investigator identities, registries and organisations establish research context, not collaboration, participant eligibility, material access or a completed experiment. CAP-002 is dated historical terminated context, not a recruiting resource or a proof of class-wide contraindication.

## External checks still pending

The teammate will add the server-side API key after GitHub upload. A real Responses request and provider/model/account permissions remain unverified. Follow the activation steps in `THERAPEUTIC_DEMO.md`; fallback is intentional when a response cannot be verified.

The software runs locally and is packaged as an easy-to-run prototype. The existing public Hugging Face Space has not been updated. Its Docker configuration is retained, but an actual Docker build and Space deployment were not tested here. Legacy atlas enrichment retains its original live-source/cache behavior; the primary hero uses the included curated snapshot. The 10× workflow thesis is explicitly unmeasured; video recording, expert validation and organizer submission remain team actions.
