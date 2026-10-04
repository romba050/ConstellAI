---
title: ConstellAI
emoji: ✨
colorFrom: indigo
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
short_description: An AI atlas for the world's rare diseases
---

# ConstellAI — sourced therapeutic research hypotheses

*Hack-Nation 7th Global AI Hackathon · Challenge 05 (OpenAI × Buffalo Initiative)*

**Existing public atlas:** https://romba050-constellai.hf.space (source: https://huggingface.co/spaces/romba050/ConstellAI).
This branch adds the therapeutic journey below; deploy this branch to the Space to publish it.

## Therapeutic journey (this branch)

**Disease → gene/variant → mechanism → evidence graph → evidence and safety ranking → research hypothesis
→ related disease/community evidence → next experiment.** The default screen is a dark,
plain-language journey for Maria, a patient-organisation leader. The deep reviewed hero is
STXBP1; CPLX1 demonstrates sourced biology with an explicit therapeutic evidence gap.
Broad atlas coverage does not imply broad therapeutic validation.

Run `START_DEMO.cmd` on Windows, or `uv run uvicorn atlas.server:app --port 8800` and open
http://127.0.0.1:8800. The reviewed evidence snapshot runs without a key or fresh API calls;
Pulse separately checks public sources in the background while the server runs.
For the small cached-demo runtime only: `python -m pip install -r requirements-demo.txt`, then
`python -m uvicorn atlas.server:app --port 8800`. Full graph-building dependencies remain in
`pyproject.toml` and `uv.lock`; the included graph avoids rebuilding for the demo.

`POST /api/v1/analyze_disease` accepts `disease`, optional `gene`, optional `variant` and
`use_openai`. The frozen `constellai-analysis-v2` schema is in `docs/analyze-disease.schema.json`. The frontend mock
at `/?data=mock` uses the same contract. The original map and CPLX1/STXBP1 journey remain
available at `/atlas`, downstream from the therapeutic analysis. Both views focus
on Maria; the atlas has no other persona switcher or stored audience preference.

The reviewed evidence graph connects disease, gene, published or unresolved variant,
mechanism, pathway, phenotype, candidate, paper, study, organisation, investigator and
research asset. Expand the map or select an edge to inspect relationship type, source,
qualitative confidence, observed/inferred status, scope and contrasting evidence.
Graph projection validates endpoints and citations before returning results. Existing
HPO annotations enter only when their exact paper reference resolves to the reviewed ledger.

The Google Doc's **Literature reviews** tab is traced into the source ledger and assessments.
The UI's literature review groups sources by evidence type and maps them to the claims they
support, study limitations and contrasting findings. See
[tab-to-software traceability](docs/LITERATURE_REVIEW_TRACEABILITY.md) for included,
corrected and deferred reference material.

Six configurable positive components minus four risk penalties determine the 0-100 research
priority index. Every component, missing-data policy and source is inspectable. Unknown
variants withhold rank; unsupported cases can return **“No defensible therapeutic candidate found.”**
This index is a disclosed curator heuristic, not an efficacy probability or prescribing tool.
Mechanism targeting, symptom targeting, human evidence and preclinical models stay distinct.

Optional OpenAI support uses the **Responses API** with strict Structured Outputs, server-side
`OPENAI_API_KEY`, verified source excerpts and deterministic ranking. A teammate can add the
key in `.env` or the deployment environment and restart the server after upload. The key
must never enter frontend code. Transport tests do not establish a successful live paid API call.

The acceleration thesis is to assemble identity, mechanism, connected evidence, candidate
comparison, safety gaps and a validation plan in one workflow. A **10× improvement is a
hypothesis to measure**, not a measured result. Expert review, experiments, ethics,
funding and partner response remain external. Patient organisations and researchers gain
an auditable research direction and a concrete question for their next discussion.

See [the one-minute demo and deployment handoff](docs/THERAPEUTIC_DEMO.md),
[primary evidence and draft corrections](docs/EVIDENCE_REVIEW.md),
and [engineering verification](docs/VERIFICATION.md). [Mandatory challenge coverage and video handoff](docs/CHALLENGE_SUBMISSION.md)
maps all six PDF pages to concrete capabilities and remaining submission actions. [Judging readiness](docs/JUDGING_READINESS.md)
maps the implemented journey and its limits to the challenge criteria. Run tests with
`python -m unittest discover -s tests -v`.

## Six-hour Pulse

Pulse checks a bounded STXBP1/CPLX1 watchlist through public Europe PMC and
ClinicalTrials.gov APIs every six hours while the server is running and the host is awake.
The dark discovery feed shows source links, record changes and source-specific fetch dates
or failures. New records mean **new to this watchlist**, not necessarily newly published.
Every discovery stays **unreviewed** and never changes the reviewed graph, evidence,
research scores or ranks automatically.

Use `START_DEMO.cmd` or the server command above; no provider API key is needed.
`GET /api/v1/pulse` returns the saved snapshot, with optional `?gene=STXBP1` or
`?gene=CPLX1` and a bounded `limit`. Browsing the feed does not trigger provider or model
calls. Keep the server running for scheduled checks; shutdown, sleep or a stopped hosting
instance pauses them. The reviewed ledger date and the latest Pulse fetch are separate.

Set `CONSTELLAI_PULSE_ENABLED=0` in the server environment or `.env` and restart to disable
scheduled checks. Optional AI drafts require `CONSTELLAI_PULSE_AI_ENABLED=1` plus the
server-side `OPENAI_API_KEY`; this is disabled by default and handles at most three paper
abstracts per run. Accepted literal quotes still require human review.

The paper search covers a rolling 90-day publication window with capped pagination.
The watchlist includes STXBP1, CPLX1, MUNC18-1, complexin-1 and exact historical study IDs.
This is discovery assistance, not exhaustive monitoring, trial eligibility or a weekly email.
See [Pulse operation and coverage](docs/PULSE.md) for the separate contract, timestamp
semantics, provider limits and recovery behavior.

Operator one-shot: `python -m atlas.pulse --once` obeys the saved interval;
`--export <path>` saves up to 5,000 discovery items. Explicit `--once --force` bypasses
timing/enablement for bootstrap or recovery while retaining the process lease.
Runtime state is `data/cache/pulse/state.sqlite3` and is ignored by Git. A valid
`data/curated/pulse-bootstrap.json` can seed a fresh cache with its original dates
and unreviewed status; it does not imply a new fetch.

## Existing atlas

Five thousand scattered points of light, one map to see the constellations. ConstellAI places **6,457 monogenic
diseases** on one map, grouped by shared symptoms and shared pathways rather than by name. A patient-group leader
types a disease, gene, symptom, mechanism or organisation into one search box and is carried to:

1. **a supported connection** — the closest diseases, with every edge citing its source;
2. **an existing asset** — registries, natural-history studies, trials, grants and models that already exist;
3. **a collaborator** — the patient group, lead investigator or shared key opinion leader;
4. **a concrete next step** — what to check first, who to write to this week, and a sourced proposal to send.

If no supported route exists, the atlas says so, shows what was searched and what evidence would change the answer.

## Run it

Requires [uv](https://docs.astral.sh/uv/) and Python ≥ 3.11.

```bash
uv sync
uv run python -m atlas.build                  # downloads public sources (~140 MB) and builds data/atlas.json.gz, ~1 min
uv run uvicorn atlas.server:app --port 8000   # open http://localhost:8000
```

Or with Docker (the same image the live demo runs):

```bash
docker build -t constellai . && docker run --rm -p 7860:7860 constellai   # open http://localhost:7860
```

`data/atlas.json.gz` (4 MB) is included, so the build command can be skipped for a quick look.

Optional: copy `.env.example` to `.env` and set `OPENAI_API_KEY` to switch on the OpenAI steps (see below).
Without a key everything still works in deterministic "template mode", and the interface says which mode is active.

## A one-minute walkthrough

1. Search **CPLX1** in `/atlas`. The gene resolves to *Developmental and epileptic encephalopathy, 63*.
   The Community tab shows retrieved records and evidence gaps; an empty search does not establish that no resource exists.
2. Open **Connections**. The top lead is the STXBP1 disease: both genes sit in the neurotransmitter-release
   (SNARE) pathways and patients share unusually informative seizure types.
3. Open that connection. The path *disease → gene → pathway → gene → disease* is drawn with a numbered evidence
   tag on every step; click a tag to see source, type (observed / inferred / curated), confidence and date.
4. **What must be checked**: inheritance differs (recessive vs dominant), and the variant-effect evidence for each
   gene is listed with ClinGen, ClinVar and quoted papers.
5. **What already exists**: inspect the STXBP1 Foundation and linked studies, their sources, sponsors and outcome
   measures. The reviewed therapeutic journey separately records dated current and historical registry statuses.
6. **What to do this week**: who to write to, which protocol to ask for, the next experiment — and
   **Open the sourced proposal** to copy a ready-to-send, fully cited collaboration brief.

For the honest-gap path, open any star on the outer edge of the map (for example *NEUROG3*).

The atlas focuses on **Maria**, a patient-organisation leader: connections, reusable assets and the next research
step. Biology, Community and People remain available as supporting research tabs within her journey.

## Architecture

```
atlas/
  sources.py   parsers for bulk files: HPO, HPO annotations, MONDO, Reactome, ClinGen
  build.py     Module 1 — reconcile → connect → score → cluster → layout → data/atlas.json.gz
  enrich.py    live evidence per disease: PubMed, ClinVar, ClinicalTrials.gov, NIH RePORTER, patient groups
  connect.py   Module 2+3 — evidence ledger, contradictions, checks, assets, actions, proposal
  llm.py       OpenAI steps: Extract, Reconcile, Explain (each with verification and a fallback)
  store.py     in-memory graph, global search with synonym resolution, entity views
  server.py    FastAPI: JSON API + static frontend
web/           no-build frontend: canvas constellation map (D3 zoom/quadtree) + evidence panel
data/curated/patient_orgs.json   hand-curated patient organisations and cross-disease registries
```

### The graph

| Node | Identifier | Source |
|---|---|---|
| Disease | MONDO (OMIM and Orphanet records merged through equivalence xrefs) | MONDO, HPOA |
| Gene | HGNC symbol / NCBI Gene | OMIM gene–disease map via HPO `genes_to_disease` |
| Variant-effect profile | per gene | ClinGen dosage, ClinVar consequence counts, literature claims |
| Mechanism | Reactome pathway | Reactome |
| Symptom | HPO term | HPO annotations |
| Paper, claim, investigator | PMID | PubMed (live) |
| Study / registry / trial | NCT number | ClinicalTrials.gov (live) |
| Grant | NIH project number | NIH RePORTER (live) |
| Patient organisation, registry | URL | curated list + ClinicalTrials.gov sponsors |

Every edge carries **source, date, confidence and kind** (`observed`, `curated` or `inferred`). Symptom edges keep
the HPO evidence code, frequency, reference (PMID/OMIM) and curation date. Similarity edges are always `inferred`.

### How diseases are connected

- **Symptom similarity**: IC-weighted cosine over HPO terms propagated to their ancestors. Information content is
  computed over all 10,737 annotated diseases, so "seizure" counts for little and "epileptic spasm" for a lot.
- **Mechanism similarity**: the same measure over the Reactome pathways of the causal genes.
- **Score** = 0.65 × symptoms + 0.35 × pathway × gate, where the gate fades the pathway term out when patients do
  not look alike. This is what keeps *same gene, different effect* diseases apart instead of merging them by name.
  Genes with no curated pathway are scored on symptoms alone, discounted by 0.8.
- **Clusters**: 12-nearest-neighbour graph (score ≥ 0.3) → Leiden communities at two resolutions (colour groups,
  then clusters inside each). The map layout is UMAP on the same similarity matrix.
- **Triage**: each link is graded *viable*, *speculative*, *thin data* or *unsupported*, and the connection view
  adds a PubMed co-mention count to show whether anyone has written the connection down before.

### Built with OpenAI

| Step | What the model does | How its output is checked | Without a key |
|---|---|---|---|
| **Extract** | Reads abstracts, returns variant-effect and asset claims as structured JSON | The quote must appear verbatim in the cited abstract, or the claim is dropped | Sentence-level pattern matching |
| **Reconcile** | Maps a lay or misspelled query to candidate names | Only candidates that exist in the atlas vocabulary are accepted | Synonym index only (MONDO, OMIM, Orphanet, HPO) |
| **Explain** | Turns a graph path into plain language for Maria | Every cited `[E#]` must be in the evidence ledger, or the text is discarded | Template built from the ledger |
| **Name** | Gives colour groups short readable names at build time | Enrichment label is kept alongside | Enriched HPO terms |

The model defaults to `gpt-5-mini` and is set with `OPENAI_MODEL`.

## Reproducing the dataset

`uv run python -m atlas.build --refresh` re-downloads every bulk source and rebuilds. URLs are in
`atlas/config.py`; release versions are written into the atlas metadata and shown in the interface. The live
layer is fetched per disease on first view and cached for seven days in `data/cache/`.
`uv run python -m atlas.check_orgs` re-checks that every curated organisation website still resolves.

## The 10× case

**Milestone:** two communities enrolling into one natural-history protocol with shared outcome measures.

| Step | Alone | With the atlas |
|---|---|---|
| Find a mechanistically related community | 6–12 months | minutes |
| Registry and data model | 12–18 months | weeks: join the partner's or an open registry |
| Protocol and outcome measures | 9–12 months | 4–8 weeks: adapt an existing protocol |
| First patient enrolled | 3–6 months | 4–8 weeks as an amendment |
| **Total** | **≈ 40 months** | **≈ 4 months** |

These durations are planning estimates, not measurements. The acceleration assumes the partner shares its
protocol, the outcome measures are valid in both diseases, ethics boards accept an amendment, and the
variant-effect check passes. Validating those four assumptions on one real pair is the next step.

## Limits

- Pathway coverage is incomplete: 1,307 diseases have no Reactome pathway and are linked on symptoms only.
- 945 diseases have fewer than five recorded symptoms; their links are flagged as thin data.
- Investigators are matched by surname and first initial; overlaps are name-level and must be verified.
- The variant-effect call is made per gene, so genes with both loss- and gain-of-function diseases show as
  variant-dependent.
- The patient-organisation list is hand-curated (87 entries) and only website liveness is checked automatically.
- The OpenAI path was written against the API but not exercised in this build, because no key was available.
- Nothing here is medical advice. An inferred link is a hypothesis, not evidence that a treatment exists.
