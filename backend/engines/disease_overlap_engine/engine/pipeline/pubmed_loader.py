
from Bio import Entrez

Entrez.email = "local@localhost"

def load(term: str, retmax: int = 40):
    h = Entrez.esearch(db="pubmed", term=term, retmax=retmax)
    rec = Entrez.read(h)
    ids = rec.get("IdList", [])
    if not ids:
        return []

    f = Entrez.efetch(db="pubmed", id=",".join(ids), rettype="medline", retmode="text")
    raw = f.read()

    papers, cur, in_ab = [], [], False
    for line in raw.splitlines():
        if line.startswith("AB  -"):
            in_ab = True
            cur.append(line.replace("AB  -", "").strip())
        elif in_ab:
            if line.startswith("      "):
                cur.append(line.strip())
            else:
                papers.append(" ".join(cur))
                cur, in_ab = [], False
    if cur:
        papers.append(" ".join(cur))
    return papers
