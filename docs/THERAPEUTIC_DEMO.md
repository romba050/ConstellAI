# One-minute therapeutic research demo

Run `START_DEMO.cmd` on Windows, or `uv run uvicorn atlas.server:app --port 8800`.
Open http://127.0.0.1:8800. The demo reads its included curated evidence and needs
no API key, fresh literature search or graph rebuild. The optional OpenAI path
uses a server-side key and cannot change the deterministic score.

| Time | Action | Narration |
| --- | --- | --- |
| 0-8 s | Search STXBP1 and analyze | Maria needs a defensible research direction for her community. |
| 8-18 s | Read the gene/mechanism summary | Some STXBP1 changes disturb the protein that helps nerve cells release signals. Individual variants can behave differently. |
| 18-32 s | Inspect the leading hypothesis | We compare source-backed research hypotheses, keeping mechanism-targeting and symptom-targeting evidence distinct. |
| 32-42 s | Expand evidence and scoring | The sources, evidence type, safety gaps and arithmetic are inspectable. A research priority score is not a chance of clinical success. |
| 42-53 s | Open validation resources and next experiment | The community can discuss a proposed variant-matched assay with researchers and explore existing study infrastructure. Access and clinical decisions need expert validation. |
| 53-60 s | Enter an unreviewed variant or analyze CPLX1 | When the evidence cannot defend a candidate, the tool says so and shows the missing question. |

The CPLX1/STXBP1 atlas remains at `/atlas` for downstream pathway/community
exploration. Shared pathway evidence is never used to transfer treatment efficacy.
The official challenge also requests a Team video; recording and organizer
submission are external work. No team identities, videos or measured acceleration
are invented here.

## API and configuration

`POST /api/v1/analyze_disease` accepts:

```json
{"disease":"STXBP1","gene":null,"variant":null,"use_openai":false}
```

The frozen request/response schema is `docs/analyze-disease.schema.json` and is
also available through `/api/v1/schema`. `/?data=mock` uses `web/demo-analysis.json`
from the same response contract. `/api/v1/health` exposes configuration status
without credentials. Set `OPENAI_API_KEY` and optional `OPENAI_MODEL` in `.env`
on the server, then restart. The key is never requested by the frontend.

Weights are in `atlas/analysis/weights.json`. Six positive ratings receive weights
30/15/20/10/10/15. Four risk categories receive maximum penalties 15/10/10/15.
Toxicity and organ burden share one category using the larger severity. Missing
positive data receives zero; unknown risk receives its full penalty. The result
is clamped to 0-100. Ratings are documented curator judgments for research triage;
they are neither a calibrated model nor medical efficacy/safety estimates.

Unknown variants withhold rank. Source-specific variant findings cannot establish
an individual's genotype, allele context or response. Reviewed research hypotheses
require expert validation; source verification does not establish clinical readiness.

## Deployment and handoff

The existing Dockerfile serves the included graph and this new journey on port
7860, matching the ConstellAI Hugging Face Space configuration. GitHub delivery
uses a new branch based on current main. Deploy this branch's source to the Space
to replace the current public main-build UI; configuring the server secret is
separate from the branch upload. No public deployment is claimed without checking
the served code. The current local preview is sufficient for the challenge's
easy-to-run-prototype route.

Sources, corrections to draft claims and evidence boundaries are recorded in
`docs/EVIDENCE_REVIEW.md`. Engineering verification is in `docs/VERIFICATION.md`.

## Teammate: activate the key after upload

1. Copy `.env.example` to `.env` locally, or add `OPENAI_API_KEY` as a server
   secret on the deployment platform. Keep `.env` out of Git. Optionally set
   `OPENAI_MODEL`; the default is documented in `.env.example`.
2. Restart the server. Open `/api/v1/health` and confirm `openai_enabled` is true.
3. Analyze STXBP1, expand **Optional source-bound AI explanation**, and click
   **Generate source-bound explanation**. This is the explicit live API check.
   Inspect its provenance: `openai_verified` means approved source-excerpt checks
   passed; `fallback` states why no verified explanation was returned. The
   candidate scores, ranks and statuses must match the cached analysis.

The model classifies approved claims against supplied source excerpts. It does
not perform a fresh literature search or decide treatments. A valid but
uncertain result can fall back without changing the cached research result.
