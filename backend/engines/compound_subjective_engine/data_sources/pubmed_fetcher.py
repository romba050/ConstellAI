from Bio import Entrez
from config import PUBMED_MAX_RESULTS

Entrez.email = "your@email.com"

def fetch_pubmed_data(query):
    handle = Entrez.esearch(db="pubmed", term=query, retmax=PUBMED_MAX_RESULTS)
    record = Entrez.read(handle)
    ids = record["IdList"]

    if not ids:
        return "No papers found."

    handle = Entrez.efetch(db="pubmed", id=ids, rettype="abstract", retmode="text")
    papers = handle.read()
    return papers
