from Bio import Entrez
from Bio import Medline

def fetch_pubmed(field, sub_field, email, retmax=500):
    Entrez.email = email

    query = (
        f'({field}[Title/Abstract]) AND '
        f'({sub_field}[Title/Abstract])'
    )

    h = Entrez.esearch(db="pubmed", term=query, retmax=retmax)
    r = Entrez.read(h)
    pmids = r.get("IdList", [])

    if not pmids:
        return []

    h = Entrez.efetch(db="pubmed", id=pmids, rettype="medline", retmode="text")
    records = Medline.parse(h)

    papers = []
    for rec in records:
        if "PMID" not in rec:
            continue
        papers.append({
            "pmid": rec.get("PMID", ""),
            "title": rec.get("TI", "") or "",
            "abstract": rec.get("AB", "") or "",
            "journal": rec.get("JT", "") or "",
            "year": (rec.get("DP", "") or "")[:4]
        })

    return papers
