# ConstellAI — an AI atlas for the world's rare diseases

*Hack-Nation 7th Global AI Hackathon · Challenge 05 (OpenAI × Buffalo Initiative)*

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

`data/atlas.json.gz` (4 MB) is included, so the build command can be skipped for a quick look.

Optional: copy `.env.example` to `.env` and set `OPENAI_API_KEY` to switch on the OpenAI steps (see below).
Without a key everything still works in deterministic "template mode", and the interface says which mode is active.

## A one-minute walkthrough

1. Search **CPLX1**. The gene resolves to *Developmental and epileptic encephalopathy, 63*: a disease with no
   dedicated patient group, no registered study and no NIH project. The Community tab says so plainly.
2. Open **Connections**. The top lead is the STXBP1 disease: both genes sit in the neurotransmitter-release
   (SNARE) pathways and patients share unusually informative seizure types.
3. Open that connection. The path *disease → gene → pathway → gene → disease* is drawn with a numbered evidence
   tag on every step; click a tag to see source, type (observed / inferred / curated), confidence and date.
4. **What must be checked**: inheritance differs (recessive vs dominant), and the variant-effect evidence for each
   gene is listed with ClinGen, ClinVar and quoted papers.
5. **What already exists**: the STXBP1 Foundation, a recruiting European trial-readiness study (NCT06625112) and two
   further natural-history studies, with sponsors, investigators and outcome measures.
6. **What to do this week**: who to write to, which protocol to ask for, the next experiment — and
   **Open the sourced proposal** to copy a ready-to-send, fully cited collaboration brief.

For the honest-gap path, open any star on the outer edge of the map (for example *NEUROG3*).

Switch **Viewing as** to change emphasis: Maria (connections and action), Devon (plain-language symptom names,
community first), Priya (search a mechanism to rank the clusters it touches), Dr. Osei (people first, and
"Scan the constellation" to find investigators who appear in several neighbouring communities).

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
| **Explain** | Turns a graph path into plain language for the selected persona | Every cited `[E#]` must be in the evidence ledger, or the text is discarded | Template built from the ledger |
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
