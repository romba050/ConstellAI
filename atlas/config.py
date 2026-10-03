import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DATA = ROOT / "data"
RAW = DATA / "raw"
CACHE = DATA / "cache"
CURATED = DATA / "curated"
ATLAS_FILE = DATA / "atlas.json.gz"
CONTRIBUTIONS_FILE = DATA / "contributions.json"
WEB = ROOT / "web"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip()
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "").strip()

# Bulk files the graph builder needs. Everything else is fetched live per disease.
BULK_SOURCES = {
    "hp.obo": "https://purl.obolibrary.org/obo/hp.obo",
    "phenotype.hpoa": "https://purl.obolibrary.org/obo/hp/hpoa/phenotype.hpoa",
    "genes_to_disease.txt": "https://purl.obolibrary.org/obo/hp/hpoa/genes_to_disease.txt",
    "mondo.obo": "https://purl.obolibrary.org/obo/mondo.obo",
    "NCBI2Reactome.txt": "https://reactome.org/download/current/NCBI2Reactome.txt",
    "ReactomePathways.txt": "https://reactome.org/download/current/ReactomePathways.txt",
    "ReactomePathwaysRelation.txt": "https://reactome.org/download/current/ReactomePathwaysRelation.txt",
    "clingen_dosage.csv": "https://search.clinicalgenome.org/kb/gene-dosage/download",
}

# Similarity model (see README: "How diseases are connected").
W_PHENO, W_PATH = 0.65, 0.35
NO_PATHWAY_DISCOUNT = 0.8
KNN = 12
MIN_SCORE = 0.3
PHENO_GATE = 0.3
SPARSE_PHENOTYPES = 5
