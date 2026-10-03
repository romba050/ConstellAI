from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

POSITIVE_DISEASE_DIRECTIONS = {"up", "overactive", "gain", "gain_of_function", "high", "elevated"}
NEGATIVE_DISEASE_DIRECTIONS = {"down", "underactive", "loss", "loss_of_function", "low", "reduced"}

INHIBIT_EFFECTS = {"inhibit", "block", "suppress", "down", "reduce", "antagonize"}
ACTIVATE_EFFECTS = {"activate", "increase", "up", "boost", "agonize", "restore"}


def normalize_token(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")


def desired_effect_for_disease_direction(direction: str | None) -> str:
    token = normalize_token(direction, "unknown")
    if token in POSITIVE_DISEASE_DIRECTIONS:
        return "inhibit"
    if token in NEGATIVE_DISEASE_DIRECTIONS:
        return "activate"
    return "modulate"


def effect_alignment_score(disease_direction: str | None, intervention_effect: str | None) -> float:
    desired = desired_effect_for_disease_direction(disease_direction)
    effect = normalize_token(intervention_effect, "unknown")

    if desired == "modulate":
        return 0.60 if effect != "unknown" else 0.35

    if desired == "inhibit":
        if effect in INHIBIT_EFFECTS:
            return 1.00
        if effect in ACTIVATE_EFFECTS:
            return -0.85
        return 0.25

    if desired == "activate":
        if effect in ACTIVATE_EFFECTS:
            return 1.00
        if effect in INHIBIT_EFFECTS:
            return -0.85
        return 0.25

    return 0.0


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def disease_weighted_target_map(
    disease_genes: Iterable[str],
    gene_weights: Dict[str, float] | None = None,
    gene_directions: Dict[str, str] | None = None,
) -> Dict[str, Dict[str, float | str]]:
    gene_weights = gene_weights or {}
    gene_directions = gene_directions or {}

    ordered = [str(g).strip().upper() for g in disease_genes if str(g).strip()]
    if not ordered:
        return {}

    out: Dict[str, Dict[str, float | str]] = {}
    total = len(ordered)
    for idx, gene in enumerate(ordered):
        default_weight = round(max(0.35, 1.0 - (idx * 0.08)), 3) if total > 1 else 1.0
        out[gene] = {
            "weight": float(gene_weights.get(gene, default_weight)),
            "direction": str(gene_directions.get(gene, "unknown")),
        }
    return out


def score_intervention_against_disease(
    intervention: dict,
    disease_targets: Dict[str, Dict[str, float | str]],
    spillover_weight: float = 0.22,
) -> dict:
    disease_genes = set(disease_targets.keys())
    target_hits = intervention.get("targets", {}) or {}
    effects = intervention.get("effects", {}) or {}
    spillover = {str(g).strip().upper() for g in (intervention.get("spillover_targets", []) or []) if str(g).strip()}

    covered: List[str] = []
    opposed: List[str] = []
    partial: List[str] = []

    weighted_coverage = 0.0
    wrong_way_penalty = 0.0

    for gene, meta in disease_targets.items():
        if gene not in target_hits:
            continue
        raw_strength = float(target_hits.get(gene, 0.0) or 0.0)
        strength = clamp(raw_strength, 0.0, 1.25)
        align = effect_alignment_score(str(meta.get("direction", "unknown")), effects.get(gene))
        contribution = float(meta["weight"]) * strength * align

        if contribution > 0.10:
            covered.append(gene)
            weighted_coverage += contribution
        elif contribution < -0.05:
            opposed.append(gene)
            wrong_way_penalty += abs(contribution)
        else:
            partial.append(gene)
            weighted_coverage += max(0.0, contribution * 0.4)

    new_spillover = sorted(spillover - disease_genes)
    spill_penalty = len(new_spillover) * spillover_weight

    raw = weighted_coverage - wrong_way_penalty - spill_penalty
    score = round(raw, 3)

    return {
        "id": intervention.get("id"),
        "name": intervention.get("name"),
        "kind": intervention.get("kind", "compound"),
        "score": score,
        "raw_score": round(weighted_coverage, 3),
        "spillover_penalty": round(spill_penalty, 3),
        "wrong_way_penalty": round(wrong_way_penalty, 3),
        "covered_genes": sorted(covered),
        "opposed_genes": sorted(opposed),
        "partial_genes": sorted(partial),
        "new_spillover": new_spillover,
        "target_count": len(covered),
    }


def score_addon_candidate(
    primary: dict,
    candidate: dict,
    disease_targets: Dict[str, Dict[str, float | str]],
    complexity_penalty: float = 0.06,
) -> dict:
    primary_covered = set(primary.get("covered_genes", []) or [])
    primary_spill = set(primary.get("new_spillover", []) or [])

    candidate_targets = set(candidate.get("covered_genes", []) or [])
    candidate_spill = set(candidate.get("new_spillover", []) or [])
    remaining = set(disease_targets.keys()) - primary_covered

    deviation_closed = sorted(candidate_targets & remaining)
    duplicate_hits = sorted(candidate_targets & primary_covered)
    new_spill = sorted(candidate_spill - primary_spill)

    closure_weight = sum(float(disease_targets[g]["weight"]) for g in deviation_closed)
    duplicate_weight = sum(float(disease_targets[g]["weight"]) for g in duplicate_hits)

    spill_penalty = len(new_spill) * 0.20
    complexity = complexity_penalty if deviation_closed else 0.12
    redundancy_penalty = duplicate_weight * 0.18

    net_gain = closure_weight - spill_penalty - complexity - redundancy_penalty

    if closure_weight <= 0:
        label = "reject"
    elif net_gain <= 0:
        label = "weak"
    elif net_gain < 0.18:
        label = "borderline"
    elif net_gain < 0.45:
        label = "usable"
    else:
        label = "strong"

    return {
        **candidate,
        "deviation_closed": deviation_closed,
        "duplicate_hits": duplicate_hits,
        "new_bundle_spillover": new_spill,
        "closure_weight": round(closure_weight, 3),
        "redundancy_penalty": round(redundancy_penalty, 3),
        "addon_spillover_penalty": round(spill_penalty, 3),
        "net_gain": round(net_gain, 3),
        "recommendation_label": label,
        "is_actionable": net_gain > 0 and len(deviation_closed) > 0,
        "why_selected": (
            f"closes {', '.join(deviation_closed)}"
            if deviation_closed else
            "does not close remaining deviation"
        ),
    }


def rank_addons(
    primary: dict,
    addon_scores: Iterable[dict],
    disease_targets: Dict[str, Dict[str, float | str]],
    min_net_gain: float = 0.05,
) -> Tuple[List[dict], dict]:
    ranked = [
        score_addon_candidate(primary, candidate, disease_targets)
        for candidate in addon_scores
    ]
    ranked.sort(key=lambda row: (row["is_actionable"], row["net_gain"], row["closure_weight"], -len(row["new_bundle_spillover"])), reverse=True)

    top = ranked[0] if ranked else None
    gate = {
        "threshold": min_net_gain,
        "top_candidate_name": top.get("name") if top else None,
        "top_net_gain": top.get("net_gain") if top else None,
        "top_is_actionable": bool(top and top.get("is_actionable")),
        "accepted": bool(top and top.get("is_actionable") and float(top.get("net_gain", 0.0)) >= min_net_gain),
    }
    return ranked, gate
