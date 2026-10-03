from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from engines.rare_disease_mimic_engine.engine import (
    build_addon_candidates,
    build_deviation_profile,
    build_early_kill_proposals,
    build_future_medicine_path,
    build_primary_result,
    build_sim_context,
    describe_selection,
    get_candidate_map,
    list_all_candidates,
    load_mock_candidates,
    load_mock_diseases,
    resolve_disease_input,
    rank_candidates,
    unique_norm_genes,
)
from engines.rare_disease_mimic_engine.optimize import choose_best_bundle
try:
    from services.master_registry import (
        clear_registry_cache,
        get_all_compounds as registry_get_all_compounds,
        get_all_diseases as registry_get_all_diseases,
        get_all_drugs as registry_get_all_drugs,
        get_all_physiology as registry_get_all_physiology,
        hydrate_fda_approved_drugs,
    )
except Exception:
    clear_registry_cache = None
    registry_get_all_compounds = None
    registry_get_all_diseases = None
    registry_get_all_drugs = None
    registry_get_all_physiology = None
    hydrate_fda_approved_drugs = None

from services.evidence_analyzer import (
    analyze_compound,
    analyze_compound_target,
    pubmed_get_article,
    pubmed_search,
)
from engines.rare_disease_mimic_engine.historical_schema import (
    HistoricalReplayCase,
    ReplayMemoryBank,
    ReplayPredictionInput,
    ReplayPredictionResult,
)
from engines.rare_disease_mimic_engine.historical_seed_data import get_seed_historical_cases
from engines.rare_disease_mimic_engine.historical_storage import (
    HistoricalReplayStore,
    build_replay_prediction,
)


# -----------------------------
# CONFIG
# -----------------------------
ROOT = Path(__file__).resolve().parent
ENGINES_DIR = ROOT / "engines"
MEMORY_DIR = ROOT / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

RARE_ENGINE_DIR = ENGINES_DIR / "rare_disease_mimic_engine"
RARE_ENGINE_DATA_DIR = RARE_ENGINE_DIR / "data"
RARE_ENGINE_DATA_DIR.mkdir(parents=True, exist_ok=True)
RARE_SIM_MEMORY_PATH = RARE_ENGINE_DATA_DIR / "sim_memory.json"
HISTORICAL_REPLAY_BANK_PATH = RARE_ENGINE_DATA_DIR / "historical_replay_bank.json"
GENE_CROSSOVER_MEMORY_PATH = ENGINES_DIR / "gene_crossover_engine" / "knowledge" / "memory.json"
EVIDENCE_RECENT_PATH = DATA_DIR / "recent_evidence_queries.json"
RARE_PROTOCOL_DIR = DATA_DIR / "rare_protocols"
RARE_PROTOCOL_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------
# GENERIC HELPERS
# -----------------------------
def now_ms() -> int:
    return int(time.time() * 1000)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(p: Path, obj: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")



def read_json(p: Path, default: Any) -> Any:
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default



def discover_engines() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    if not ENGINES_DIR.exists():
        return out
    for d in ENGINES_DIR.iterdir():
        if d.is_dir():
            out[d.name] = {"path": str(d), "files": len(list(d.rglob("*")))}
    return out



def safeguard_memory_path() -> Path:
    return MEMORY_DIR / "safeguard_confirmed.json"



def load_safeguard_memory() -> Dict[str, Any]:
    return read_json(safeguard_memory_path(), default={"items": []})



def save_safeguard_memory(mem: Dict[str, Any]) -> None:
    write_json(safeguard_memory_path(), mem)



def load_rare_sim_memory() -> Dict[str, Any]:
    return read_json(
        RARE_SIM_MEMORY_PATH,
        default={
            "trained": False,
            "window": None,
            "cases_seen": 0,
            "hit_ratio": 0.0,
            "pattern_summary": "train first to store general rare-pattern logic",
            "trace_sample": [],
            "updated_at_ms": None,
        },
    )



def save_rare_sim_memory(mem: Dict[str, Any]) -> None:
    write_json(RARE_SIM_MEMORY_PATH, mem)


def historical_replay_store() -> HistoricalReplayStore:
    return HistoricalReplayStore(HISTORICAL_REPLAY_BANK_PATH)


def ensure_historical_seed_bank() -> ReplayMemoryBank:
    store = historical_replay_store()
    bank = store.load()
    if bank.cases:
        return bank
    bank = store.replace_cases(get_seed_historical_cases())
    return bank




def tag_extract(experiment_text: str) -> List[str]:
    t = (experiment_text or "").upper()
    tags: List[str] = []
    if any(x in t for x in ["STORE", "FREEZE", "THAW"]):
        tags.append("CELL_STORAGE")
    if any(x in t for x in ["LABEL", "NAME", "SKU"]):
        tags.append("LABELING")
    if any(x in t for x in ["INCUB", "TEMP", "HUMID"]):
        tags.append("INCUBATION")
    if any(x in t for x in ["NEW", "UNVERIFIED", "NOVEL"]):
        tags.append("HYPOTHESIS_RISK")
    if not tags:
        tags.append("GENERAL")
    return tags



def norm_gene(g: str) -> str:
    return (g or "").strip().upper().replace(" ", "").replace("-", "")


# -----------------------------
# API MODELS
# -----------------------------
class HealthOut(BaseModel):
    ok: bool
    engines: Dict[str, Dict[str, Any]]
    engines_found: List[str]
    time_ms: int


class EarlyKillExp(BaseModel):
    name: str
    cost_eur: float
    days: int
    early_kill: str


class ProfitPotential(BaseModel):
    scenario: str
    range_eur: str


class HypothesisBundleReq(BaseModel):
    mode: str = "early_kill_5"
    drug_id: Optional[str] = None
    drug_name: Optional[str] = None
    category: Optional[str] = None
    selected_targets: List[str] = Field(default_factory=list)
    picked_compounds: List[str] = Field(default_factory=list)


class HypothesisBundleItem(BaseModel):
    idx: int
    hypothesis: str
    why: List[str]
    early_kill_experiments: List[EarlyKillExp]
    cost_total_eur: float
    profit_potential: ProfitPotential


class HypothesisBundleOut(BaseModel):
    engine: str = "backend"
    mode: str
    seed: str
    items: List[HypothesisBundleItem]


class SafeguardReq(BaseModel):
    experiment_text: Optional[str] = None
    text: Optional[str] = None
    seed: int | None = None

    def resolved_text(self) -> str:
        return (self.experiment_text or self.text or "").strip()


class FailureMode(BaseModel):
    summary: str
    cost_eur: float
    time_weeks: int
    avoidable: bool


class SafeguardOut(BaseModel):
    tags: List[str]
    matches: List[FailureMode]
    safeguards: List[str]
    assumptions: Dict[str, Any]
    estimated_savings_eur: float


class MemoryAddItem(BaseModel):
    text: str
    tags: List[str] = Field(default_factory=list)


class MemoryAddReq(BaseModel):
    items: List[MemoryAddItem] = Field(default_factory=list)


class MemoryListItem(BaseModel):
    text: str
    tags: List[str]
    count: int


class MemoryListOut(BaseModel):
    items: List[MemoryListItem]


class SystemMemoryEngineOut(BaseModel):
    id: str
    name: str
    runs: int = 0
    stored_cases: int = 0
    confidence: str = "early"
    summary: str = ""
    top_pattern: str = ""
    improved: str = ""
    last_updated_ms: Optional[int] = None


class SystemMemoryUpdateOut(BaseModel):
    engine: str
    note: str


class SystemMemorySummaryOut(BaseModel):
    rare_window: Optional[str] = None
    rare_hit_ratio: float = 0.0
    safeguard_rule_count: int = 0
    engines: List[SystemMemoryEngineOut] = Field(default_factory=list)
    recent_updates: List[SystemMemoryUpdateOut] = Field(default_factory=list)
    recent_evidence_queries: List[Dict[str, Any]] = Field(default_factory=list)


class RareDisease(BaseModel):
    id: str
    name: str
    genes: List[str]
    notes: str = ""
    directions: Dict[str, str] = Field(default_factory=dict)


class Candidate(BaseModel):
    id: str
    name: str
    targets: List[str]
    source: str = "demo"
    kind: str = "drug"


class RankedCandidate(BaseModel):
    id: str
    name: str
    kind: str
    score: float
    raw_score: float
    overlap_genes: List[str]
    spillover_genes: List[str]
    spillover_count: int
    target_count: int
    source: str = "demo"


class SelectionSummary(BaseModel):
    selected: List[Any]
    covered_genes: List[str]
    uncovered_genes: List[str]
    spillover_genes: List[str]
    coverage_ratio: float
    spillover_ratio: float
    best_primary_candidate_id: Optional[str] = None
    best_primary_candidate_name: Optional[str] = None
    best_primary_overlap_genes: List[str] = Field(default_factory=list)
    deviation_uncovered_genes: List[str] = Field(default_factory=list)
    suggested_addon_ids: List[str] = Field(default_factory=list)
    suggested_addon_summary: List[str] = Field(default_factory=list)
    bundle_ids: List[str] = Field(default_factory=list)
    bundle_names: List[str] = Field(default_factory=list)
    rank_depth_used: int = 0
    max_bundle_items_used: int = 0
    spillover_weight_used: float = 0.0


class RareAnalyzeReq(BaseModel):
    disease_id: str = "custom"
    disease_genes: List[str] = Field(default_factory=list)
    disease_gene_text: str = ""
    selected_candidates: List[str] = Field(default_factory=list)
    max_results: int = 12
    max_bundle_items: int = 4
    rank_depth: int = 8
    spillover_weight: float = 0.12
    planner_mode: str = "mode_a"
    bundle_strategy: str = "dynamic"
    include_physiology: bool = True


class RarePrimaryOut(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    score: float = 0.0
    raw_score: float = 0.0
    coverage_genes: List[str] = Field(default_factory=list)
    coverage_count: int = 0
    coverage_ratio: float = 0.0
    spillover_genes: List[str] = Field(default_factory=list)
    spillover_count: int = 0
    source: Optional[str] = None
    rationale: str = ""


class RareDeviationOut(BaseModel):
    covered_genes: List[str] = Field(default_factory=list)
    uncovered_genes: List[str] = Field(default_factory=list)
    uncovered_directions: Dict[str, str] = Field(default_factory=dict)
    covered_count: int = 0
    uncovered_count: int = 0
    coverage_ratio: float = 0.0
    summary: str = ""


class RareAddonItem(BaseModel):
    id: str
    name: str
    kind: str
    score: float
    covers_deviation_genes: List[str]
    new_spillover_genes: List[str]
    net_gain: float
    bundle_compatibility: str
    why_selected: str
    source: str = "demo"


class RareBundleOut(BaseModel):
    bundle_ids: List[str] = Field(default_factory=list)
    bundle_names: List[str] = Field(default_factory=list)
    suggested_addon_ids: List[str] = Field(default_factory=list)
    suggested_addon_names: List[str] = Field(default_factory=list)
    covered_genes: List[str] = Field(default_factory=list)
    uncovered_genes: List[str] = Field(default_factory=list)
    uncovered_directions: Dict[str, str] = Field(default_factory=dict)
    spillover_genes: List[str] = Field(default_factory=list)
    spillover_count: int = 0
    coverage_ratio: float = 0.0
    score: float = 0.0


class RareFuturePathOut(BaseModel):
    ideal_target_set: List[str] = Field(default_factory=list)
    current_market_coverage_genes: List[str] = Field(default_factory=list)
    remaining_gap_genes: List[str] = Field(default_factory=list)
    current_market_coverage_ratio: float = 0.0
    creation_justified: bool = False
    creation_rationale: str = ""
    translation_note: str = ""


class RareProposalOut(BaseModel):
    id: str
    title: str
    focus: str
    goal: str
    cheap_readout: str
    stop_rule: str
    hypothesis_anchor: str = ""
    reasoning_trace: List[str] = Field(default_factory=list)
    estimated_savings_eur: float = 0.0
    protocol_pdf_url: Optional[str] = None


class RareProposalProtocolReq(BaseModel):
    disease_name: str = ""
    proposal_id: str = ""
    proposal_title: str = ""
    focus: str = ""
    goal: str = ""
    cheap_readout: str = ""
    stop_rule: str = ""
    hypothesis_anchor: str = ""
    reasoning_trace: List[str] = Field(default_factory=list)
    estimated_savings_eur: float = 0.0
    bundle_names: List[str] = Field(default_factory=list)


class RareProposalProtocolOut(BaseModel):
    ok: bool
    filename: str
    pdf_url: str
    estimated_savings_eur: float = 0.0


class RareSimMemoryOut(BaseModel):
    trained: bool
    window: Optional[str] = None
    cases_seen: int = 0
    hit_ratio: float = 0.0
    pattern_summary: str = ""
    trace_sample: List[Dict[str, Any]] = Field(default_factory=list)
    updated_at_ms: Optional[int] = None


class RareSimContextOut(BaseModel):
    trained: bool = False
    window: Optional[str] = None
    cases_seen: int = 0
    hit_ratio: float = 0.0
    pattern_summary: str = ""
    matched_traces: List[Dict[str, Any]] = Field(default_factory=list)
    trace_sample: List[Dict[str, Any]] = Field(default_factory=list)
    support_note: str = ""


class RareInstitutionalAssessmentOut(BaseModel):
    readiness_label: str = "early"
    readiness_score: float = 0.0
    facility_fit: str = "research triage only"
    human_review_required: bool = True
    evidence_posture: str = "mechanism-first"
    source_mix: Dict[str, int] = Field(default_factory=dict)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    recommended_next_steps: List[str] = Field(default_factory=list)
    audit_flags: List[str] = Field(default_factory=list)
    disclaimer: str = ""


class RareAnalyzeOut(BaseModel):
    disease: RareDisease
    ranked: List[RankedCandidate]
    summary: SelectionSummary
    primary: RarePrimaryOut
    deviation: RareDeviationOut
    addons: List[RareAddonItem]
    bundle: RareBundleOut
    future_path: RareFuturePathOut
    proposals: List[RareProposalOut]
    sim_context: RareSimContextOut
    institutional_assessment: RareInstitutionalAssessmentOut


class RareSimTrainReq(BaseModel):
    start_year: int = 1970
    end_year: int = 2005
    seed: int = 1337


class RareSimTrainOut(BaseModel):
    ok: bool
    learned: RareSimMemoryOut




class HistoricalReplaySeedOut(BaseModel):
    ok: bool
    cases_loaded: int
    window: str
    bank_path: str


class HistoricalReplayStoreHitReq(BaseModel):
    replay_id: str
    disease_name: str
    reusable_rule: str
    confidence: str = "medium"
    source_ids: List[str] = Field(default_factory=list)


class HistoricalReplayRunReq(BaseModel):
    replay_id: str = ""
    disease_name: str
    discovery_year: Optional[int] = None
    candidate_features: List[str] = Field(default_factory=list)
    suspected_targets: List[Dict[str, Any]] = Field(default_factory=list)
    notes: str = ""
    store_if_hit: bool = False
    hit: Optional[bool] = None
    hit_explanation: str = ""


class HistoricalReplayTrainReq(BaseModel):
    start_year: int = 1970
    end_year: int = 2005
    max_cases_per_year: int = 2
    seed: int = 1337


class HistoricalReplayTrainOut(BaseModel):
    ok: bool
    window: str
    cases_replayed: int
    replays_recorded: int
    matched_case_ids: List[str] = Field(default_factory=list)
    note: str = ""

class CompoundReportItem(BaseModel):
    compound: str
    path: str


class CompoundReportListOut(BaseModel):
    items: List[CompoundReportItem]


class CompoundAnalyzeReq(BaseModel):
    compound: str = ""
    context: str = ""
    targets: List[str] = Field(default_factory=list)
    max_papers: int = 8
    use_llm: bool = True


class CompoundAnalyzeOut(BaseModel):
    compound: str
    objective_summary: str
    subjective_summary: str
    pmids: List[str] = Field(default_factory=list)
    report_pdf_url: Optional[str] = None
    notes: str = ""


class RegistryBucketStats(BaseModel):
    total: int = 0
    rare: int = 0
    starter: int = 0
    sources: List[str] = Field(default_factory=list)


class RegistrySummaryOut(BaseModel):
    diseases: RegistryBucketStats
    drugs: RegistryBucketStats
    compounds: RegistryBucketStats
    physiology: RegistryBucketStats
    loaded: bool = False
    note: str = ""


# -----------------------------
# DEMO DATA
# -----------------------------
FAILURE_LIBRARY = [
    {
        "tags": ["CELL_STORAGE", "LABELING", "SIMILAR_NAMES"],
        "summary": "WRONG STORAGE MEDIUM PICKED DUE TO SIMILAR NAMING; CELLS LOST.",
        "cost_eur": 4500,
        "time_weeks": 3,
        "avoidable": True,
    },
    {
        "tags": ["INCUBATION"],
        "summary": "INCUBATION TEMPERATURE DRIFTED; ASSAY FAILED SILENTLY UNTIL ENDPOINT.",
        "cost_eur": 6000,
        "time_weeks": 2,
        "avoidable": True,
    },
    {
        "tags": ["GENERAL"],
        "summary": "REAGENT LOT VARIATION NOT NOTICED; RESULTS NOT REPRODUCIBLE.",
        "cost_eur": 8000,
        "time_weeks": 4,
        "avoidable": True,
    },
    {
        "tags": ["HYPOTHESIS_RISK"],
        "summary": "NOVEL PROTOCOL HAD HIDDEN DEPENDENCY; RUN INVALID.",
        "cost_eur": 12000,
        "time_weeks": 6,
        "avoidable": True,
    },
]


# -----------------------------
# RARE HELPERS
# -----------------------------
def candidate_to_api(c) -> Candidate:
    target_values = getattr(c, "target_genes", None)
    if target_values is None:
        target_values = getattr(c, "targets", [])
    return Candidate(
        id=c.id,
        name=c.name,
        targets=sorted(list(target_values or [])),
        source=getattr(c, "source", "demo"),
        kind=getattr(c, "kind", "drug"),
    )




def _registry_candidate_records(kind: str, include_physiology: bool = True):
    rows = []
    if registry_get_candidates is not None:
        try:
            rows = registry_get_candidates(kind, include_physiology=include_physiology) or []
        except Exception:
            rows = []
    if rows:
        try:
            return [_candidate_from_registry(item) for item in rows]
        except Exception:
            pass
    return load_mock_candidates(kind, include_physiology=include_physiology)


def _drug_mimic_candidate_records():
    rows = []
    if registry_get_all_drugs is not None:
        try:
            rows = registry_get_all_drugs() or []
        except Exception:
            rows = []
    if rows:
        mapped = []
        unmapped = []
        for item in rows:
            try:
                rec = _candidate_from_registry(item)
            except Exception:
                continue
            if getattr(rec, 'targets', None):
                mapped.append(rec)
            else:
                unmapped.append(rec)
        mapped.sort(key=lambda c: (-len(getattr(c, 'targets', []) or []), str(getattr(c, 'name', '')).lower()))
        unmapped.sort(key=lambda c: str(getattr(c, 'name', '')).lower())
        return mapped + unmapped
    return load_mock_candidates('drug')

def _registry_bucket_stats(items: List[Dict[str, Any]]) -> RegistryBucketStats:
    total = len(items)
    rare = sum(1 for item in items if bool(item.get("rare", False)))
    starter = sum(1 for item in items if str(item.get("status") or "").strip().lower() == "starter")
    sources = sorted({str(item.get("source") or "unknown").strip().lower() for item in items if str(item.get("source") or "").strip()})
    return RegistryBucketStats(total=total, rare=rare, starter=starter, sources=sources)




def _safe_slug(value: str) -> str:
    token = "_".join((value or "").strip().lower().split())
    token = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in token)
    while "__" in token:
        token = token.replace("__", "_")
    return token.strip("_") or "rare_protocol"


def build_rare_protocol_pdf(payload: RareProposalProtocolReq) -> Path:
    base = f"{_safe_slug(payload.disease_name)}_{_safe_slug(payload.proposal_id or payload.proposal_title)}_{now_ms()}"
    out_path = RARE_PROTOCOL_DIR / f"{base}.pdf"
    c = canvas.Canvas(str(out_path), pagesize=A4)
    width, height = A4
    y = height - 48

    def line(text: str, gap: int = 16, bold: bool = False):
        nonlocal y
        if y < 64:
            c.showPage()
            y = height - 48
        c.setFont("Helvetica-Bold" if bold else "Helvetica", 10 if not bold else 11)
        safe = str(text or "").replace("	", " ")
        for chunk in [safe[i:i+105] for i in range(0, len(safe), 105)] or [""]:
            c.drawString(42, y, chunk)
            y -= gap

    line("MED-R5 safeguard deviation protocol", bold=True)
    line(f"disease: {payload.disease_name}")
    line(f"experiment: {payload.proposal_title}")
    line(f"focus: {payload.focus}")
    line(f"goal: {payload.goal}")
    line(f"cheap readout: {payload.cheap_readout}")
    line(f"stop rule: {payload.stop_rule}")
    line(f"bundle: {', '.join(payload.bundle_names) or 'none'}")
    line(f"hypothesis anchor: {payload.hypothesis_anchor}")
    line("")
    line("reasoning trace", bold=True)
    for item in payload.reasoning_trace or []:
        line(f"- {item}")
    line("")
    line("safeguard deviation protocol", bold=True)
    protocol_lines = [
        "1. verify assay model and control before any full run.",
        "2. run the cheapest target-engagement readout first.",
        "3. cap spend until signal and spillover are both visible.",
        "4. document every deviation, storage issue, timing drift, and readout failure.",
        "5. stop immediately if stop-rule is hit and store the miss in safeguard memory.",
    ]
    for item in protocol_lines:
        line(item)
    line("")
    line("mistakes avoided / estimated savings", bold=True)
    line(f"potential savings from avoided mistakes: EUR {payload.estimated_savings_eur:,.0f}")
    line("main avoided losses: wrong model continuation, false-positive bundle spend, uncaught spillover, and repetition of the same failed setup.")
    c.save()
    return out_path


def proposal_to_protocol_url(proposal_id: str) -> str:
    return f"/api/rare/proposal/protocol/{proposal_id}"

def build_registry_summary() -> RegistrySummaryOut:
    if not (registry_get_all_diseases and registry_get_all_drugs and registry_get_all_compounds):
        return RegistrySummaryOut(
            diseases=RegistryBucketStats(),
            drugs=RegistryBucketStats(),
            compounds=RegistryBucketStats(),
            physiology=RegistryBucketStats(),
            loaded=False,
            note="master registry not available",
        )

    try:
        diseases = registry_get_all_diseases()
        drugs = registry_get_all_drugs()
        compounds = registry_get_all_compounds()
        physiology = registry_get_all_physiology() if registry_get_all_physiology else []
        return RegistrySummaryOut(
            diseases=_registry_bucket_stats(diseases),
            drugs=_registry_bucket_stats(drugs),
            compounds=_registry_bucket_stats(compounds),
            physiology=_registry_bucket_stats(physiology),
            loaded=True,
            note="shared backend registry loaded",
        )
    except Exception as exc:
        return RegistrySummaryOut(
            diseases=RegistryBucketStats(),
            drugs=RegistryBucketStats(),
            compounds=RegistryBucketStats(),
            physiology=RegistryBucketStats(),
            loaded=False,
            note=f"registry load failed: {exc}",
        )


def find_compound_report_pdf(compound: str) -> Optional[Path]:
    slug = (compound or "").strip().lower().replace(" ", "_")
    if not slug:
        return None
    if not ENGINES_DIR.exists():
        return None
    candidates = []
    for p in ENGINES_DIR.rglob("*_report.pdf"):
        if p.name.lower() == f"{slug}_report.pdf":
            candidates.append(p)
    if candidates:
        candidates.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return candidates[0]
    return None


def _safe_mtime_ms(path: Path) -> Optional[int]:
    try:
        return int(path.stat().st_mtime * 1000)
    except Exception:
        return None


def load_recent_evidence_queries() -> List[Dict[str, Any]]:
    data = read_json(EVIDENCE_RECENT_PATH, default={"items": []})
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        return data["items"]
    return []


def append_recent_evidence_query(compound: str, context: str = "", targets: Optional[List[str]] = None) -> None:
    targets = [t for t in (targets or []) if t]
    items = load_recent_evidence_queries()
    payload = {
        "compound": (compound or "").strip(),
        "context": (context or "").strip(),
        "targets": targets[:12],
        "updated_at_ms": now_ms(),
    }
    if not payload["compound"]:
        return
    deduped = [payload]
    for item in items:
        if not isinstance(item, dict):
            continue
        same = (item.get("compound", "").strip().lower() == payload["compound"].lower() and
                (item.get("context", "").strip().lower() == payload["context"].lower()))
        if not same:
            deduped.append(item)
    ensure_parent(EVIDENCE_RECENT_PATH)
    write_json(EVIDENCE_RECENT_PATH, {"items": deduped[:12]})


def build_system_memory_summary() -> Dict[str, Any]:
    rare_mem = load_rare_sim_memory()
    safeguard_mem = load_safeguard_memory()
    gene_mem = read_json(GENE_CROSSOVER_MEMORY_PATH, default={})
    historical_bank = read_json(HISTORICAL_REPLAY_BANK_PATH, default={})
    recent_evidence = load_recent_evidence_queries()

    safeguard_items = safeguard_mem.get("items", []) if isinstance(safeguard_mem, dict) else []
    gene_keys = len(gene_mem) if isinstance(gene_mem, dict) else 0
    replay_runs = len((historical_bank or {}).get("replay_runs", [])) if isinstance(historical_bank, dict) else 0
    historical_cases = len((historical_bank or {}).get("cases", [])) if isinstance(historical_bank, dict) else 0

    engines = [
        {
            "id": "rare",
            "name": "rare disease _ ml",
            "runs": int(rare_mem.get("cases_seen", 0) or 0),
            "stored_cases": int(rare_mem.get("cases_seen", 0) or 0),
            "confidence": "trained" if rare_mem.get("trained") else "early",
            "summary": rare_mem.get("pattern_summary", "rare disease simulation memory"),
            "top_pattern": rare_mem.get("pattern_summary", ""),
            "improved": rare_mem.get("window", "not trained yet"),
            "last_updated_ms": rare_mem.get("updated_at_ms") or _safe_mtime_ms(RARE_SIM_MEMORY_PATH),
        },
        {
            "id": "subj_obj",
            "name": "subj _ obj",
            "runs": gene_keys,
            "stored_cases": gene_keys,
            "confidence": "indexed" if gene_keys else "early",
            "summary": f"{gene_keys} indexed memory keys available for evidence crossover.",
            "top_pattern": "gene-target memory indexed for compound crossover",
            "improved": "backend evidence compare endpoint active",
            "last_updated_ms": _safe_mtime_ms(GENE_CROSSOVER_MEMORY_PATH),
        },
        {
            "id": "safeguard",
            "name": "safeguard _ deviation",
            "runs": len(safeguard_items),
            "stored_cases": len(safeguard_items),
            "confidence": "growing" if safeguard_items else "early",
            "summary": f"{len(safeguard_items)} stored safeguard checklist rules.",
            "top_pattern": safeguard_items[-1]["text"] if safeguard_items else "no stored safeguard rule yet",
            "improved": "confirmed checklist memory retained",
            "last_updated_ms": _safe_mtime_ms(safeguard_memory_path()),
        },
        {
            "id": "history",
            "name": "rare history replay",
            "runs": replay_runs,
            "stored_cases": historical_cases,
            "confidence": "seeded" if historical_cases else "early",
            "summary": f"{historical_cases} historical replay cases with {replay_runs} stored replays.",
            "top_pattern": "first medicine logic and later improvement logic retained",
            "improved": "historical replay bank visible",
            "last_updated_ms": _safe_mtime_ms(HISTORICAL_REPLAY_BANK_PATH),
        },
    ]

    recent_updates = []
    for engine in engines:
        note = engine.get("improved") or engine.get("top_pattern") or engine.get("summary") or "updated"
        recent_updates.append({"engine": engine["name"], "note": note})

    return {
        "rare_window": rare_mem.get("window"),
        "rare_hit_ratio": float(rare_mem.get("hit_ratio", 0.0) or 0.0),
        "safeguard_rule_count": len(safeguard_items),
        "engines": engines,
        "recent_updates": recent_updates,
        "recent_evidence_queries": recent_evidence,
    }


# -----------------------------
# APP
# -----------------------------
def build_rare_institutional_assessment(
    *,
    disease: Any,
    ranked: List[Dict[str, Any]],
    primary_payload: Dict[str, Any],
    deviation_payload: Dict[str, Any],
    bundle_payload: Dict[str, Any],
    addon_ranked: List[Dict[str, Any]],
    sim_context_payload: Dict[str, Any],
    summary_payload: Dict[str, Any],
) -> Dict[str, Any]:
    source_mix: Dict[str, int] = {}
    for row in ranked[:12]:
        src = str(row.get("source") or "unknown").strip().lower() or "unknown"
        source_mix[src] = source_mix.get(src, 0) + 1

    registry_summary = build_registry_summary()
    disease_count = int(getattr(registry_summary.diseases, "total", 0) or 0)
    drug_count = int(getattr(registry_summary.drugs, "total", 0) or 0)
    compound_count = int(getattr(registry_summary.compounds, "total", 0) or 0)

    coverage_ratio = float(bundle_payload.get("coverage_ratio", primary_payload.get("coverage_ratio", 0.0)) or 0.0)
    spillover_count = int(bundle_payload.get("spillover_count", primary_payload.get("spillover_count", 0)) or 0)
    uncovered_count = int(deviation_payload.get("uncovered_count", 0) or 0)
    bundle_size = len(bundle_payload.get("bundle_ids", []) or [])
    trained = bool(sim_context_payload.get("trained"))
    hit_ratio = float(sim_context_payload.get("hit_ratio", 0.0) or 0.0)
    custom_disease = str(getattr(disease, "id", "") or "") == "custom"
    source_keys = set(source_mix.keys())
    fallback_heavy = ("fallback" in source_keys) or ("demo" in source_keys) or not source_keys

    readiness_score = 0.0
    readiness_score += min(0.55, coverage_ratio * 0.55)
    readiness_score += 0.10 if drug_count >= 10 else 0.04
    readiness_score += 0.08 if compound_count >= 20 else 0.03
    readiness_score += 0.08 if disease_count >= 10 else 0.03
    readiness_score += 0.08 if registry_summary.loaded and not fallback_heavy else 0.0
    readiness_score += min(0.06, hit_ratio * 0.06)
    readiness_score -= min(0.18, uncovered_count * 0.06)
    readiness_score -= min(0.10, spillover_count * 0.03)
    readiness_score -= 0.08 if custom_disease else 0.0
    readiness_score -= 0.06 if bundle_size >= 4 else 0.0
    readiness_score = max(0.05, min(0.92, readiness_score))

    if readiness_score >= 0.72 and not fallback_heavy and trained:
        readiness_label = "translational review"
        facility_fit = "research support with strict human review"
    elif readiness_score >= 0.52:
        readiness_label = "research triage"
        facility_fit = "hypothesis triage and mechanism review"
    else:
        readiness_label = "early"
        facility_fit = "research triage only"

    evidence_posture = "mixed registry + mechanism"
    if fallback_heavy:
        evidence_posture = "starter / fallback mechanism data"
    elif trained:
        evidence_posture = "registry + mechanism + replay memory"

    strengths = []
    weaknesses = []
    blockers = []
    next_steps = []
    audit_flags = []

    if primary_payload.get("name"):
        strengths.append(f"primary candidate identified: {primary_payload.get('name')}")
    if coverage_ratio >= 0.66:
        strengths.append(f"bundle closes {round(coverage_ratio * 100)}% of disease signals")
    if addon_ranked:
        strengths.append(f"deviation rescue path available via {len(addon_ranked)} add-on candidates")
    if trained:
        strengths.append(f"historical replay memory active across {sim_context_payload.get('cases_seen', 0)} simulated cases")
    if registry_summary.loaded:
        strengths.append(f"shared registry loaded: {disease_count} diseases, {drug_count} drugs, {compound_count} compounds")

    if fallback_heavy:
        weaknesses.append("rankings are still heavily dependent on starter or fallback entries")
        blockers.append("expand validated registry depth before facility-facing claims")
        audit_flags.append("starter_data_dependency")
    if coverage_ratio < 0.8:
        weaknesses.append("mechanism closure is incomplete; uncovered disease signals remain")
    if uncovered_count > 0:
        blockers.append(f"{uncovered_count} disease signals remain open after primary selection")
        audit_flags.append("open_deviation_signals")
    if spillover_count > 0:
        weaknesses.append(f"bundle introduces {spillover_count} spillover targets that need review")
        audit_flags.append("spillover_review_needed")
    if custom_disease:
        weaknesses.append("custom disease input bypasses curated disease definitions")
        audit_flags.append("custom_disease_input")
    if not trained:
        weaknesses.append("historical replay memory has not been trained yet")
        blockers.append("train replay memory before positioning as institutional learning system")
        audit_flags.append("replay_untrained")
    if hit_ratio < 0.35:
        weaknesses.append("historical replay support is still weak or early")
    if bundle_size >= 4:
        weaknesses.append("bundle complexity is high; explainability and interaction review get harder")
        audit_flags.append("high_bundle_complexity")

    next_steps.extend([
        "separate research-support outputs from any treatment-facing wording",
        "attach evidence tier and citation trace to every target-level claim",
        "grow the non-starter registry so ranking is not driven by fallback candidates",
        "add interaction / contraindication review before bundle export",
        "log clinician or researcher overrides to create an audit trail",
    ])
    if not trained:
        next_steps.insert(0, "run historical replay training and store replay hits back into memory")
    if coverage_ratio < 0.8:
        next_steps.insert(0, "improve closure on uncovered disease signals before claiming protocol quality")

    disclaimer = (
        "this output is appropriate for hypothesis generation and translational review only. "
        "it is not a standalone oncology or rare-disease treatment recommendation and requires expert human review."
    )

    return {
        "readiness_label": readiness_label,
        "readiness_score": round(readiness_score, 3),
        "facility_fit": facility_fit,
        "human_review_required": True,
        "evidence_posture": evidence_posture,
        "source_mix": source_mix,
        "strengths": strengths[:6],
        "weaknesses": weaknesses[:8],
        "blockers": blockers[:6],
        "recommended_next_steps": next_steps[:6],
        "audit_flags": audit_flags[:8],
        "disclaimer": disclaimer,
    }


app = FastAPI(title="MED-R5 Backend", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthOut)
def api_health() -> HealthOut:
    engines = discover_engines()
    return HealthOut(ok=True, engines=engines, engines_found=sorted(list(engines.keys())), time_ms=now_ms())


@app.post("/api/hypothesis/bundle", response_model=HypothesisBundleOut)
def api_hypothesis_bundle(req: HypothesisBundleReq) -> HypothesisBundleOut:
    seed = f"{int(time.time())}"
    targets = unique_norm_genes(req.selected_targets)
    items: List[HypothesisBundleItem] = []
    for i in range(1, 6):
        items.append(
            HypothesisBundleItem(
                idx=i,
                hypothesis=f"EARLY-KILL {i} (DEMO): MATCH {req.drug_name or req.drug_id or 'DRUG'} SIGNATURE AGAINST {', '.join(targets) or 'TARGETS'}.",
                why=["DEMO: TARGET ENGAGEMENT PROXY.", "DEMO: FAIL FAST IF NO SIGNAL AT NON-TOXIC RANGE."],
                early_kill_experiments=[
                    EarlyKillExp(
                        name="TARGET ENGAGEMENT PROXY",
                        cost_eur=6500 + i * 22,
                        days=7 + i,
                        early_kill="STOP IF NO TARGET-ENGAGEMENT SIGNAL AT ANY NON-TOXIC DOSE RANGE.",
                    )
                ],
                cost_total_eur=6500 + i * 22,
                profit_potential=ProfitPotential(scenario="DEMO", range_eur="50k-250k"),
            )
        )
    return HypothesisBundleOut(engine="backend", mode=req.mode, seed=seed, items=items)


@app.post("/api/safeguard/analyze", response_model=SafeguardOut)
def api_safeguard_analyze(req: SafeguardReq) -> SafeguardOut:
    text = req.resolved_text()
    tags = tag_extract(text)

    matches = []
    for fm in FAILURE_LIBRARY:
        if any(t in fm["tags"] for t in tags):
            matches.append(
                FailureMode(
                    summary=fm["summary"],
                    cost_eur=float(fm["cost_eur"]),
                    time_weeks=int(fm["time_weeks"]),
                    avoidable=bool(fm["avoidable"]),
                )
            )

    safeguards = []
    if "CELL_STORAGE" in tags:
        safeguards.append("VERIFY STORAGE MEDIUM + TEMPERATURE AGAINST SOP BEFORE FREEZE/THAW.")
    if "LABELING" in tags:
        safeguards.append("DOUBLE-CHECK LABELS, BARCODE, AND SAMPLE-ID MAP BEFORE RUN.")
    if "INCUBATION" in tags:
        safeguards.append("LOG INCUBATOR TEMP/HUMIDITY; ALERT ON DRIFT; VERIFY WITH EXTERNAL PROBE.")
    if "HYPOTHESIS_RISK" in tags:
        safeguards.append("RUN A SMALL PILOT WITH CONTROL; CAP SPEND UNTIL VARIANCE IS UNDER CONTROL.")
    if not safeguards:
        safeguards.append("APPLY GENERAL QA: CONTROLS, LOT TRACKING, SOP CHECKLIST, AUDIT LOG.")

    estimated_savings = sum([m.cost_eur for m in matches]) * 0.25

    return SafeguardOut(
        tags=tags,
        matches=matches,
        safeguards=safeguards,
        assumptions={"mode": "demo", "tags": tags},
        estimated_savings_eur=float(estimated_savings),
    )


@app.post("/api/safeguard/refresh", response_model=SafeguardOut)
def api_safeguard_refresh(req: SafeguardReq) -> SafeguardOut:
    return api_safeguard_analyze(req)


@app.post("/api/safeguard/memory/add")
def api_safeguard_memory_add(req: MemoryAddReq):
    mem = load_safeguard_memory()
    items = mem.get("items", [])
    for it in req.items:
        txt = (it.text or "").strip()
        if not txt:
            continue
        tags = it.tags or tag_extract(txt)
        items.append({"text": txt, "tags": tags, "count": 1})
    mem["items"] = items
    save_safeguard_memory(mem)
    return {"ok": True, "count": len(req.items)}


@app.get("/api/safeguard/memory/list", response_model=MemoryListOut)
def api_safeguard_memory_list() -> MemoryListOut:
    mem = load_safeguard_memory()
    out = []
    for it in mem.get("items", []):
        out.append(MemoryListItem(text=it.get("text", ""), tags=it.get("tags", []), count=int(it.get("count", 1))))
    return MemoryListOut(items=out)


@app.get("/api/registry/summary", response_model=RegistrySummaryOut)
def api_registry_summary() -> RegistrySummaryOut:
    return build_registry_summary()


@app.post("/api/registry/reload", response_model=RegistrySummaryOut)
def api_registry_reload() -> RegistrySummaryOut:
    if clear_registry_cache is not None:
        try:
            clear_registry_cache()
        except Exception:
            pass
    return build_registry_summary()


@app.post("/api/registry/fda/hydrate")
def api_registry_fda_hydrate() -> Dict[str, Any]:
    if hydrate_fda_approved_drugs is None:
        raise HTTPException(status_code=500, detail="FDA hydration service not available")
    try:
        return hydrate_fda_approved_drugs()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"FDA hydration failed: {exc}")


@app.get("/api/rare/diseases", response_model=List[RareDisease])
def api_rare_diseases() -> List[RareDisease]:
    disease_rows = []
    for d in load_mock_diseases():
        if getattr(d, "id", "") == "custom" or bool(getattr(d, "rare", True)):
            disease_rows.append(RareDisease(id=d.id, name=d.name, genes=d.genes, notes=d.notes, directions=getattr(d, "directions", {}) or {}))
    disease_rows.sort(key=lambda row: (row.id == "custom", row.name.lower()))
    return disease_rows


@app.get("/api/rare/drugs", response_model=List[Candidate])
def api_rare_drugs() -> List[Candidate]:
    return [candidate_to_api(c) for c in _registry_candidate_records("drug")]


@app.get("/api/rare/compounds", response_model=List[Candidate])
def api_rare_compounds() -> List[Candidate]:
    return [candidate_to_api(c) for c in _registry_candidate_records("compound")]


@app.get("/api/rare/physiology", response_model=List[Candidate])
def api_rare_physiology() -> List[Candidate]:
    return [candidate_to_api(c) for c in _registry_candidate_records("physiology", include_physiology=True)]


@app.get("/api/drug-mimic/drugs", response_model=List[Candidate])
def api_drug_mimic_drugs() -> List[Candidate]:
    return [candidate_to_api(c) for c in _drug_mimic_candidate_records()]


@app.post("/api/rare/analyze", response_model=RareAnalyzeOut)
def api_rare_analyze(req: RareAnalyzeReq) -> RareAnalyzeOut:
    try:
        disease = resolve_disease_input(
            disease_id=req.disease_id,
            disease_genes=req.disease_genes,
            disease_gene_text=req.disease_gene_text,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    disease_genes = unique_norm_genes(disease.genes)
    all_candidates = list_all_candidates(include_physiology=bool(req.include_physiology))
    candidate_map = get_candidate_map(all_candidates)
    drugs = [c for c in all_candidates if c.kind == "drug" and getattr(c, "targets", [])]
    compounds = [c for c in all_candidates if c.kind == "compound" and getattr(c, "targets", [])]
    physiology = [c for c in all_candidates if c.kind == "physiology" and getattr(c, "targets", [])]

    spillover_weight = float(req.spillover_weight if req.spillover_weight is not None else 0.12)
    rank_depth = max(1, min(int(req.rank_depth or 8), 200))
    max_results = max(1, min(int(req.max_results or 12), 100))
    max_bundle_items = max(1, int(req.max_bundle_items or 4))
    planner_mode = str(req.planner_mode or "mode_a").strip().lower()
    bundle_strategy = str(req.bundle_strategy or "dynamic").strip().lower()

    ranked_all = rank_candidates(
        disease_genes=disease_genes,
        candidates=all_candidates,
        spillover_weight=spillover_weight,
        top_k=max(rank_depth, max_results, len(all_candidates)),
        disease_directions=getattr(disease, "directions", {}) or {},
    )
    ranked = ranked_all[:max_results]
    ranked_drugs = [r for r in ranked_all if r.get("kind") == "drug"]

    primary_payload = build_primary_result(disease, ranked_drugs)
    primary_id = primary_payload.get("id")
    if primary_id and primary_id in candidate_map:
        primary_candidate = candidate_map[primary_id]
    else:
        primary_candidate = drugs[0] if drugs else None

    deviation_payload = build_deviation_profile(disease, primary_payload)
    support_candidates = compounds + (physiology if bool(req.include_physiology) else []) + ([] if planner_mode == "mode_b" else drugs)
    addon_ranked = build_addon_candidates(
        deviation_genes=deviation_payload.get("uncovered_genes", []),
        candidates=support_candidates,
        selected_ids={primary_id} if primary_id else set(),
        spillover_weight=spillover_weight,
        top_k=10,
        deviation_directions=deviation_payload.get("uncovered_directions", {}) or {},
    )

    addon_ranked = [
        row for row in addon_ranked
        if row.get("covers_deviation_genes") and float(row.get("net_gain", 0.0)) > 0
        and (planner_mode != "mode_b" or row.get("kind") != "drug")
    ]
    addon_pool = [candidate_map[x["id"]] for x in addon_ranked if x["id"] in candidate_map]
    if primary_candidate:
        bundle_payload = choose_best_bundle(
            disease_genes=disease_genes,
            primary=primary_candidate,
            addon_pool=addon_pool,
            max_bundle_items=max_bundle_items,
            spillover_weight=spillover_weight,
            disease_directions=getattr(disease, "directions", {}) or {},
            planner_mode=planner_mode,
            bundle_strategy=bundle_strategy,
            include_physiology=bool(req.include_physiology),
        )
    else:
        bundle_payload = {
            "planner_mode": planner_mode,
            "bundle_strategy": bundle_strategy,
            "bundle_ids": [],
            "bundle_names": [],
            "suggested_addon_ids": [],
            "suggested_addon_names": [],
            "covered_genes": [],
            "uncovered_genes": disease_genes,
            "spillover_genes": [],
            "spillover_count": 0,
            "coverage_ratio": 0.0,
            "score": 0.0,
            "logic_trace": [],
            "selection_reasoning": [],
            "stop_reason": "no primary candidate available",
        }

    bundle_payload.setdefault("suggested_addon_ids", bundle_payload.get("bundle_ids", [])[1:])
    bundle_payload.setdefault("suggested_addon_names", bundle_payload.get("bundle_names", [])[1:])
    disease_direction_map = getattr(disease, "directions", {}) or {}
    bundle_payload.setdefault(
        "uncovered_directions",
        {gene: disease_direction_map.get(gene, "unknown") for gene in bundle_payload.get("uncovered_genes", [])},
    )

    chosen_addon_ids = set(bundle_payload.get("suggested_addon_ids", []))
    addon_summaries = []
    for row in addon_ranked:
        if row["id"] in chosen_addon_ids:
            addon_summaries.append(
                f"{row['name']} adds {', '.join(row['covers_deviation_genes']) or 'no new genes'}"
            )

    selected_ids = req.selected_candidates or bundle_payload.get("bundle_ids", [])
    selection = describe_selection(disease_genes, candidate_map, selected_ids)

    future_payload = build_future_medicine_path(disease, primary_payload, bundle_payload)
    proposals_payload = build_early_kill_proposals(
        disease=disease,
        primary_result=primary_payload,
        deviation_profile=deviation_payload,
        bundle_result=bundle_payload,
        future_path=future_payload,
    )
    for proposal in proposals_payload:
        proposal["protocol_pdf_url"] = proposal_to_protocol_url(proposal.get("id", "proposal"))
    sim_context_payload = build_sim_context(load_rare_sim_memory(), disease, primary_payload)

    summary_payload = {
        **selection,
        "best_primary_candidate_id": primary_payload.get("id"),
        "best_primary_candidate_name": primary_payload.get("name"),
        "best_primary_overlap_genes": primary_payload.get("coverage_genes", []),
        "deviation_uncovered_genes": deviation_payload.get("uncovered_genes", []),
        "suggested_addon_ids": bundle_payload.get("suggested_addon_ids", []),
        "suggested_addon_summary": addon_summaries,
        "bundle_ids": bundle_payload.get("bundle_ids", []),
        "bundle_names": bundle_payload.get("bundle_names", []),
        "rank_depth_used": rank_depth,
        "max_bundle_items_used": max_bundle_items,
        "spillover_weight_used": spillover_weight,
    }
    institutional_payload = build_rare_institutional_assessment(
        disease=disease,
        ranked=ranked,
        primary_payload=primary_payload,
        deviation_payload=deviation_payload,
        bundle_payload=bundle_payload,
        addon_ranked=addon_ranked,
        sim_context_payload=sim_context_payload,
        summary_payload=summary_payload,
    )

    return RareAnalyzeOut(
        disease=RareDisease(id=disease.id, name=disease.name, genes=disease.genes, notes=disease.notes, directions=getattr(disease, "directions", {}) or {}),
        ranked=[RankedCandidate(**row) for row in ranked],
        summary=SelectionSummary(**summary_payload),
        primary=RarePrimaryOut(**primary_payload),
        deviation=RareDeviationOut(**deviation_payload),
        addons=[RareAddonItem(**row) for row in addon_ranked],
        bundle=RareBundleOut(**{k: bundle_payload.get(k) for k in RareBundleOut.model_fields.keys()}),
        future_path=RareFuturePathOut(**future_payload),
        proposals=[RareProposalOut(**row) for row in proposals_payload],
        sim_context=RareSimContextOut(**sim_context_payload),
        institutional_assessment=RareInstitutionalAssessmentOut(**institutional_payload),
    )


@app.post("/api/rare/proposal/protocol", response_model=RareProposalProtocolOut)
def api_rare_proposal_protocol(req: RareProposalProtocolReq) -> RareProposalProtocolOut:
    path = build_rare_protocol_pdf(req)
    return RareProposalProtocolOut(
        ok=True,
        filename=path.name,
        pdf_url=f"/api/rare/proposal/protocol/file/{path.name}",
        estimated_savings_eur=float(req.estimated_savings_eur or 0.0),
    )


@app.get("/api/rare/proposal/protocol/file/{filename}")
def api_rare_proposal_protocol_file(filename: str):
    path = RARE_PROTOCOL_DIR / Path(filename).name
    if not path.exists():
        raise HTTPException(status_code=404, detail="protocol pdf not found")
    return FileResponse(path=str(path), filename=path.name, media_type="application/pdf")


@app.post("/api/rare/sim/train", response_model=RareSimTrainOut)
def api_rare_sim_train(req: RareSimTrainReq) -> RareSimTrainOut:
    start_year = int(req.start_year)
    end_year = int(req.end_year)
    if start_year < 1900 or end_year < start_year:
        raise HTTPException(status_code=400, detail="invalid training window")

    rng = random.Random(int(req.seed))
    disease_bank = [d for d in load_mock_diseases() if d.id != "custom"]
    if not disease_bank:
        raise HTTPException(status_code=500, detail="no rare disease bank available")

    history_bank = ensure_historical_seed_bank()
    history_cases = list(history_bank.cases)

    years = list(range(start_year, end_year + 1))
    trace_sample: List[Dict[str, Any]] = []
    cases_seen = 0
    hit_cases = 0

    from engines.rare_disease_mimic_engine.engine import rank_candidates

    replay_store = historical_replay_store()
    replay_recorded = 0

    for year in years:
        for _ in range(rng.randint(1, 3)):
            cases_seen += 1
            disease = rng.choice(disease_bank)
            ranked = rank_candidates(
                disease_genes=disease.genes,
                candidates=list_all_candidates(),
                spillover_weight=0.12,
                top_k=25,
            )
            best = next((r for r in ranked if r.get("kind") == "drug"), ranked[0] if ranked else None)
            hit = bool(best and len(best.get("overlap_genes", [])) > 0)
            if hit:
                hit_cases += 1

            if len(trace_sample) < 12:
                trace_sample.append(
                    {
                        "year": year,
                        "disease_id": disease.id,
                        "disease_name": disease.name,
                        "genes": disease.genes,
                        "best_primary_id": best["id"] if best else None,
                        "best_primary_name": best["name"] if best else None,
                        "coverage_hits": len(best.get("overlap_genes", [])) if best else 0,
                        "spillover_count": int(best.get("spillover_count", 0)) if best else 0,
                        "hit": hit,
                    }
                )

            if history_cases:
                case = rng.choice(history_cases)
                replay_input = ReplayPredictionInput(
                    disease_name=case.disease_name,
                    discovery_year=year,
                    candidate_features=list(case.tags),
                    suspected_targets=case.discovery.suspected_targets,
                    notes=f"historical replay training pass for {case.disease_name} in synthetic year {year}",
                )
                replay = build_replay_prediction(
                    bank=history_bank,
                    replay_id=f"train_{year}_{case.case_id}_{cases_seen}",
                    replay_input=replay_input,
                )
                replay.hit = bool(replay.matched_case_ids)
                replay.hit_explanation = (
                    "matched stored historical pattern during simulation training"
                    if replay.hit else
                    "no strong historical pattern match found during simulation training"
                )
                replay_store.record_replay(replay)
                replay_recorded += 1
                if replay.hit and case.patterns:
                    replay_store.append_hit_logic(
                        replay_id=replay.replay_id,
                        disease_name=case.disease_name,
                        reusable_rule=case.patterns[0].reusable_rule or case.patterns[0].pattern_summary,
                        confidence=case.patterns[0].confidence,
                        source_ids=case.patterns[0].source_ids,
                    )
                history_bank = replay_store.load()

    hit_ratio = float(hit_cases / max(1, cases_seen))
    pattern_summary = (
        f"trained on {cases_seen} simulated rare cases from {start_year} to {end_year}; "
        f"primary-first then deviation-fill bundle logic stored; "
        f"historical replay bank engaged; "
        f"observed hit ratio {round(hit_ratio, 4)}"
    )

    mem = {
        "trained": True,
        "window": f"{start_year}-{end_year}",
        "cases_seen": cases_seen,
        "hit_ratio": hit_ratio,
        "pattern_summary": pattern_summary,
        "trace_sample": trace_sample,
        "updated_at_ms": now_ms(),
    }
    save_rare_sim_memory(mem)

    return RareSimTrainOut(ok=True, learned=RareSimMemoryOut(**mem))


@app.get("/api/rare/sim/memory", response_model=RareSimMemoryOut)
def api_rare_sim_memory() -> RareSimMemoryOut:
    mem = load_rare_sim_memory()
    return RareSimMemoryOut(**mem)



@app.get("/api/rare/history/bank", response_model=ReplayMemoryBank)
def api_rare_history_bank() -> ReplayMemoryBank:
    return ensure_historical_seed_bank()


@app.post("/api/rare/history/seed", response_model=HistoricalReplaySeedOut)
def api_rare_history_seed() -> HistoricalReplaySeedOut:
    store = historical_replay_store()
    bank = store.replace_cases(get_seed_historical_cases())
    return HistoricalReplaySeedOut(
        ok=True,
        cases_loaded=len(bank.cases),
        window=f"{bank.window_start_year}-{bank.window_end_year}",
        bank_path=str(HISTORICAL_REPLAY_BANK_PATH),
    )


@app.post("/api/rare/history/replay", response_model=ReplayPredictionResult)
def api_rare_history_replay(req: HistoricalReplayRunReq) -> ReplayPredictionResult:
    store = historical_replay_store()
    bank = ensure_historical_seed_bank()
    suspected_targets = req.suspected_targets or []
    replay_input = ReplayPredictionInput(
        disease_name=req.disease_name,
        discovery_year=req.discovery_year,
        candidate_features=req.candidate_features,
        suspected_targets=suspected_targets,
        notes=req.notes,
    )
    replay_id = (req.replay_id or f"replay_{now_ms()}").strip()
    replay = build_replay_prediction(bank=bank, replay_id=replay_id, replay_input=replay_input)
    replay.hit = req.hit if req.hit is not None else bool(replay.matched_case_ids)
    replay.hit_explanation = req.hit_explanation or (
        "matched historical disease-to-drug logic" if replay.hit else "no strong historical match yet"
    )

    if req.store_if_hit and replay.hit:
        reusable_rule = replay.predicted_improvement_logic or replay.predicted_first_medicine_logic or replay.predicted_failure_logic
        if reusable_rule:
            store.append_hit_logic(
                replay_id=replay.replay_id,
                disease_name=req.disease_name,
                reusable_rule=reusable_rule,
                confidence=replay.confidence,
                source_ids=[],
            )
            replay.stored_logic_note = "hit logic stored back into replay memory"
            bank = store.load()

    store.record_replay(replay)
    return replay


@app.post("/api/rare/history/store-hit", response_model=ReplayMemoryBank)
def api_rare_history_store_hit(req: HistoricalReplayStoreHitReq) -> ReplayMemoryBank:
    store = historical_replay_store()
    ensure_historical_seed_bank()
    return store.append_hit_logic(
        replay_id=req.replay_id,
        disease_name=req.disease_name,
        reusable_rule=req.reusable_rule,
        confidence=req.confidence,
        source_ids=req.source_ids,
    )


@app.post("/api/rare/history/train", response_model=HistoricalReplayTrainOut)
def api_rare_history_train(req: HistoricalReplayTrainReq) -> HistoricalReplayTrainOut:
    start_year = int(req.start_year)
    end_year = int(req.end_year)
    if start_year < 1900 or end_year < start_year:
        raise HTTPException(status_code=400, detail="invalid historical training window")

    store = historical_replay_store()
    bank = ensure_historical_seed_bank()
    rng = random.Random(int(req.seed))
    max_cases_per_year = max(1, min(int(req.max_cases_per_year), 10))

    cases_replayed = 0
    replay_runs = 0
    matched_case_ids: List[str] = []

    for year in range(start_year, end_year + 1):
        for _ in range(rng.randint(1, max_cases_per_year)):
            case = rng.choice(bank.cases)
            replay_input = ReplayPredictionInput(
                disease_name=case.disease_name,
                discovery_year=year,
                candidate_features=list(case.tags),
                suspected_targets=case.discovery.suspected_targets,
                notes=f"historical replay training for {case.disease_name} in year {year}",
            )
            replay = build_replay_prediction(
                bank=bank,
                replay_id=f"history_train_{year}_{case.case_id}_{cases_replayed+1}",
                replay_input=replay_input,
            )
            replay.hit = bool(replay.matched_case_ids)
            replay.hit_explanation = (
                "historical replay matched a stored disease-to-drug pattern"
                if replay.hit else
                "historical replay did not yet match a stored pattern"
            )
            store.record_replay(replay)
            replay_runs += 1
            cases_replayed += 1

            if replay.hit:
                matched_case_ids.extend(replay.matched_case_ids[:2])
                reusable_rule = replay.predicted_improvement_logic or replay.predicted_first_medicine_logic
                if reusable_rule:
                    store.append_hit_logic(
                        replay_id=replay.replay_id,
                        disease_name=case.disease_name,
                        reusable_rule=reusable_rule,
                        confidence=replay.confidence,
                        source_ids=[],
                    )
                    bank = store.load()

    return HistoricalReplayTrainOut(
        ok=True,
        window=f"{start_year}-{end_year}",
        cases_replayed=cases_replayed,
        replays_recorded=replay_runs,
        matched_case_ids=sorted(set(matched_case_ids)),
        note="historical replay training stored replay runs and hit logic back into memory",
    )


@app.get("/api/compound/reports", response_model=CompoundReportListOut)
def api_compound_reports() -> CompoundReportListOut:
    items: List[CompoundReportItem] = []
    if ENGINES_DIR.exists():
        for p in ENGINES_DIR.rglob("*_report.pdf"):
            compound = p.name.replace("_report.pdf", "").replace("_", " ").strip()
            items.append(CompoundReportItem(compound=compound, path=str(p)))
    items.sort(key=lambda x: x.compound.lower())
    return CompoundReportListOut(items=items)


@app.get("/api/compound/report/{compound}")
def api_compound_report_download(compound: str):
    p = find_compound_report_pdf(compound)
    if not p or not p.exists():
        raise HTTPException(status_code=404, detail="report not found")
    return FileResponse(path=str(p), filename=p.name, media_type="application/pdf")


@app.get("/api/system/memory/summary", response_model=SystemMemorySummaryOut)
def api_system_memory_summary() -> SystemMemorySummaryOut:
    return SystemMemorySummaryOut(**build_system_memory_summary())


@app.post("/api/compound/analyze", response_model=CompoundAnalyzeOut)
def api_compound_analyze(req: CompoundAnalyzeReq) -> CompoundAnalyzeOut:
    compound = (req.compound or "").strip()
    if not compound:
        raise HTTPException(status_code=400, detail="compound is empty")

    context = (req.context or "").strip()
    targets = unique_norm_genes(req.targets or [])
    max_papers = max(1, min(int(req.max_papers or 8), 25))

    res = analyze_compound(
        compound=compound,
        context=context,
        targets=targets,
        max_papers=max_papers,
        use_llm=bool(req.use_llm),
    )

    p = find_compound_report_pdf(compound)
    pdf_url = f"/api/compound/report/{compound}" if p else None

    try:
        append_recent_evidence_query(compound=compound, context=context, targets=targets)
    except Exception:
        pass

    return CompoundAnalyzeOut(
        compound=compound,
        objective_summary=res.get("objective_summary", ""),
        subjective_summary=res.get("subjective_summary", ""),
        pmids=res.get("pmids", []),
        report_pdf_url=pdf_url,
        notes=res.get("notes", ""),
    )


# -----------------------------
# EVIDENCE API
# -----------------------------
class PubMedSearchOut(BaseModel):
    query: str
    pmids: List[str]
    total: int
    cached: bool


class PubMedArticleOut(BaseModel):
    pmid: str
    title: str = ""
    year: Optional[int] = None
    journal: str = ""
    authors: List[str] = Field(default_factory=list)
    abstract: str = ""


class CompoundTargetEvidenceReq(BaseModel):
    compound: str
    target: str
    disease: str = ""
    drug: str = ""
    max_papers: int = 8
    use_llm: bool = True


class CompoundTargetEvidenceOut(BaseModel):
    compound: str
    target: str
    query: str
    direction: str
    confidence: float
    key_findings: List[str]
    cautions: List[str]
    pmids: List[str]
    cached: bool


@app.get("/api/evidence/pubmed/search", response_model=PubMedSearchOut)
def api_pubmed_search(q: str, max_results: int = 10) -> PubMedSearchOut:
    q = (q or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail="q is empty")
    max_results = max(1, min(int(max_results), 50))
    r = pubmed_search(q, retmax=max_results)
    return PubMedSearchOut(query=q, pmids=r["pmids"], total=r["total"], cached=r["cached"])


@app.get("/api/evidence/pubmed/article/{pmid}", response_model=PubMedArticleOut)
def api_pubmed_article(pmid: str) -> PubMedArticleOut:
    pmid = (pmid or "").strip()
    if not pmid.isdigit():
        raise HTTPException(status_code=400, detail="pmid must be numeric")

    art = pubmed_get_article(pmid)
    if not art:
        raise HTTPException(status_code=404, detail="pmid not found")
    return PubMedArticleOut(**art)


@app.post("/api/evidence/compound_target", response_model=CompoundTargetEvidenceOut)
def api_compound_target(req: CompoundTargetEvidenceReq) -> CompoundTargetEvidenceOut:
    compound = (req.compound or "").strip()
    target = norm_gene(req.target or "")
    if not compound or not target:
        raise HTTPException(status_code=400, detail="compound/target required")

    max_papers = max(1, min(int(req.max_papers or 8), 25))
    r = analyze_compound_target(
        compound=compound,
        target=target,
        disease=(req.disease or "").strip(),
        drug=(req.drug or "").strip(),
        max_papers=max_papers,
        use_llm=bool(req.use_llm),
    )

    return CompoundTargetEvidenceOut(
        compound=compound,
        target=target,
        query=r["query"],
        direction=r["direction"],
        confidence=float(r["confidence"]),
        key_findings=r.get("key_findings", []),
        cautions=r.get("cautions", []),
        pmids=r.get("pmids", []),
        cached=bool(r.get("cached", False)),
    )

# -----------------------------
# SELF LLM ENDPOINTS
# -----------------------------

from self_llm.engine import generate_proposal
from self_llm.loop_runner import run_loop
from self_llm.patch_suggester import suggest_patch


class SelfLLMRequest(BaseModel):
    hint: str | None = None


class SelfLLMLoopRequest(BaseModel):
    hint: str | None = None
    iterations: int = 5


class SelfLLMPatchRequest(BaseModel):
    proposal: str = ""


@app.post("/api/self_llm/start")
def api_self_llm_start(req: SelfLLMRequest):
    return generate_proposal(req.hint or "")


@app.post("/api/self_llm/run_loop")
def api_self_llm_loop(req: SelfLLMLoopRequest):
    results = run_loop(iterations=req.iterations, hint=req.hint or "")
    return {"proposals": results}


@app.post("/api/self_llm/suggest_patch")
def api_self_llm_patch(req: SelfLLMPatchRequest):
    patch = suggest_patch(req.proposal or "")
    return {"patch": patch}
