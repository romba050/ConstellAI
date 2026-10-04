"""ConstellAI API + static frontend.

    uv run uvicorn atlas.server:app --port 8000
"""
import datetime
import json
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import connect, enrich, llm
from .analysis.models import AnalyzeRequest, AnalyzeResponse
from .analysis.service import AnalysisService, EvidenceIntegrityError, SCHEMA_VERSION
from .config import ATLAS_FILE, CONTRIBUTIONS_FILE, WEB
from .store import Atlas, load_contributions

if not ATLAS_FILE.exists():
    raise SystemExit("data/atlas.json.gz not found. Build it first:  uv run python -m atlas.build")

atlas = Atlas()
app = FastAPI(title="ConstellAI")
analysis_service = AnalysisService(atlas=atlas)
logger = logging.getLogger(__name__)


@app.get("/api/v1/health")
def health():
    """Capability flags expose neither keys nor environment contents."""
    return {"status": "ok", "schema_version": SCHEMA_VERSION,
            "scoring_version": analysis_service.weights["config_version"],
            "openai_enabled": llm.available()}


@app.get("/api/v1/schema")
def analysis_schema():
    return {"request": AnalyzeRequest.model_json_schema(), "response": AnalyzeResponse.model_json_schema()}


@app.post("/api/v1/analyze_disease", response_model=AnalyzeResponse)
def analyze_disease(request: AnalyzeRequest):
    try:
        return analysis_service.analyze(request)
    except EvidenceIntegrityError:
        logger.error("Curated therapeutic evidence failed contract validation")
        raise HTTPException(503, "Reviewed evidence is unavailable; therapeutic analysis was withheld.")
    except ValueError:
        raise HTTPException(422, "Disease must contain a name, gene symbol or exact identifier.")


def disease_or_404(did):
    if did not in atlas.diseases:
        raise HTTPException(404, f"Unknown disease {did}")
    return atlas.diseases[did]


@app.get("/api/atlas")
def get_atlas():
    return {"meta": atlas.meta, "llm": llm.status(), "points": atlas.map_points(), "edges": atlas.map_edges(),
            "groups": sorted(atlas.groups.values(), key=lambda g: (g["id"] < 0, g["id"])),
            "organizations": len(enrich.curated()["organizations"])}


@app.get("/api/search")
def search(q: str, use_openai: bool = True):
    hits = atlas.search(q)
    resolved = None
    if not hits and use_openai and llm.available() and len(q) >= 4:
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
def connection(a: str, b: str, audience: str = "maria"):
    disease_or_404(a), disease_or_404(b)
    return connect.connection(atlas, a, b, audience)


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
    return FileResponse(WEB / "research.html")


@app.get("/atlas")
def atlas_index():
    return FileResponse(WEB / "index.html")


app.mount("/", StaticFiles(directory=WEB), name="web")
