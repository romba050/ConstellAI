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

# ConstellAI — an AI atlas for the world's rare diseases

*Hack-Nation 7th Global AI Hackathon · Challenge 05 (OpenAI × Buffalo Initiative)*

**Live demo:** https://romba050-constellai.hf.space (source: https://huggingface.co/spaces/romba050/ConstellAI)

ConstellAI is built for **Maria**, who leads the patient group for **STXBP1-related disorders**: a rare genetic
epilepsy and developmental disorder with no approved treatment. It answers her three questions:

1. **Which trials can our families join?** Every open study that mentions STXBP1, plus children's interventional
   trials for the epilepsies STXBP1 patients have, each screened by gpt-oss-120b against its eligibility text and
   filtered by the child's age and country.
2. **Who shares our biology?** STXBP1 sits on a map of 6,457 monogenic diseases grouped by shared symptoms and
   pathways rather than by name; every link to a neighbouring disease cites its source.
3. **What should we do this week?** Which group or study team to write to, what to check first, and a ready-to-send
   enquiry or sourced collaboration proposal.

If the evidence does not support something, the atlas says so: today, for example, no open drug or gene-therapy
trial names STXBP1, and the Trials tab states that before listing the broader trials that might accept it.

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

Optional: copy `.env.example` to `.env` and set `CEREBRAS_API_KEY` (gpt-oss-120b) or `OPENAI_API_KEY` to switch on
the AI steps (see below). Without a key everything still works in deterministic "template mode", and the interface
says which mode is active.

## Two pages

- **Dashboard (`/`)** — Maria's landing page for STXBP1:
  - **Knowledge graph**: diseases, genes, variants, mechanisms, symptoms, patient groups, papers, treatment studies
    and research assets around STXBP1. Click a dot for everything linked to it, or a line for the evidence behind
    that link. Each link sits on an evidence ladder: *observed* (database, registry or published statement),
    *inferred* (computed by ConstellAI), *hypothesis* (team curation not confirmed by a source we query) or
    *no data* (searched, nothing found).
  - **What to do this week**, with draft e-mails, and **every STXBP1 study as registered**: status, last update and
    enrolment, with a warning on records that are withdrawn, stopped, empty or not updated for a year.
  - **Pulse**: papers, preprints and study-record changes from the last 60 days, re-checked every 6 hours, with a
    one-line note per item by gpt-oss-120b (titles only, unreviewed).
  - **Trials your families could ask to join**, screened against eligibility text and filtered by age and country.
  - **What we searched**: each search, where, the count and the date. A zero means "none found in these sources".
- **Atlas (`/atlas`)** — the map of 6,457 monogenic diseases with STXBP1 selected. Click any star to open its
  connection to STXBP1: evidence path, what must be checked, reusable assets, a sourced proposal, and sliders to
  test the assumptions behind the 10× case.

## Architecture

```
atlas/
  sources.py   parsers for bulk files: HPO, HPO annotations, MONDO, Reactome, ClinGen
  build.py     Module 1 — reconcile → connect → score → cluster → layout → data/atlas.json.gz
  enrich.py    live evidence per disease: PubMed, ClinVar, ClinicalTrials.gov, NIH RePORTER, patient groups
  connect.py   Module 2+3 — evidence ledger, contradictions, checks, assets, actions, proposal
  trials.py    open trials for the focus disease, screened for eligibility; status flags for every study
  dashboard.py typed knowledge graph around the focus disease, evidence ladder, search ledger
  pulse.py     self-updating feed: fetchers, change detector, AI one-line notes
  seed.py      verifies the team's hand-curated papers against PubMed → data/curated/stxbp1_seed.json
  llm.py       AI steps: Extract, Reconcile, Explain, Screen (each with verification and a fallback)
  store.py     in-memory graph, global search with synonym resolution, entity views
  server.py    FastAPI: JSON API + static frontend
web/           no-build frontend: index.html + dashboard.js (dashboard), atlas.html + app.js (map), common.js
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
| **Explain** | Turns a graph path into plain language for the selected persona | Every cited `[E#]` must be in the evidence ledger, or the text is discarded | Template built from the ledger |
| **Name** | Gives colour groups short readable names at build time | Enrichment label is kept alongside | Enriched HPO terms |
| **Screen** | Reads each trial's eligibility criteria and decides whether an STXBP1 child could qualify, with a reason and extra requirements | The deciding criterion must be quoted verbatim or the quote is dropped; trials whose text names STXBP1 are always marked as such | Rules: gene restrictions in the title, gene named in the text |

The model is OpenAI's open-weight **gpt-oss-120b**, served by Cerebras (`CEREBRAS_API_KEY`). With only
`OPENAI_API_KEY` set, the same steps run on the OpenAI API (`OPENAI_MODEL`, default `gpt-5-mini`).

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
- The Cerebras key allows 5 requests per minute. Trial screening is batched (about 8 trials per call) and cached per
  trial version, but when several people open connections at once, explanations fall back to the template.
- Trial eligibility is screened from the text on ClinicalTrials.gov only. Lists kept on a study's own website (for
  example Simons Searchlight's gene list) are not seen.
- Nothing here is medical advice. An inferred link is a hypothesis, not evidence that a treatment exists.
