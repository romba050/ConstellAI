# backend/services/pubmed_client.py (FULL REPLACEMENT)
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import requests

from config import SETTINGS
from services.evidence_db import EvidenceDB


EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _common_params() -> Dict[str, str]:
    p = {"tool": SETTINGS.ncbi_tool, "email": SETTINGS.ncbi_email}
    if SETTINGS.ncbi_api_key:
        p["api_key"] = SETTINGS.ncbi_api_key
    return p


def search_pubmed(query: str, retmax: int = 10) -> Dict[str, Any]:
    """
    Returns {pmids: [...], total: int, cached: bool}.
    Cached in sqlite by query+retmax.
    """
    query = (query or "").strip()
    if not query:
        return {"pmids": [], "total": 0, "cached": False}

    db = EvidenceDB.get()
    cached = db.get_pubmed_search(query=query, retmax=retmax)
    if cached:
        return {"pmids": cached["pmids"], "total": cached["total"], "cached": True}

    params = {"db": "pubmed", "term": query, "retmax": str(retmax), "retmode": "json", **_common_params()}
    r = requests.get(f"{EUTILS}/esearch.fcgi", params=params, timeout=30)
    r.raise_for_status()

    js = r.json()
    es = js.get("esearchresult", {}) if isinstance(js, dict) else {}
    pmids = es.get("idlist", []) or []
    total = int(es.get("count", 0) or 0)

    db.put_pubmed_search(query=query, retmax=retmax, pmids=pmids, total=total)
    return {"pmids": pmids, "total": total, "cached": False}


def fetch_pubmed_abstracts(pmids: List[str]) -> List[Dict[str, Any]]:
    """
    Returns list of {pmid,title,abstract,journal,year,authors[]}.
    Uses efetch XML and stores in sqlite.
    """
    pmids = [p for p in (pmids or []) if str(p).isdigit()]
    if not pmids:
        return []

    db = EvidenceDB.get()

    cached = db.get_articles(pmids)
    cached_map = {a["pmid"]: a for a in cached}

    missing = [p for p in pmids if p not in cached_map]
    if missing:
        params = {"db": "pubmed", "id": ",".join(missing), "retmode": "xml", **_common_params()}
        r = requests.get(f"{EUTILS}/efetch.fcgi", params=params, timeout=45)
        r.raise_for_status()
        xml = r.text

        parsed = _parse_efetch(xml)
        for art in parsed:
            db.put_article(art)

        for art in parsed:
            cached_map[art["pmid"]] = art

    out = [cached_map[p] for p in pmids if p in cached_map]
    return out


def _parse_efetch(xml_text: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return out

    for article in root.findall(".//PubmedArticle"):
        pmid = _text(article.find(".//PMID")) or ""
        if not pmid:
            continue

        title = _text(article.find(".//ArticleTitle")) or ""
        abstract = " ".join([_text(x) or "" for x in article.findall(".//Abstract/AbstractText")]).strip()

        journal = _text(article.find(".//Journal/Title")) or ""
        year = _safe_int(_text(article.find(".//JournalIssue/PubDate/Year")))

        authors = []
        for a in article.findall(".//AuthorList/Author"):
            last = _text(a.find("LastName")) or ""
            fore = _text(a.find("ForeName")) or ""
            name = (fore + " " + last).strip()
            if name:
                authors.append(name)

        out.append(
            {
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "journal": journal,
                "year": year,
                "authors": authors,
            }
        )
    return out


def _text(node: Optional[ET.Element]) -> Optional[str]:
    if node is None:
        return None
    return "".join(node.itertext()).strip()


def _safe_int(x: Optional[str]) -> Optional[int]:
    try:
        return int(x) if x else None
    except Exception:
        return None