# MEDR5 integration preview

This branch adds a deterministic, sourced research module to ConstellAI. Existing
atlas data, graph construction, CPLX1 → STXBP1 connections, evidence services and
hero UI are unchanged. No legacy backend imports, LLM calls, embeddings,
physiology, mimicry, repurposing priors or broad disease expansion are included.

## Isolated demo

The JSON endpoint is read-only and available independently of the UI flag:

```text
GET /api/disease/MONDO:0007113/therapeutics
GET /api/disease/MONDO:0007113/therapeutics?mechanism=ube3a-deficiency
GET /api/disease/MONDO:0007113/therapeutics?variant=VCV000155984.20
GET /api/disease/MONDO:0033372/therapeutics
```

Enable only the separate `/therapeutics` page (and its two whitelisted assets):

```powershell
$env:MEDR5_THERAPEUTICS_ENABLED = '1'
uv run uvicorn atlas.server:app --host 127.0.0.1 --port 8798
```

The flag defaults off. `/` serves the original hero page in both modes. There is
no new navigation item in the hero. Disabling the flag returns 404 for the preview
page and its assets, while keeping the read-only JSON endpoint available.

## Scientific contract

`adapter.py` joins an **exact MONDO disease ID and matching causal gene** to a
reviewed profile in `evidence.json`. It does not infer therapeutic direction from
inheritance, ClinVar pathogenicity, the existing gene-level effect heuristics,
shared pathways or an LLM. Variant IDs and mechanisms without reviewed functional
context return unknown and withhold ranking. The ClinVar example is an identity /
pathogenicity assertion, not a reviewed functional rescue direction.

Only the previously reviewed Angelman neuronal UBE3A-deficiency pilot is included:
topotecan is an existing oncology medicine with experimental **indirect UBE3A
expression** evidence; UBE3A-ATS antisense is a research comparator, not an approved
medicine or a named clinical ASO product. These relationships are not binding or
agonism predictions. Each effect has an ID, relation type, direction, context,
claim kind and reviewed source IDs. Paper records retain PMID, DOI where available,
journal, year, publication types, authors, source URL, study design, context-specific
sample size, claim and uncertainty. Registry validation checks the provenance
contract; it cannot certify the truth of a scientific claim.

The signed disease deviation is `-1` for loss / reduction and `+1` for gain /
increase. The desired intervention effect is the opposite sign. Desired matches
cover a target; opposite effects incur a penalty and withhold prioritisation.
Unknown never receives partial credit.

```text
known-effect fit = desired weighted coverage fraction
                - 0.85 × wrong-direction weight fraction
                - 0.22 × distinct listed off-signature mechanisms
add-on gain = newly covered remaining-axis weight fraction
            - 0.18 × redundant weight fraction
            - 0.20 × newly listed spillover mechanisms
            - 0.06 combination complexity
```

These constants come from the deterministic MEDR5 helper (`scoring.py`, legacy
commit `bdc2b5a258d0b4f4ef8f584e9c53f899a9b01ad3`). This extraction normalizes weights,
withholds unknown directions, deduplicates target counts, and rejects conflicting
effects. There is no reward for unrelated targets, no evidence-quality probability
and no journal-prestige weight. The selected comparator restores the same modeled
UBE3A axis, so it cannot be justified as an add-on in this pilot.

All scores describe **curated axes and listed effects only**. A single covered
axis is never interpreted as complete disease rescue. Spillover lists are incomplete;
their penalties are lower bounds. Clinical benefit, clinical risk, exposure, timing,
delivery, genotype-specific rescue and combination interactions remain unestablished.
Mechanistic fit, evidence strength and clinical safety evidence are separate outputs.
No dose or clinical treatment recommendation is generated.

## Validation

From the repository root, after installing the existing FastAPI/httpx dependencies:

```text
python -m unittest discover -s tests -v
node --check atlas/therapeutics/ui/panel.js
```

Tests cover signed directions, weighted desired coverage, wrong-way penalties,
off-signature penalties, missing/conflicting provenance, remaining deviation,
complementary closure, redundancy, exact disease mapping, unknown variants and
mechanisms, flag defaults, API errors and the existing hero graph/evidence contracts.
Pure-math fixtures are explicitly synthetic; they are never part of the biomedical
catalog or application response. The curated pilot is not a therapeutic validation
benchmark or a clinical decision tool.

Merge review should retain the flag's off default, review the limited source/context
claims and confirm existing demo behavior. Clinical applicability is a separate,
unresolved scientific question.
