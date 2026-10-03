from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set
import re

try:
    from services.master_registry import (
        get_all_candidates as registry_get_all_candidates,
        get_candidates as registry_get_candidates,
        get_rare_diseases as registry_get_rare_diseases,
        get_all_drugs as registry_get_all_drugs,
    )
except Exception:
    registry_get_all_candidates = None
    registry_get_candidates = None
    registry_get_rare_diseases = None
    registry_get_all_drugs = None


@dataclass
class RareDiseaseRecord:
    id: str
    name: str
    genes: List[str]
    notes: str = ""
    directions: Dict[str, str] = field(default_factory=dict)
    category: str = ""
    rare: bool = True
    source: str = "registry"


@dataclass
class CandidateRecord:
    id: str
    name: str
    targets: List[str]
    source: str = "demo"
    kind: str = "drug"
    effects: Dict[str, str] = field(default_factory=dict)
    strength_map: Dict[str, float] = field(default_factory=dict)
    spillover_targets: List[str] = field(default_factory=list)
    status: str = "starter"
    notes: str = ""
    xrefs: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    target_confidence_map: Dict[str, str] = field(default_factory=dict)


_POSITIVE_DISEASE = {"up", "overactive", "gain", "high", "elevated"}
_NEGATIVE_DISEASE = {"down", "underactive", "loss", "low", "reduced"}
_INHIBIT = {"inhibit", "block", "suppress", "down", "reduce", "antagonize"}
_ACTIVATE = {"activate", "increase", "up", "boost", "agonize", "restore"}

_FALLBACK_DISEASE_BANK: List[RareDiseaseRecord] = [
    RareDiseaseRecord(
        id="rett_demo",
        name="rett syndrome",
        genes=["MECP2", "BDNF", "CREB1", "HDAC2", "GSK3B"],
        notes="fallback rare disease profile",
        directions={"MECP2": "down", "BDNF": "down", "CREB1": "down", "HDAC2": "up", "GSK3B": "up"},
        category="neurology",
        rare=True,
        source="fallback",
    ),
    RareDiseaseRecord(
        id="fragilex_demo",
        name="fragile x syndrome",
        genes=["FMR1", "CREB1", "ERK1", "GSK3B", "MMP9"],
        notes="fallback rare disease profile",
        directions={"FMR1": "down", "CREB1": "down", "ERK1": "up", "GSK3B": "up", "MMP9": "up"},
        category="neurology",
        rare=True,
        source="fallback",
    ),
    RareDiseaseRecord(
        id="angelman_demo",
        name="angelman syndrome",
        genes=["UBE3A", "BDNF", "CREB1", "GSK3B", "HDAC2"],
        notes="fallback rare disease profile",
        directions={"UBE3A": "down", "BDNF": "down", "CREB1": "down", "GSK3B": "up", "HDAC2": "up"},
        category="neurology",
        rare=True,
        source="fallback",
    ),
    RareDiseaseRecord(
        id="huntington_demo",
        name="huntington disease",
        genes=["HTT", "BDNF", "CREB1", "CASP3", "GSK3B"],
        notes="fallback rare disease profile",
        directions={"HTT": "up", "BDNF": "down", "CREB1": "down", "CASP3": "up", "GSK3B": "up"},
        category="neurology",
        rare=True,
        source="fallback",
    ),
]

_FALLBACK_CANDIDATES: List[CandidateRecord] = [
    CandidateRecord(
        id="d_valproate",
        name="valproate",
        kind="drug",
        targets=["HDAC2", "GSK3B", "CREB1"],
        effects={"HDAC2": "inhibit", "GSK3B": "inhibit", "CREB1": "activate"},
        strength_map={"HDAC2": 0.85, "GSK3B": 0.72, "CREB1": 0.22},
        spillover_targets=["ABCB1"],
        source="fallback",
    ),
    CandidateRecord(
        id="d_lithium",
        name="lithium",
        kind="drug",
        targets=["GSK3B", "CREB1"],
        effects={"GSK3B": "inhibit", "CREB1": "activate"},
        strength_map={"GSK3B": 0.82, "CREB1": 0.30},
        spillover_targets=["INPP1"],
        source="fallback",
    ),
    CandidateRecord(
        id="c_curcumin",
        name="curcumin",
        kind="compound",
        targets=["CREB1", "BDNF", "GSK3B"],
        effects={"CREB1": "activate", "BDNF": "activate", "GSK3B": "inhibit"},
        strength_map={"CREB1": 0.70, "BDNF": 0.35, "GSK3B": 0.20},
        spillover_targets=["AKT1", "NFKB1"],
        source="fallback",
    ),
    CandidateRecord(
        id="d_evolocumab",
        name="evolocumab",
        kind="drug",
        targets=["PCSK9"],
        effects={"PCSK9": "inhibit"},
        strength_map={"PCSK9": 0.95},
        spillover_targets=[],
        source="fallback",
    ),
    CandidateRecord(
        id="d_atorvastatin",
        name="atorvastatin",
        kind="drug",
        targets=["HMGCR"],
        effects={"HMGCR": "inhibit"},
        strength_map={"HMGCR": 0.95},
        spillover_targets=[],
        source="fallback",
    ),
    CandidateRecord(
        id="d_sirolimus",
        name="sirolimus (rapamycin)",
        kind="drug",
        targets=["MTOR"],
        effects={"MTOR": "inhibit"},
        strength_map={"MTOR": 0.95},
        spillover_targets=[],
        source="fallback",
    ),
    CandidateRecord(
        id="d_riluzole",
        name="riluzole",
        kind="drug",
        targets=["SLC1A2"],
        effects={"SLC1A2": "activate"},
        strength_map={"SLC1A2": 0.50},
        spillover_targets=[],
        source="fallback",
    ),
    CandidateRecord(
        id="c_resveratrol",
        name="resveratrol",
        kind="compound",
        targets=["SIRT1", "CREB1"],
        effects={"SIRT1": "activate", "CREB1": "activate"},
        strength_map={"SIRT1": 0.60, "CREB1": 0.20},
        spillover_targets=["AMPK"],
        source="fallback",
    ),
]


def unique_norm_genes(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for value in values or []:
        gene = str(value or "").strip().upper().replace(" ", "").replace("-", "")
        if gene and gene not in seen:
            out.append(gene)
            seen.add(gene)
    return out


def _candidate_from_registry(item: Dict[str, object]) -> CandidateRecord:
    targets_raw = item.get("targets") or []
    targets: List[str] = []
    effects: Dict[str, str] = {}
    strength_map: Dict[str, float] = {}
    spillover_targets: List[str] = []
    target_confidence_map: Dict[str, str] = {}

    for target in targets_raw:
        if not isinstance(target, dict):
            continue
        gene = str(target.get("gene") or "").strip().upper().replace(" ", "").replace("-", "")
        if not gene:
            continue
        if gene not in targets:
            targets.append(gene)
        effects[gene] = str(target.get("direction") or target.get("effect") or "modulate").strip().lower()
        try:
            strength_map[gene] = float(target.get("strength", 0.6) or 0.6)
        except Exception:
            strength_map[gene] = 0.6
        target_confidence_map[gene] = str(target.get("confidence") or item.get("status") or "starter").strip().lower()
        if bool(target.get("spillover", False)) and gene not in spillover_targets:
            spillover_targets.append(gene)

    return CandidateRecord(
        id=str(item.get("id") or "").strip(),
        name=str(item.get("name") or "").strip(),
        targets=targets,
        source=str(item.get("source") or "registry").strip().lower(),
        kind=str(item.get("kind") or item.get("type") or "drug").strip().lower(),
        effects=effects,
        strength_map=strength_map,
        spillover_targets=spillover_targets,
        status=str(item.get("status") or "starter").strip().lower(),
        notes=str(item.get("notes") or "").strip(),
        xrefs=[str(x).strip() for x in (item.get("xrefs") or []) if str(x).strip()],
        aliases=[str(x).strip() for x in (item.get("aliases") or []) if str(x).strip()],
        target_confidence_map=target_confidence_map,
    )


def _disease_from_registry(item: Dict[str, object]) -> RareDiseaseRecord:
    directions_raw = item.get("directions") or {}
    directions = {
        str(k or "").strip().upper().replace(" ", "").replace("-", ""): str(v or "").strip().lower()
        for k, v in directions_raw.items()
        if str(k or "").strip()
    }
    return RareDiseaseRecord(
        id=str(item.get("id") or "").strip(),
        name=str(item.get("name") or "").strip(),
        genes=unique_norm_genes(item.get("genes") or []),
        notes=str(item.get("notes") or "").strip(),
        directions=directions,
        category=str(item.get("category") or "").strip().lower(),
        rare=bool(item.get("rare", True)),
        source="registry",
    )


_EVIDENCE_LABEL_RANK = {
    "human": 5,
    "clinical": 5,
    "approved": 4,
    "listed": 4,
    "hydrated": 4,
    "preclinical": 3,
    "animal": 2,
    "invitro": 2,
    "mechanistic": 2,
    "starter": 1,
    "fallback": 0,
    "unknown": 0,
}


def _normalize_confidence_label(value: str) -> str:
    token = str(value or "").strip().lower()
    if not token:
        return "unknown"
    aliases = {
        "clinical": "human",
        "approved_drug": "approved",
        "openfda_drugsfda": "approved",
        "rxterms": "listed",
        "pubchem_seed": "preclinical",
        "starter_registry": "starter",
    }
    return aliases.get(token, token)


def _evidence_summary(candidate: CandidateRecord, genes: Iterable[str]) -> Dict[str, object]:
    matched = unique_norm_genes(genes)
    labels: List[str] = []
    trace: List[str] = []
    for gene in matched:
        label = _normalize_confidence_label(candidate.target_confidence_map.get(gene) or candidate.status or candidate.source)
        labels.append(label)
        trace.append(f"{gene}:{label}")
    labels = [x for x in labels if x]
    if labels:
        labels_sorted = sorted(labels, key=lambda item: (_EVIDENCE_LABEL_RANK.get(item, 0), item), reverse=True)
        tier = labels_sorted[0]
        evidence_score = round(sum(_EVIDENCE_LABEL_RANK.get(item, 0) for item in labels) / max(1, len(labels)), 2)
    else:
        tier = _normalize_confidence_label(candidate.status or candidate.source)
        evidence_score = float(_EVIDENCE_LABEL_RANK.get(tier, 0))
    return {
        "evidence_tier": tier,
        "evidence_score": evidence_score,
        "citation_trace": trace[:6],
        "xref_count": len(candidate.xrefs or []),
        "notes_excerpt": (candidate.notes or "")[:180],
        "registry_status": candidate.status or "starter",
    }


def load_mock_diseases() -> List[RareDiseaseRecord]:
    out: List[RareDiseaseRecord] = []
    if registry_get_rare_diseases is not None:
        try:
            out = [_disease_from_registry(item) for item in registry_get_rare_diseases()]
        except Exception:
            out = []
    if not out:
        out = list(_FALLBACK_DISEASE_BANK)
    out.append(
        RareDiseaseRecord(
            id="custom",
            name="custom (paste genes)",
            genes=[],
            notes="custom pasted genes",
            directions={},
            category="custom",
            rare=False,
            source="runtime",
        )
    )
    return out


def load_mock_candidates(kind: Optional[str] = None, include_physiology: bool = True) -> List[CandidateRecord]:
    out: List[CandidateRecord] = []
    if registry_get_candidates is not None:
        try:
            out = [_candidate_from_registry(item) for item in registry_get_candidates(kind, include_physiology=include_physiology)]
        except Exception:
            out = []
    if not out:
        if kind is None:
            out = list(_FALLBACK_CANDIDATES)
        else:
            kind_l = str(kind).strip().lower()
            out = [c for c in _FALLBACK_CANDIDATES if c.kind == kind_l]
    return out


def list_all_candidates(include_physiology: bool = True) -> List[CandidateRecord]:
    return load_mock_candidates(None, include_physiology=include_physiology)


def get_candidate_map(candidates: Sequence[CandidateRecord]) -> Dict[str, CandidateRecord]:
    return {c.id: c for c in candidates}


_UP_MARKERS = (
    "up", "upregulated", "upregulation", "overactive", "overactivated", "hyperactive",
    "activated", "activation", "gain", "gain of function", "gof", "elevated",
    "increased", "too much", "constitutively active", "overexpressed",
)

_DOWN_MARKERS = (
    "down", "downregulated", "downregulation", "underactive", "suppressed", "suppression",
    "inhibited", "inhibition", "loss", "loss of function", "lof", "reduced", "decreased",
    "deficient", "silenced", "too low",
)


def _normalize_direction_token(value: str) -> str:
    token = str(value or "").strip().lower().replace("_", " ").replace("-", " ")
    token = re.sub(r"\s+", " ", token).strip()
    if not token:
        return "unknown"
    if any(marker in token for marker in _UP_MARKERS):
        return "up"
    if any(marker in token for marker in _DOWN_MARKERS):
        return "down"
    return "unknown"


def _looks_like_gene_token(token: str) -> bool:
    t = str(token or "").strip().upper()
    return bool(t) and bool(re.match(r"^[A-Z0-9][A-Z0-9_-]{1,20}$", t))


def _parse_signed_gene_text(text: str) -> tuple[List[str], Dict[str, str]]:
    if not text:
        return [], {}

    raw_chunks = [part.strip() for part in re.split(r"[\n;|,]+", str(text)) if part.strip()]
    genes: List[str] = []
    directions: Dict[str, str] = {}

    for chunk in raw_chunks:
        tokens = [tok for tok in re.split(r"\s+", chunk.strip()) if tok]
        if not tokens:
            continue

        # old style: "MECP2 BDNF CREB1"
        # but do not misread direction words like "up" / "down" as genes.
        remaining_text = " ".join(tokens[1:])
        looks_like_old_gene_list = (
            len(tokens) > 1
            and all(_looks_like_gene_token(tok) for tok in tokens)
            and _normalize_direction_token(remaining_text) == "unknown"
            and tokens[-1].strip().lower() not in {"up", "down", "gof", "lof"}
        )
        if looks_like_old_gene_list:
            for tok in tokens:
                gene = unique_norm_genes([tok])[0]
                if gene not in genes:
                    genes.append(gene)
                directions.setdefault(gene, "unknown")
            continue

        gene = unique_norm_genes([tokens[0]])
        if not gene:
            continue
        gene = gene[0]
        if gene not in genes:
            genes.append(gene)
        direction = _normalize_direction_token(" ".join(tokens[1:])) if len(tokens) > 1 else "unknown"
        directions[gene] = direction

    return genes, directions


def _genes_from_text(text: str) -> List[str]:
    genes, _directions = _parse_signed_gene_text(text)
    return genes


def resolve_disease_input(
    disease_id: str = "custom",
    disease_genes: Optional[Iterable[str]] = None,
    disease_gene_text: str = "",
) -> RareDiseaseRecord:
    disease_id = str(disease_id or "custom").strip()
    disease_bank = load_mock_diseases()
    if disease_id != "custom":
        for d in disease_bank:
            if d.id == disease_id:
                return d
        raise KeyError(f"unknown disease_id: {disease_id}")

    text_genes, text_directions = _parse_signed_gene_text(disease_gene_text)
    genes = unique_norm_genes(list(disease_genes or []) + text_genes)
    if not genes:
        raise ValueError("no disease genes provided")

    merged_directions = {g: "unknown" for g in genes}
    for gene, direction in text_directions.items():
        if gene in merged_directions:
            merged_directions[gene] = direction or "unknown"

    return RareDiseaseRecord(
        id="custom",
        name="custom (paste genes)",
        genes=genes,
        notes="custom pasted genes",
        directions=merged_directions,
        category="custom",
        rare=False,
        source="runtime",
    )


def _gene_weights(genes: Sequence[str]) -> Dict[str, float]:
    weights: Dict[str, float] = {}
    for idx, gene in enumerate(unique_norm_genes(genes)):
        weights[gene] = round(max(0.40, 1.0 - (idx * 0.08)), 3)
    return weights


def _gene_directions(disease: RareDiseaseRecord) -> Dict[str, str]:
    if disease.directions:
        return {k: str(v or "unknown").strip().lower() for k, v in disease.directions.items()}
    return {g: "unknown" for g in unique_norm_genes(disease.genes)}


def _desired_effect(direction: str) -> str:
    token = str(direction or "unknown").strip().lower().replace("-", "_")
    if token in _POSITIVE_DISEASE:
        return "inhibit"
    if token in _NEGATIVE_DISEASE:
        return "activate"
    return "modulate"


def _alignment(direction: str, effect: str) -> float:
    desired = _desired_effect(direction)
    effect = str(effect or "unknown").strip().lower()
    if desired == "modulate":
        return 0.60 if effect != "unknown" else 0.35
    if desired == "inhibit":
        if effect in _INHIBIT:
            return 1.00
        if effect in _ACTIVATE:
            return -0.85
        return 0.25
    if desired == "activate":
        if effect in _ACTIVATE:
            return 1.00
        if effect in _INHIBIT:
            return -0.85
        return 0.25
    return 0.0


def rank_candidates(
    disease_genes: Iterable[str],
    candidates: Sequence[CandidateRecord],
    spillover_weight: float = 0.12,
    top_k: int = 8,
    disease_directions: Optional[Dict[str, str]] = None,
) -> List[Dict[str, object]]:
    genes = unique_norm_genes(disease_genes)
    gene_set = set(genes)
    weights = _gene_weights(genes)

    disease_obj = None
    for d in load_mock_diseases():
        if d.id == "custom":
            continue
        if unique_norm_genes(d.genes) == genes:
            disease_obj = d
            break

    directions = {g: "unknown" for g in genes}
    if disease_obj:
        directions.update(_gene_directions(disease_obj))
    if disease_directions:
        for gene, direction in disease_directions.items():
            gene_n = unique_norm_genes([gene])
            if gene_n and gene_n[0] in directions:
                directions[gene_n[0]] = _normalize_direction_token(direction)

    rows: List[Dict[str, object]] = []
    for c in candidates:
        overlap = []
        opposed = []
        raw_score = 0.0
        wrong_way_penalty = 0.0
        for gene in genes:
            if gene not in c.targets:
                continue
            strength = float(c.strength_map.get(gene, 0.6))
            align = _alignment(directions.get(gene, "unknown"), c.effects.get(gene, "unknown"))
            contribution = float(weights.get(gene, 0.5)) * strength * align
            if contribution > 0.10:
                overlap.append(gene)
                raw_score += contribution
            elif contribution < -0.05:
                opposed.append(gene)
                wrong_way_penalty += abs(contribution)

        spillover = [g for g in c.spillover_targets if g not in gene_set]
        spillover_penalty = len(spillover) * float(spillover_weight)
        score = round(raw_score - wrong_way_penalty - spillover_penalty, 3)

        evidence = _evidence_summary(c, overlap)
        rows.append(
            {
                "id": c.id,
                "name": c.name,
                "kind": c.kind,
                "score": score,
                "raw_score": round(raw_score, 3),
                "overlap_genes": sorted(overlap),
                "covered_genes": sorted(overlap),
                "opposed_genes": sorted(opposed),
                "spillover_genes": sorted(spillover),
                "spillover_count": len(spillover),
                "target_count": len(overlap),
                "source": c.source,
                "evidence_tier": evidence["evidence_tier"],
                "evidence_score": evidence["evidence_score"],
                "citation_trace": evidence["citation_trace"],
                "xref_count": evidence["xref_count"],
                "notes_excerpt": evidence["notes_excerpt"],
                "registry_status": evidence["registry_status"],
            }
        )

    rows.sort(key=lambda row: (float(row["score"]), float(row["raw_score"]), -int(row["spillover_count"])), reverse=True)
    return rows[: max(1, int(top_k))]


def build_primary_result(disease: RareDiseaseRecord, ranked_drugs: Sequence[Dict[str, object]]) -> Dict[str, object]:
    genes = unique_norm_genes(disease.genes)
    best = dict(ranked_drugs[0]) if ranked_drugs else {
        "id": None,
        "name": None,
        "score": 0.0,
        "raw_score": 0.0,
        "covered_genes": [],
        "spillover_genes": [],
        "source": "demo",
    }
    coverage_genes = list(best.get("covered_genes", []))
    coverage_ratio = round(len(coverage_genes) / max(1, len(genes)), 3)
    best.update(
        {
            "coverage_genes": coverage_genes,
            "coverage_count": len(coverage_genes),
            "coverage_ratio": coverage_ratio,
            "spillover_count": len(best.get("spillover_genes", [])),
            "rationale": f"best current market-style candidate by signed weighted disease coverage and spillover penalty: {best.get('name') or 'none'}",
            "evidence_tier": best.get("evidence_tier", "unknown"),
            "evidence_score": float(best.get("evidence_score", 0.0) or 0.0),
            "citation_trace": list(best.get("citation_trace", []))[:6],
            "xref_count": int(best.get("xref_count", 0) or 0),
            "registry_status": str(best.get("registry_status", "starter") or "starter"),
            "notes_excerpt": str(best.get("notes_excerpt", "") or ""),
        }
    )
    return best


def build_deviation_profile(disease: RareDiseaseRecord, primary_result: Dict[str, object]) -> Dict[str, object]:
    genes = unique_norm_genes(disease.genes)
    covered = set(primary_result.get("coverage_genes", []))
    uncovered = [g for g in genes if g not in covered]
    disease_directions = _gene_directions(disease)
    return {
        "covered_genes": sorted(covered),
        "uncovered_genes": uncovered,
        "uncovered_directions": {g: disease_directions.get(g, "unknown") for g in uncovered},
        "covered_count": len(covered),
        "uncovered_count": len(uncovered),
        "coverage_ratio": round(len(covered) / max(1, len(genes)), 3),
        "summary": "deviation genes not covered by current best primary candidate",
    }


def build_addon_candidates(
    deviation_genes: Sequence[str],
    candidates: Sequence[CandidateRecord],
    selected_ids: Optional[Set[str]] = None,
    spillover_weight: float = 0.12,
    top_k: int = 6,
    deviation_directions: Optional[Dict[str, str]] = None,
) -> List[Dict[str, object]]:
    selected_ids = set(selected_ids or set())
    deviation = unique_norm_genes(deviation_genes)
    if not deviation:
        return []

    ranked = rank_candidates(
        disease_genes=deviation,
        candidates=[c for c in candidates if c.id not in selected_ids],
        spillover_weight=spillover_weight,
        top_k=max(20, top_k),
        disease_directions=deviation_directions,
    )

    out: List[Dict[str, object]] = []
    for row in ranked:
        covers = list(row.get("covered_genes", []))
        spill = list(row.get("spillover_genes", []))
        net_gain = round(float(row.get("score", 0.0)) - (0.05 if not covers else 0.0), 3)
        if covers:
            bundle_compat = "high" if net_gain > 0.35 else "medium" if net_gain > 0 else "low"
            why = f"covers {', '.join(covers)}"
        else:
            bundle_compat = "low"
            why = "does not close remaining deviation"

        out.append(
            {
                "id": row["id"],
                "name": row["name"],
                "kind": row["kind"],
                "score": row["score"],
                "covers_deviation_genes": covers,
                "new_spillover_genes": spill,
                "net_gain": net_gain,
                "bundle_compatibility": bundle_compat,
                "why_selected": why,
                "source": row.get("source", "demo"),
                "evidence_tier": row.get("evidence_tier", "unknown"),
                "evidence_score": float(row.get("evidence_score", 0.0) or 0.0),
                "citation_trace": list(row.get("citation_trace", []))[:6],
                "xref_count": int(row.get("xref_count", 0) or 0),
                "notes_excerpt": str(row.get("notes_excerpt", "") or ""),
                "registry_status": str(row.get("registry_status", "starter") or "starter"),
            }
        )

    out.sort(key=lambda r: (float(r["net_gain"]), len(r["covers_deviation_genes"]), -len(r["new_spillover_genes"])), reverse=True)
    return out[: max(1, int(top_k))]


def build_future_medicine_path(
    disease: RareDiseaseRecord,
    primary_result: Dict[str, object],
    bundle_result: Dict[str, object],
) -> Dict[str, object]:
    genes = unique_norm_genes(disease.genes)
    remaining = unique_norm_genes(bundle_result.get("uncovered_genes", []))
    weighted_gap = len(remaining) / max(1, len(genes))
    creation_justified = bool(remaining)
    return {
        "ideal_target_set": genes,
        "current_market_coverage_genes": unique_norm_genes(primary_result.get("coverage_genes", [])),
        "remaining_gap_genes": remaining,
        "current_market_coverage_ratio": round(len(primary_result.get("coverage_genes", [])) / max(1, len(genes)), 3),
        "creation_justified": creation_justified,
        "creation_rationale": (
            f"remaining weighted gap after current market bundle: {', '.join(remaining)}"
            if remaining else
            "current market bundle is already close to the ideal disease target set"
        ),
        "translation_note": "compare best market candidate against gap-closing future medicine logic, then use early-kill experiments before large commitment",
        "justification_score": round(weighted_gap + (0.08 * len(bundle_result.get("spillover_genes", []))), 3),
    }


def build_early_kill_proposals(
    disease: RareDiseaseRecord,
    primary_result: Dict[str, object],
    deviation_profile: Dict[str, object],
    bundle_result: Dict[str, object],
    future_path: Dict[str, object],
) -> List[Dict[str, object]]:
    deviation_focus = ", ".join(deviation_profile.get("uncovered_genes", [])) or "no major deviation left"
    bundle_focus = ", ".join(bundle_result.get("bundle_names", [])) or ", ".join(bundle_result.get("bundle_ids", [])) or (primary_result.get("name") or "primary")
    future_focus = ", ".join(future_path.get("remaining_gap_genes", [])) or "no residual gap"
    logic_trace = bundle_result.get("selection_reasoning", []) or []
    lead_hypothesis = f"{bundle_focus} could neutralize the signed disease deviation of {disease.name}"
    base_savings = 2500 + (900 * len(bundle_result.get("bundle_ids", []))) + (700 * len(deviation_profile.get("uncovered_genes", [])))
    return [
        {
            "id": "primary_engagement",
            "title": "primary target engagement check",
            "focus": primary_result.get("name") or "none",
            "goal": "verify that the primary engages the main covered disease genes before broader spend",
            "cheap_readout": "low-cost mechanistic marker panel",
            "stop_rule": "stop if no signal appears in the primary-covered target set",
            "hypothesis_anchor": lead_hypothesis,
            "reasoning_trace": logic_trace[:2] + ["early kill this first because the full stack should not continue if the lead drug misses core targets"],
            "estimated_savings_eur": float(base_savings),
        },
        {
            "id": "deviation_rescue",
            "title": "deviation rescue check",
            "focus": deviation_focus,
            "goal": "test whether deviation genes truly need rescue or are downstream only",
            "cheap_readout": "small add-on comparison arm",
            "stop_rule": "stop if deviation genes do not change disease-relevant output",
            "hypothesis_anchor": lead_hypothesis,
            "reasoning_trace": logic_trace[:3] + [f"uncovered deviation after the primary was {deviation_focus}"] ,
            "estimated_savings_eur": float(base_savings + 1200),
        },
        {
            "id": "bundle_redundancy",
            "title": "minimal bundle redundancy check",
            "focus": bundle_focus,
            "goal": "confirm each added component contributes unique coverage rather than cosmetic overlap",
            "cheap_readout": "ablation-style remove-one-component run",
            "stop_rule": "stop using any add-on that does not improve deviation closure",
            "hypothesis_anchor": lead_hypothesis,
            "reasoning_trace": logic_trace + ["remove each addon one by one to see if bundle logic was real or fake overlap"],
            "estimated_savings_eur": float(base_savings + 1600),
        },
        {
            "id": "spillover_check",
            "title": "spillover and off-target check",
            "focus": "spillover control",
            "goal": "measure whether bundle spillover outweighs disease coverage gain",
            "cheap_readout": "side-signal panel on non-disease targets",
            "stop_rule": "stop if spillover burden rises without material disease-gene gain",
            "hypothesis_anchor": lead_hypothesis,
            "reasoning_trace": [f"bundle spillover genes: {', '.join(bundle_result.get('spillover_genes', [])) or 'none'}", "cheap off-target checks can avoid burning later protocol budget"],
            "estimated_savings_eur": float(base_savings + 2100),
        },
        {
            "id": "future_mimic",
            "title": "future medicine mimic check",
            "focus": future_focus,
            "goal": "simulate whether a future medicine path is justified beyond the current market bundle",
            "cheap_readout": "virtual or low-scale gap-fill mimic",
            "stop_rule": "stop if gap-fill logic does not improve on current market bundle",
            "hypothesis_anchor": lead_hypothesis,
            "reasoning_trace": [future_path.get("creation_rationale", ""), future_path.get("translation_note", "")],
            "estimated_savings_eur": float(base_savings + 2800),
        },
    ]


def build_sim_context(memory: Dict[str, object], disease: RareDiseaseRecord, primary_result: Dict[str, object]) -> Dict[str, object]:
    trace_sample = list(memory.get("trace_sample", []) or [])
    disease_name = disease.name
    matched = [row for row in trace_sample if str(row.get("case", "")).lower() == disease_name.lower()]
    support = "historical traces suggest primary-first then deviation-fill logic" if (matched or trace_sample) else "none"
    return {
        "trained": bool(memory.get("trained", False)),
        "window": memory.get("window"),
        "cases_seen": int(memory.get("cases_seen", 0) or 0),
        "hit_ratio": float(memory.get("hit_ratio", 0.0) or 0.0),
        "pattern_summary": str(memory.get("pattern_summary", memory.get("pattern", "train first to store general rare-pattern logic"))),
        "matched_traces": matched[:6],
        "trace_sample": trace_sample[:6],
        "support_note": support,
    }


def describe_selection(
    disease_genes: Sequence[str],
    candidate_map: Dict[str, CandidateRecord],
    selected_ids: Sequence[str],
) -> Dict[str, object]:
    genes = unique_norm_genes(disease_genes)
    selected = [candidate_map[sid] for sid in selected_ids if sid in candidate_map]
    covered: Set[str] = set()
    spillover: Set[str] = set()
    gene_set = set(genes)

    selected_payload = []
    for c in selected:
        covered.update(g for g in c.targets if g in gene_set)
        spillover.update(g for g in c.spillover_targets if g not in gene_set)
        selected_payload.append({"id": c.id, "name": c.name, "kind": c.kind, "source": c.source})

    uncovered = [g for g in genes if g not in covered]
    return {
        "selected": selected_payload,
        "covered_genes": sorted(covered),
        "uncovered_genes": uncovered,
        "spillover_genes": sorted(spillover),
        "coverage_ratio": round(len(covered) / max(1, len(genes)), 3),
        "spillover_ratio": round(len(spillover) / max(1, len(genes)), 3),
    }
