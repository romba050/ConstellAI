import time
import requests
from xml.etree import ElementTree

EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def fetch_pubmed(pmids, max_retries=3, backoff_seconds=2):
    """
    Fetch full PubMed records using EFETCH.
    Retries on transient HTTP 5xx errors.
    Never raises on failure – returns [] instead.
    """

    if not pmids:
        return []

    params = {
        "db": "pubmed",
        "id": ",".join(str(p) for p in pmids),
        "retmode": "xml",
    }

    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            r = requests.get(EFETCH_URL, params=params, timeout=60)

            if r.status_code >= 500:
                raise requests.HTTPError(
                    f"PubMed EFETCH {r.status_code}", response=r
                )

            r.raise_for_status()
            break

        except Exception as e:
            last_error = e
            print(f"[warn] pubmed fetch failed (attempt {attempt}/{max_retries}): {e}")

            if attempt < max_retries:
                time.sleep(backoff_seconds * attempt)
            else:
                print("[warn] pubmed fetch abandoned for pmid(s):", pmids)
                return []

    try:
        root = ElementTree.fromstring(r.text)
    except Exception as e:
        print("[warn] pubmed XML parse failed:", e)
        return []

    records = []

    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID")

        title = article.findtext(".//ArticleTitle") or ""
        abstract = " ".join(
            t.text.strip()
            for t in article.findall(".//AbstractText")
            if t.text
        )

        year = (
            article.findtext(".//PubDate/Year")
            or article.findtext(".//ArticleDate/Year")
        )

        pubtypes = [
            pt.text
            for pt in article.findall(".//PublicationType")
            if pt.text
        ]

        records.append({
            "pmid": pmid,
            "title": title,
            "abstract": abstract,
            "year": int(year) if year and year.isdigit() else None,
            "publication_type": pubtypes,
        })

    return records
