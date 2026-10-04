"""Hand-curated seed evidence for the STXBP1 dashboard, verified against PubMed.

    uv run python -m atlas.seed

The biomedical team supplies citations and what each one supports. This script
looks every title up in PubMed and writes data/curated/stxbp1_seed.json with the
PMID, journal and year PubMed returns. A citation that cannot be matched is kept
out of the graph and listed under `unresolved`.
"""
import datetime
import json
import re

from .config import CURATED
from .enrich import ncbi

FILE = CURATED / "stxbp1_seed.json"

# title, short label, the graph node it supports, relation, and the claim as the team summarised it
PAPERS = [
    ("De novo mutations in the gene encoding STXBP1 (MUNC18-1) cause early infantile epileptic encephalopathy",
     "Saitsu 2008", "d:focus", "first reported the gene–disease link",
     "Original report that de novo STXBP1 variants cause early infantile epileptic encephalopathy."),
    ("Protein instability, haploinsufficiency, and cortical hyper-excitability underlie STXBP1 encephalopathy",
     "Kovacevic 2018", "m:haploinsufficiency", "supports the mechanism",
     "Patient variants make the Munc18-1 protein unstable and lower its cellular level."),
    ("Stxbp1/Munc18-1 haploinsufficiency impairs inhibition and mediates key neurological features of STXBP1 encephalopathy",
     "Chen 2020", "a:mouse", "describes the mouse model",
     "Mice with one working Stxbp1 copy show seizures and cognitive, psychiatric and motor problems."),
    ("SNAREopathies: Diversity in Mechanisms and Symptoms",
     "Verhage & Sørensen 2020", "m:snare", "reviews the shared mechanism",
     "Reviews diseases of the synaptic vesicle fusion machinery together, including STXBP1 and CPLX1."),
    ("Genes that Affect Brain Structure and Function Identified by Rare Variant Analyses of Mendelian Neurologic Disease",
     "Karaca 2015", "g:CPLX1", "first reported CPLX1 variants",
     "First report of homozygous loss-of-function CPLX1 variants in families with neurologic disease."),
    ("Variants in CPLX1 in two families with autosomal-recessive severe infantile myoclonic epilepsy and ID",
     "Redler 2017", "g:CPLX1", "second independent report",
     "Homozygous CPLX1 variants in two unrelated families; recessive inheritance."),
    ("STXBP1 encephalopathy: A neurodevelopmental disorder including epilepsy",
     "Stamberger 2016", "d:focus", "describes the patient cohort",
     "Cohort study of the symptoms and seizure types in STXBP1 encephalopathy."),
    ("Mechanism-based rescue of Munc18-1 dysfunction in varied encephalopathies by chemical chaperones",
     "Guiberson 2018", "m:dominant_negative", "reports a second mechanism and a chaperone approach",
     "Some variants act dominant-negatively; chemical chaperones restored protein levels in models."),
]

# Presynaptic release-machinery genes the team wants on the map (from the SNAREopathies review).
SNARE_GENES = ["CPLX1", "STX1B", "SNAP25", "VAMP2", "SYT1", "STX1A", "UNC13A", "RIMS1", "STXBP6"]
# Studies to always show, whatever their status.
STUDIES = ["NCT06555965", "NCT06625112", "NCT05462054", "NCT06983158", "NCT04937062"]


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def resolve(title):
    ids = ncbi("esearch", db="pubmed", term=f"{title}[Title]", retmode="json", retmax=5).json()["esearchresult"].get("idlist", [])
    if not ids:
        return None
    summ = ncbi("esummary", db="pubmed", id=",".join(ids), retmode="json").json()["result"]
    for pmid in ids:
        r = summ[pmid]
        if norm(r["title"]).startswith(norm(title)[:60]):
            return {"pmid": pmid, "title": r["title"].rstrip("."), "journal": r.get("source", ""),
                    "year": r.get("pubdate", "")[:4], "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"}
    return None


def main():
    papers, unresolved = [], []
    for title, label, target, relation, claim in PAPERS:
        hit = resolve(title)
        if hit:
            papers.append({**hit, "label": label, "supports": target, "relation": relation, "claim": claim})
            print("ok ", label, hit["pmid"], hit["journal"], hit["year"])
        else:
            unresolved.append({"label": label, "title": title})
            print("-- ", label, "not matched in PubMed")
    FILE.write_text(json.dumps({
        "about": "Seed evidence curated by the team's biomedical member. PMIDs, journals and years come from PubMed; "
                 "the one-line claims are the team's summaries and should be checked against the papers.",
        "verified": datetime.date.today().isoformat(),
        "papers": papers, "unresolved": unresolved, "snare_genes": SNARE_GENES, "studies": STUDIES,
    }, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
