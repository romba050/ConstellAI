"""Pulse: what changed recently for the focus gene, so the dashboard updates itself.

watchlist term -> fetchers (ClinicalTrials.gov, PubMed, Europe PMC preprints, a watched
web page) -> change detector (ids and page hash seen before) -> one-line AI summary ->
feed. Items are machine-collected and unreviewed; each links to its source.
"""
import datetime
import hashlib
import json
import re
import threading

from . import llm
from .config import CACHE
from .enrich import HTTP, ncbi

FILE = CACHE / "pulse.json"
WINDOW_DAYS = 60
WATCHED_PAGES = [("STXBP1 Foundation: clinical trials and research", "https://www.stxbp1disorders.org/clinicaltrialsandresearch")]
_lock = threading.Lock()


def _studies(gene, since):
    r = HTTP.get("https://clinicaltrials.gov/api/v2/studies", params={
        "query.term": f"{gene} AND AREA[LastUpdatePostDate]RANGE[{since},MAX]", "pageSize": 30,
        "fields": "NCTId,BriefTitle,OverallStatus,LastUpdatePostDate"})
    r.raise_for_status()
    out = []
    for s in r.json().get("studies", []):
        p = s["protocolSection"]
        nct, st = p["identificationModule"]["nctId"], p["statusModule"]
        date = st.get("lastUpdatePostDateStruct", {}).get("date", "")
        out.append({"id": f"{nct}@{date}", "kind": "Study record updated", "title": p["identificationModule"].get("briefTitle", ""),
                    "date": date, "detail": st.get("overallStatus", "").replace("_", " ").lower(),
                    "url": f"https://clinicaltrials.gov/study/{nct}", "source": "ClinicalTrials.gov"})
    return out


def _papers(gene):
    ids = ncbi("esearch", db="pubmed", term=f"{gene}[Title/Abstract]", retmode="json", retmax=15,
               datetype="edat", reldate=WINDOW_DAYS, sort="date").json()["esearchresult"].get("idlist", [])
    if not ids:
        return []
    res = ncbi("esummary", db="pubmed", id=",".join(ids), retmode="json").json()["result"]
    out = []
    for pmid in ids:
        r = res[pmid]
        date = (r.get("sortpubdate") or "")[:10].replace("/", "-")
        out.append({"id": f"PMID{pmid}", "kind": "New paper", "title": r.get("title", "").rstrip("."), "date": date,
                    "detail": r.get("source", ""), "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/", "source": "PubMed"})
    return out


def _preprints(gene, since):
    r = HTTP.get("https://www.ebi.ac.uk/europepmc/webservices/rest/search", params={
        "query": f'(TITLE:"{gene}" OR ABSTRACT:"{gene}") AND SRC:PPR AND FIRST_PDATE:[{since} TO 3000-01-01]',
        "format": "json", "pageSize": 15, "sort": "FIRST_PDATE_D desc"})
    r.raise_for_status()
    out = []
    for x in r.json().get("resultList", {}).get("result", []):
        out.append({"id": f"PPR{x['id']}", "kind": "New preprint (not peer reviewed)", "title": x.get("title", "").rstrip("."),
                    "date": x.get("firstPublicationDate", ""), "detail": x.get("bookOrReportDetails", {}).get("publisher", "") or "preprint",
                    "url": f"https://europepmc.org/article/PPR/{x['id']}", "source": "Europe PMC"})
    return out


def _pages(state):
    out = []
    for name, url in WATCHED_PAGES:
        r = HTTP.get(url, headers={"User-Agent": "Mozilla/5.0 (ConstellAI page watcher)"})
        r.raise_for_status()
        text = re.sub(r"\s+", " ", re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", r.text, flags=re.S)).strip()
        digest = hashlib.sha256(text.encode()).hexdigest()
        old = state.setdefault("pages", {}).get(url)
        if old and old["hash"] != digest:
            out.append({"id": f"page:{digest[:12]}", "kind": "Watched page changed", "title": name, "date": datetime.date.today().isoformat(),
                        "detail": f"content differs from {old['date']}", "url": url, "source": "page watcher"})
        if not old or old["hash"] != digest:
            state["pages"][url] = {"hash": digest, "date": datetime.date.today().isoformat()}
    return out


def refresh(gene):
    with _lock:
        state = json.loads(FILE.read_text()) if FILE.exists() else {}
        first_run = not state.get("seen")
        seen, summaries = state.setdefault("seen", {}), state.setdefault("summaries", {})
        today = datetime.date.today()
        since = (today - datetime.timedelta(days=WINDOW_DAYS)).isoformat()
        items, errors = [], []
        for label, fn in (("ClinicalTrials.gov", lambda: _studies(gene, since)), ("PubMed", lambda: _papers(gene)),
                          ("Europe PMC", lambda: _preprints(gene, since)), ("page watcher", lambda: _pages(state))):
            try:
                items += fn()
            except Exception as e:
                errors.append(f"{label}: {type(e).__name__}")
        for it in items:
            seen.setdefault(it["id"], today.isoformat())
            # on the very first run everything is baseline, not news
            it["new"] = not first_run and seen[it["id"]] == today.isoformat()
        items.sort(key=lambda it: it["date"], reverse=True)
        todo = [it for it in items if it["id"] not in summaries and it["kind"] != "Watched page changed"][:14]
        if todo and llm.available():
            got = llm.summarise_updates(gene, [{"id": it["id"], "kind": it["kind"], "title": it["title"], "detail": it["detail"]} for it in todo])
            summaries.update(got or {})
        for it in items:
            it["summary"] = summaries.get(it["id"], "")
        state.update({"gene": gene, "checked": datetime.datetime.now().isoformat(timespec="minutes"), "items": items,
                      "errors": errors, "window_days": WINDOW_DAYS,
                      "model": f"{llm.MODEL} via {llm.PROVIDER}" if llm.available() else None})
        FILE.parent.mkdir(parents=True, exist_ok=True)
        FILE.write_text(json.dumps(state))
        return view(state)


def view(state):
    return {k: state.get(k) for k in ("gene", "checked", "items", "errors", "window_days", "model")}


def get(gene, max_age_hours=6, force=False):
    if FILE.exists() and not force:
        state = json.loads(FILE.read_text())
        age = datetime.datetime.now() - datetime.datetime.fromisoformat(state["checked"])
        if state.get("gene") == gene and age.total_seconds() < max_age_hours * 3600:
            return view(state)
    return refresh(gene)
