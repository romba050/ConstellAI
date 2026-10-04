"""ConstellAI API + static frontend.

    uv run uvicorn atlas.server:app --port 8000
"""
import datetime
import json
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import connect, dashboard, enrich, llm, pulse, trials
from .config import ATLAS_FILE, CONTRIBUTIONS_FILE, FOCUS_DISEASE, WEB
from .store import Atlas, load_contributions

if not ATLAS_FILE.exists():
    raise SystemExit("data/atlas.json.gz not found. Build it first:  uv run python -m atlas.build")

atlas = Atlas()
app = FastAPI(title="ConstellAI")
PULSE_HOURS = 6


@app.on_event("startup")
def warm_focus():
    """Fetch the focus disease's evidence and trials in the background so the first visitor doesn't wait."""
    def run():
        d = atlas.diseases[FOCUS_DISEASE]
        jobs = (lambda: enrich.enrich(d), lambda: dashboard.build(atlas, FOCUS_DISEASE), lambda: trials.find(d))
        for job in jobs:
            try:
                job()
            except Exception as e:
                print(f"[warm] failed: {e}")
        while True:  # the scheduled fetcher behind the Pulse feed
            try:
                pulse.get(d["genes"][0], max_age_hours=PULSE_HOURS)
            except Exception as e:
                print(f"[pulse] failed: {e}")
            time.sleep(PULSE_HOURS * 3600)
    threading.Thread(target=run, daemon=True).start()


def disease_or_404(did):
    if did not in atlas.diseases:
        raise HTTPException(404, f"Unknown disease {did}")
    return atlas.diseases[did]


@app.get("/api/atlas")
def get_atlas():
    return {"meta": atlas.meta, "llm": llm.status(), "focus": FOCUS_DISEASE, "points": atlas.map_points(), "edges": atlas.map_edges(),
            "groups": sorted(atlas.groups.values(), key=lambda g: (g["id"] < 0, g["id"])),
            "organizations": len(enrich.curated()["organizations"])}


@app.get("/api/dashboard")
def get_dashboard(refresh: bool = False):
    """Knowledge graph, study status and search ledger for the focus disease."""
    return {**dashboard.build(atlas, FOCUS_DISEASE, force=refresh), "llm": llm.status(), "meta": atlas.meta}


@app.get("/api/pulse")
def get_pulse(refresh: bool = False):
    return pulse.get(atlas.diseases[FOCUS_DISEASE]["genes"][0], max_age_hours=PULSE_HOURS, force=refresh)


@app.get("/api/search")
def search(q: str):
    hits = atlas.search(q)
    resolved = None
    if not hits and llm.available() and len(q) >= 4:
        # Reconcile: let the model propose names, but only accept ones that exist in the vocabulary.
        for cand in llm.resolve_query(q) or []:
            for h in atlas.search(cand, limit=2):
                if h not in hits:
                    hits.append({**h, "matched": f"AI-resolved from “{q}” → {cand}"})
        resolved = "openai"
    return {"q": q, "hits": hits[:12], "resolved": resolved}


@app.get("/api/disease/{did}")
def disease(did: str):
    disease_or_404(did)
    return atlas.detail(did)


@app.get("/api/disease/{did}/evidence")
def disease_evidence(did: str, refresh: bool = False):
    d = disease_or_404(did)
    enr = enrich.enrich(d, force=refresh)
    return {**enr, "effect": connect.effect_profile(atlas, d, enr)}


@app.get("/api/disease/{did}/trials")
def disease_trials(did: str, refresh: bool = False):
    """Open studies a family could ask to join, each screened against the disease."""
    return trials.find(disease_or_404(did), force=refresh)


@app.get("/api/disease/{did}/network")
def disease_network(did: str, n: int = 5):
    """Network overlap: people who appear in more than one of the closest disease communities."""
    d = disease_or_404(did)
    members = [d] + [atlas.diseases[nb["id"]] for nb in d["neighbors"] if not nb["same_gene"]][:n]
    with ThreadPoolExecutor(3) as ex:
        enriched = list(ex.map(enrich.enrich, members))
    seen, rows = defaultdict(list), []
    for m, e in zip(members, enriched):
        for p in e["investigators"][:15]:
            seen[p["key"]].append((m, p))
        rows.append({**atlas.card(m["id"]), "lead": e["investigators"][0]["name"] if e["investigators"] else None,
                     "studies": sum(s["specific"] for s in e["trials"]["studies"]),
                     "orgs": [o["name"] for o in e["organizations"]][:3]})
    bridges = [{"name": hits[0][1]["name"], "affiliation": next((p["affiliation"] for _, p in hits if p["affiliation"]), ""),
                "diseases": [atlas.card(m["id"]) for m, _ in hits], "score": sum(p["score"] for _, p in hits)}
               for hits in seen.values() if len(hits) > 1]
    bridges.sort(key=lambda b: (-len(b["diseases"]), -b["score"]))
    return {"diseases": rows, "bridges": bridges[:10]}


@app.get("/api/connection")
def connection(a: str, b: str):
    disease_or_404(a), disease_or_404(b)
    return connect.connection(atlas, a, b)


@app.get("/api/entity/{typ}/{eid:path}")
def entity(typ: str, eid: str):
    try:
        return atlas.entity(typ, eid)
    except (KeyError, StopIteration):
        raise HTTPException(404, f"Unknown {typ} {eid}")


@app.get("/api/cluster/{cid}")
def cluster(cid: str):
    if cid not in atlas.clusters:
        raise HTTPException(404, "Unknown cluster")
    c = atlas.clusters[cid]
    return {**c, "phenotypes": [{**p, "name": atlas.hpo[p["hp"]]["name"]} for p in c["phenotypes"]],
            "pathways": [{**p, "name": atlas.pathways[p["id"]]["name"]} for p in c["pathways"]],
            "members": [atlas.card(m) for m in atlas.cluster_members[cid]]}


class Contribution(BaseModel):
    disease: str
    kind: str = Field(pattern="^(phenotype|asset|group|correction)$")
    text: str = Field(min_length=3, max_length=600)
    source: str = Field(default="", max_length=300)
    author: str = Field(default="", max_length=120)


@app.post("/api/contribute")
def contribute(c: Contribution):
    """Patient groups add missing evidence; it is shown as unverified until a curator reviews it."""
    disease_or_404(c.disease)
    items = load_contributions()
    item = {**c.model_dump(), "date": datetime.date.today().isoformat(), "status": "unverified"}
    items.append(item)
    CONTRIBUTIONS_FILE.write_text(json.dumps(items, indent=1))
    return item


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.get("/atlas")
def atlas_page():
    return FileResponse(WEB / "atlas.html")


app.mount("/", StaticFiles(directory=WEB), name="web")
