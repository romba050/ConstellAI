import requests
from Bio import Entrez
from tqdm import tqdm

def fetch_papers(drug, email, max_papers=50):
    Entrez.email = email
    handle = Entrez.esearch(db="pubmed", term=f"{drug} AND (mechanism OR pathway OR activation OR transcriptomic OR omics)", retmax=max_papers)
    record = Entrez.read(handle)
    id_list = record["IdList"]

    papers = []
    for pmid in tqdm(id_list, desc="Fetching abstracts"):
        handle = Entrez.efetch(db="pubmed", id=pmid, rettype="abstract", retmode="text")
        abstract = handle.read()
        papers.append({"pmid": pmid, "text": abstract})
    return papers