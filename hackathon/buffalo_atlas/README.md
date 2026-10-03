# MEDR5 Atlas — Buffalo hackathon edition

An atlas tells a rare-disease community what is known. MEDR5 Atlas connects the communities and evidence, then reasons over the biology to show what should be investigated next.

Built for Hack-Nation Global AI Hackathon 7, Challenge #5, AI Atlas for Rare Diseases. The six-page official challenge PDF supplied by the owner was reviewed on 2026-10-03; see [OFFICIAL_CHALLENGE_REVIEW.md](OFFICIAL_CHALLENGE_REVIEW.md). The original MEDR5 application remains intact.

## Run in one command

From the repository root, with Python 3.10 or newer:

```sh
python hackathon/buffalo_atlas/run.py
```

Open http://127.0.0.1:8795/demo. Windows users can double-click `START_BUFFALO_ATLAS.cmd`. Use `--port 8796` if the default port is occupied. Stop the terminal server with Ctrl+C. The server binds only to loopback. No package installation, frontend build, credentials or network call is required for the cached demo.

The four existing surfaces now use a dark palette, including the graph, controls, source inspector, dialogs and exports preview. Evidence type, study design, sample context and uncertainty remain distinct from numerical mechanistic priority.

Optional production build, with Node.js 18+ and npm:

```sh
cd hackathon/buffalo_atlas/frontend
npm ci
npm run build
```

The server uses `dist/` when present and serves the same source UI directly otherwise. Development with Vite needs the Python API; the supported complete demo command is the Python command above.

## Demo

Search **Angelman** or **UBE3A**. The **Atlas** opens a genuine typed graph with clickable sourced edges. Open **Connections / shared assets** for Family / Patient Group or Researcher explanations, the Angelman–Prader-Willi shared imprinting-model study, UBE3A dosage-gain counterexample and cited shared research brief. Then open **Therapeutic hypotheses** and finish on **Next action**. These are the only four major surfaces. The final scope is frozen.

Compare topotecan, a published UBE3A-ATS antisense perturbation and (S)-PHA533533. Only topotecan is the existing-medicine repurposing hypothesis; the other two are research comparators. See unresolved biology, non-redundancy gates, mechanistic surrogates and the cellular falsification experiment. Clinical safety evidence is a separate dimension throughout.

Four curated pilots: Angelman/UBE3A, CDKL5 deficiency, CACNA1A-related disorders and STXBP1-related disorder. Angelman has the deep end-to-end journey; the others provide cited biology, studies, groups and explicit ranking gates. The inherited 6,131-entry GARD catalog provides broader name discovery and includes non-monogenic conditions. It does not establish 6,131 validated monogenic mechanisms or therapies.

## Preserved technology and new work

Pre-existing: original MEDR5 source, the signed direction/add-on helpers in `backend/engines/rare_disease_mimic_engine/scoring.py`, and the GARD catalog. The preserved baseline is `old-sw` at `6d3ece8cc689a91d66a85356626e1899dfde9cde`, also tagged `pre-hackathon-medr5`.

New: this isolated Python API, cited snapshot, typed provenance graph, evidence gates, interpretable ranking adapter, four-surface UI with patient and researcher audience views, cross-community/model journey, counterexample, research brief exports, OpenAI Responses adapter, tests and documentation. No original frontend/backend source was rewritten.

## Data sources and reproducibility

The versioned `data/pilot_evidence.json` is a **curated snapshot of real cited public records**, not a fabricated biomedical database. It contains 39 source records and 11 PubMed-indexed papers with PMID, DOI, journal, indexed year, title, authors, publication types, paraphrased claim, study design, sample context and uncertainty. Publication notices are preserved. Literature has no journal allowlist; journal prestige and author identity do not increase mechanistic priority. BMJ, Journal of Internal Medicine, Cureus and other journals are eligible through PubMed indexing when their claims are relevant. There is no Ovid dependency or institutional-access requirement.

Core biology uses MONDO/HPO identifiers and a condition-specific ClinVar example with transcript and review scope. OMIM and Orphanet identifiers are verified cross-references; their direct licensed/blocked contents were not imported. A public NIH RePORTER project and investigators are linked to the hero graph as research aims, not therapeutic-effect evidence. ClinicalTrials.gov records remain dated registry snapshots. NORD, Global Genes, EURORDIS and verified official groups provide community navigation. Supplemental NLM disease references and DailyMed warnings are explicitly labelled. No registry access, partnership or patient records are invented. Details and access limits: [SOURCE_PROVENANCE.md](SOURCE_PROVENANCE.md).

From the repository root, rebuild the graph dataset and reasoning outputs with Python alone:

```sh
python hackathon/buffalo_atlas/tools/reproduce_dataset.py --output reproduced-dataset
```

Use a new or empty output directory. The tool validates sources and every graph, exports the exact curated inputs, source records, four typed graphs, deterministic reasoning and benchmark results, then writes a SHA-256 manifest. Two independent rebuilds have identical artifact hashes. No network, model call or credentials are needed. This reproduces the **reviewed curated slice and its derived dataset**; it does not claim fully automated discovery, source refresh or a systematic review. Human-curated claims and mapping decisions are the explicit versioned inputs.

Optional bibliography refresh into a separate review proposal:

```sh
python hackathon/buffalo_atlas/tools/refresh_pubmed_metadata.py --output pubmed-review.json
```

This reads only the current PMID slice from the public NCBI API, uses no journal filter, saves no copyrighted abstract/full text, and never changes the graph or scores. Review new claims, contradictions, variant context and registry status before editing curated inputs; refresh does not replace semantic review. Source URLs, retrieval queries and review receipts accompany the snapshot.

## Scoring and AI

Numerical scoring is deterministic: normalized signed causal-axis coverage minus wrong-direction, irrelevant/spillover and evidence-uncertainty penalties. Extra target count does not improve coverage. Unknown causal direction or missing evidence withholds ranking. Bundles must close a new supported axis and overcome redundancy/spillover; the curated demo produces no supported bundle. The product projects the cited typed graph into scoring inputs; removing a supporting edge withholds ranking. A separate disease-specific evidence prior is not added to mechanistic fit. Local frequent-flyer normalization discounts positive priority for many cited disease associations; polypharmacology already incurs spillover penalties. See [ARCHITECTURE.md](ARCHITECTURE.md) and [BENCHMARK_REPORT.md](BENCHMARK_REPORT.md).

OpenAI Codex assisted evidence curation, relationship drafting, family explanations and experimental-question drafting during development. Saved replay is labeled as saved replay. Runtime **Extract with OpenAI** uses server-side `OPENAI_API_KEY` with the Responses API and a strict structured schema; it accepts exact cited spans and allowed entities only. It does not change the graph or numerical scores. No key is committed or sent to the browser. Configure the key in the launching environment; optional `ATLAS_OPENAI_MODEL` defaults to `gpt-4.1-mini`. Live paid API execution was not verified because no key was available. An optional LM Studio-compatible local model is supported at 127.0.0.1:1234, with `ATLAS_LM_MODEL` for its model name.

## Validation and limits

```sh
python -m unittest discover -s hackathon/buffalo_atlas/tests -v
```

See [TEST_REPORT.md](TEST_REPORT.md), [SOURCE_PROVENANCE.md](SOURCE_PROVENANCE.md), [DEMO_SCRIPT.md](DEMO_SCRIPT.md) and [CHALLENGE_COMPLIANCE.md](CHALLENGE_COMPLIANCE.md).

Single curated molecular axis coverage is not whole-disease coverage. Source inspection and automated integrity checks are not independent clinical review. Exposure, dose, developmental timing, phenotype rescue and long-term tolerability are unresolved. Model availability and collaborator participation are unverified. No measured 10x improvement, clinical efficacy, diagnosis, treatment recommendation or combination safety is claimed. No patient records or outreach are handled. The PDF requires a Team video and a **1-minute walkthrough**; the recording script is prepared, but videos are not recorded/submitted. It requires OpenAI models **or tools**, not specifically a paid live API call. Codex development use and the unverified runtime adapter are disclosed separately; organizer acceptance remains external.

**Research decision support — not medical advice. Therapeutic hypotheses require experimental and clinical validation.**
